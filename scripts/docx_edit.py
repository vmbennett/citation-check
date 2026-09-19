#!/usr/bin/env python3
"""Apply text edits to a .docx as Word tracked changes (or plain edits) and optionally
replace the reference list. Never modifies the input file.

Usage:
  docx_edit.py input.docx output.docx edits.json [--author "Claude"]

edits.json:
{
  "author": "Claude",                       # optional, default Claude
  "edits": [
    {"old": "was greater", "new": "is greater", "tracked": true,
     "context": "was greater than their marginal cost"},   # context: unique string that contains old
    {"old": "(Schmalensee, 1981)", "new": "(Shelef et al., 2025)", "tracked": true}
  ],
  "references": {                           # optional: replace everything after the heading
    "heading": "References",
    "entries": ["Adegbesan, J. A. 2009. ...", "..."]
  }
}

Each edit must match exactly one paragraph (use "context" to disambiguate). Edits are
applied in order; an edit that fails stops the run with a message naming it, so fix the
old/context string and rerun. Text inserted by an earlier *tracked* edit is not searchable
by later edits (it lives inside <w:ins>), so anchor later edits on untouched text.

Requires: lxml. Verify the result with: python -c "import docx; docx.Document('out.docx')"
and: pandoc --track-changes=all out.docx -t markdown | grep -c insertion
"""
import argparse, copy, datetime, json, os, shutil, sys, tempfile, zipfile
from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
XMLSPACE = '{http://www.w3.org/XML/1998/namespace}space'


def q(tag):
    return '{%s}%s' % (W, tag)


class Doc:
    def __init__(self, path, author='Claude'):
        self.tmp = tempfile.mkdtemp(prefix='docx_edit_')
        with zipfile.ZipFile(path) as z:
            z.extractall(self.tmp)
        self.xml_path = os.path.join(self.tmp, 'word', 'document.xml')
        self.tree = etree.parse(self.xml_path)
        self.root = self.tree.getroot()
        self.body = self.root.find(q('body'))
        self.author = author
        self.date = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        self._id = 90000
        for p in self.root.iter(q('p')):
            self._merge_runs(p)

    # ---- run helpers
    @staticmethod
    def _simple(r):
        return r.tag == q('r') and all(k.tag in (q('rPr'), q('t'), q('lastRenderedPageBreak')) for k in r)

    @staticmethod
    def _text(r):
        return ''.join((t.text or '') for t in r.findall(q('t')))

    def _merge_runs(self, p):
        prev = None
        for r in list(p):
            if r.tag != q('r') or not self._simple(r):
                prev = None
                continue
            rpr = r.find(q('rPr'))
            sig = etree.tostring(rpr) if rpr is not None else b''
            ts = r.findall(q('t'))
            if len(ts) > 1:
                ts[0].text = ''.join((t.text or '') for t in ts)
                for t in ts[1:]:
                    r.remove(t)
            if prev is not None and prev[1] == sig and ts:
                pt = prev[0].find(q('t'))
                if pt is None:
                    pt = etree.SubElement(prev[0], q('t'))
                pt.text = (pt.text or '') + ts[0].text
                pt.set(XMLSPACE, 'preserve')
                p.remove(r)
            else:
                if ts:
                    ts[0].set(XMLSPACE, 'preserve')
                prev = (r, sig)

    def _make_run(self, rpr, text, deleted=False):
        r = etree.Element(q('r'))
        if rpr is not None:
            r.append(copy.deepcopy(rpr))
        t = etree.SubElement(r, q('delText') if deleted else q('t'))
        t.text = text
        t.set(XMLSPACE, 'preserve')
        return r

    def _next_id(self):
        self._id += 1
        return str(self._id)

    def _ptext(self, p):
        return ''.join(self._text(r) for r in p.findall(q('r')))

    # ---- public
    def replace(self, old, new, tracked=True, context=None):
        key = context or old
        hits = [p for p in self.root.iter(q('p')) if key in self._ptext(p)]
        if len(hits) != 1:
            raise ValueError(f'expected exactly 1 paragraph containing {key!r}, found {len(hits)}')
        p = hits[0]
        full = self._ptext(p)
        i = (full.index(context) + context.index(old)) if context else full.index(old)
        j = i + len(old)
        pos, spans = 0, []
        for r in p.findall(q('r')):
            t = self._text(r)
            spans.append((r, pos, pos + len(t)))
            pos += len(t)
        covered = [(r, s, e) for r, s, e in spans if e > i and s < j]
        if not covered or not all(self._simple(r) for r, _, _ in covered):
            raise ValueError(f'{old!r} spans a run that cannot be split (tab/break/field inside)')
        first, fs, _ = covered[0]
        last, ls, _ = covered[-1]
        before = self._text(first)[: i - fs]
        after = self._text(last)[j - ls:]
        rpr_a, rpr_b = first.find(q('rPr')), last.find(q('rPr'))
        idx = list(p).index(first)
        for r, _, _ in covered:
            p.remove(r)
        nodes = []
        if before:
            nodes.append(self._make_run(rpr_a, before))
        if tracked:
            d = etree.Element(q('del'))
            d.set(q('id'), self._next_id()); d.set(q('author'), self.author); d.set(q('date'), self.date)
            d.append(self._make_run(rpr_a, old, deleted=True))
            nodes.append(d)
            if new:
                ins = etree.Element(q('ins'))
                ins.set(q('id'), self._next_id()); ins.set(q('author'), self.author); ins.set(q('date'), self.date)
                ins.append(self._make_run(rpr_a, new))
                nodes.append(ins)
        elif new:
            nodes.append(self._make_run(rpr_a, new))
        if after:
            nodes.append(self._make_run(rpr_b, after))
        for n in nodes:
            p.insert(idx, n)
            idx += 1

    def replace_references(self, entries, heading='References'):
        paras = self.body.findall(q('p'))
        heads = [p for p in paras if self._ptext(p).strip().lower() == heading.lower()]
        if not heads:
            raise ValueError(f'no paragraph reads exactly {heading!r}')
        h = heads[-1]
        hidx = list(self.body).index(h)
        old = [el for el in list(self.body)[hidx + 1:] if el.tag == q('p')]
        if not old:
            raise ValueError('no paragraphs after the references heading')
        template = copy.deepcopy(old[0])
        for k in list(template):
            if k.tag != q('pPr'):
                template.remove(k)
        first_run = old[0].find(q('r'))
        rpr = first_run.find(q('rPr')) if first_run is not None else None
        for el in old:
            self.body.remove(el)
        at = hidx + 1
        for e in entries:
            p = copy.deepcopy(template)
            p.append(self._make_run(rpr, e))
            self.body.insert(at, p)
            at += 1

    def save(self, out):
        self.tree.write(self.xml_path, xml_declaration=True, encoding='UTF-8', standalone=True)
        if os.path.exists(out):
            os.remove(out)
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
            for base, _, files in os.walk(self.tmp):
                for f in files:
                    full = os.path.join(base, f)
                    z.write(full, os.path.relpath(full, self.tmp))
        shutil.rmtree(self.tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input'); ap.add_argument('output'); ap.add_argument('edits')
    ap.add_argument('--author')
    a = ap.parse_args()
    spec = json.load(open(a.edits))
    doc = Doc(a.input, author=a.author or spec.get('author', 'Claude'))
    refs = spec.get('references')
    if refs:  # do this first so body-text searches don't hit reference entries
        doc.replace_references(refs['entries'], refs.get('heading', 'References'))
        print(f"replaced reference list ({len(refs['entries'])} entries)")
    for n, e in enumerate(spec.get('edits', []), 1):
        try:
            doc.replace(e['old'], e.get('new', ''), e.get('tracked', True), e.get('context'))
            print(f"{n:3d} {'tracked ' if e.get('tracked', True) else 'plain   '} {e['old'][:60]!r}")
        except ValueError as err:
            sys.exit(f'edit {n} failed: {err}')
    doc.save(a.output)
    print('saved', a.output)


if __name__ == '__main__':
    main()
