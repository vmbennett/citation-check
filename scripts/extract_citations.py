#!/usr/bin/env python3
"""Extract the reference list and every in-text citation from a manuscript.

Usage:
  extract_citations.py manuscript.docx  [-o citations.json]
  extract_citations.py manuscript.tex   [--bib refs.bib] [-o citations.json]

Output: a JSON list, one entry per reference:
  {key, reference_text | bib_key + bib_fields, first_author, year,
   mentions: [ {sentence} ... ] }
The model then writes the *claims* (what the sentence attributes to the work)
from the mentions -- the script only finds them.

Requires pandoc for .docx input. No third-party Python packages.
"""
import argparse, json, os, re, subprocess, sys

REF_HEADINGS = ('references', 'bibliography', 'works cited', 'literature cited')


# ----------------------------------------------------------------- helpers
def sentences(text):
    """Crude sentence splitter that keeps citation parentheses intact."""
    text = re.sub(r'\s+', ' ', text)
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z“"(\[\\])', text)
    return [p.strip() for p in parts if p.strip()]


def docx_to_text(path):
    return subprocess.run(['pandoc', '--track-changes=accept', path, '-t', 'plain', '--wrap=none'],
                          capture_output=True, text=True, check=True).stdout


def split_body_refs(text):
    lines = text.split('\n')
    idx = None
    for i, l in enumerate(lines):
        if l.strip().lower() in REF_HEADINGS:
            idx = i  # keep the LAST heading match (a TOC could hit earlier)
    if idx is None:
        return text, []
    body = '\n'.join(lines[:idx])
    refs = [l.strip() for l in lines[idx + 1:] if l.strip()]
    # merge wrapped lines: a new entry starts with a capitalised surname + comma
    merged = []
    for l in refs:
        if merged and not re.match(r"^[A-Z][A-Za-z’'\-]+,", l):
            merged[-1] += ' ' + l
        else:
            merged.append(l)
    return body, merged


def ref_key(entry):
    m = re.match(r"^([A-Z][A-Za-z’'\- ]+?),.*?\b((?:19|20)\d{2}[a-z]?)\b", entry)
    if not m:
        return None, None
    return m.group(1).split()[0], m.group(2)


# ----------------------------------------------------------------- docx
def extract_docx(path):
    text = docx_to_text(path)
    body, refs = split_body_refs(text)
    sents = sentences(body)
    out = []
    for entry in refs:
        surname, year = ref_key(entry)
        if not surname:
            out.append({'key': entry[:40], 'reference_text': entry, 'first_author': None,
                        'year': None, 'mentions': [], 'note': 'could not parse author/year'})
            continue
        yr = year.rstrip('abcdefg')
        # surname then the year within ~100 chars with no sentence break: catches
        # "(Barney, 1986; ...)", "Barney (1986)", "Arrow’s (1962)", "Denrell, Fang, and Winter (2003)"
        pat = re.compile(r"\b" + re.escape(surname) + r"(?:’s|'s)?[^.;]{0,100}?\b" + re.escape(yr))
        mentions = [{'sentence': s} for s in sents if pat.search(s)]
        out.append({'key': f'{surname}{yr}', 'reference_text': entry, 'first_author': surname,
                    'year': year, 'mentions': mentions})
    return out


# ----------------------------------------------------------------- latex
def parse_bib(path):
    src = open(path, encoding='utf-8', errors='replace').read()
    entries = {}
    for m in re.finditer(r'@(\w+)\s*\{\s*([^,\s]+)\s*,', src):
        etype, key = m.group(1), m.group(2)
        # find the matching closing brace
        depth, i = 1, m.end()
        while i < len(src) and depth:
            depth += {'{': 1, '}': -1}.get(src[i], 0)
            i += 1
        body = src[m.end():i - 1]
        fields = {}
        for fm in re.finditer(r'(\w+)\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|"[^"]*"|[^,\n]+)', body):
            val = fm.group(2).strip().strip('{}"').strip()
            fields[fm.group(1).lower()] = re.sub(r'\s+', ' ', val)
        entries[key] = {'type': etype.lower(), **fields}
    return entries


def strip_latex(s):
    s = re.sub(r'\\(?:cite[pt]?|parencite|textcite|citep|citet|autocite)\*?(?:\[[^\]]*\])*\{([^}]*)\}',
               r'[\1]', s)
    s = re.sub(r'\\[a-zA-Z]+\*?(?:\[[^\]]*\])?\{([^}]*)\}', r'\1', s)
    s = re.sub(r'\\[a-zA-Z]+', '', s)
    s = s.replace('~', ' ').replace('``', '“').replace("''", '”')
    return re.sub(r'\s+', ' ', s)


def extract_tex(path, bib=None):
    src = open(path, encoding='utf-8', errors='replace').read()
    src = re.sub(r'(?<!\\)%.*', '', src)  # drop comments
    if bib is None:
        m = re.search(r'\\(?:bibliography|addbibresource)\{([^}]+)\}', src)
        if m:
            cand = m.group(1).split(',')[0].strip()
            if not cand.endswith('.bib'):
                cand += '.bib'
            bib = os.path.join(os.path.dirname(os.path.abspath(path)), cand)
    bibdb = parse_bib(bib) if bib and os.path.exists(bib) else {}
    cite_re = re.compile(r'\\(?:cite[pt]?|parencite|textcite|citep|citet|autocite)\*?(?:\[[^\]]*\])*\{([^}]*)\}')
    used = {}
    for para in re.split(r'\n\s*\n', src):
        for s in sentences(para):
            for m in cite_re.finditer(s):
                for k in m.group(1).split(','):
                    k = k.strip()
                    if k:
                        used.setdefault(k, []).append({'sentence': strip_latex(s)})
    out = []
    for k, ments in used.items():
        f = bibdb.get(k, {})
        out.append({'key': k, 'bib_key': k, 'bib_fields': f,
                    'first_author': (f.get('author', '').split(' and ')[0].split(',')[0].strip() or None),
                    'year': f.get('year'), 'mentions': ments,
                    **({} if f else {'note': 'key not found in .bib'})})
    return out


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('manuscript')
    ap.add_argument('--bib')
    ap.add_argument('-o', '--out', default='citations.json')
    a = ap.parse_args()
    if a.manuscript.lower().endswith('.docx'):
        data = extract_docx(a.manuscript)
    elif a.manuscript.lower().endswith('.tex'):
        data = extract_tex(a.manuscript, a.bib)
    else:
        sys.exit('manuscript must be .docx or .tex')
    json.dump(data, open(a.out, 'w'), indent=1, ensure_ascii=False)
    n_ment = sum(len(d['mentions']) for d in data)
    orphans = [d['key'] for d in data if not d['mentions']]
    print(f'{len(data)} references, {n_ment} in-text mentions -> {a.out}')
    if orphans:
        print('references with no in-text mention (check manually):', ', '.join(orphans))


if __name__ == '__main__':
    main()
