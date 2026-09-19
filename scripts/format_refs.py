#!/usr/bin/env python3
"""Format normalized metadata records (from crossref_lookup.py or the verification
agents) as reference-list strings.

Usage:
  format_refs.py records.json --style amr|apa [--sort]
records.json: list of {authors:[{family,given}] | "authors": "Barney, J. B.", year, title,
  container, volume, issue, pages, publisher, place, type, editors, book_title, doi}

Styles: amr (Academy of Management journals: "Barney, J. B. 1986. Title. Journal, 32: 1231–1241.")
        apa (APA 7: "Barney, J. B. (1986). Title. Journal, 32(10), 1231–1241. https://doi.org/...")
Titles are printed as given; use --sentence-case to lower-case words after the first
(keeps words after a colon and all-caps acronyms capitalized).
"""
import argparse, json, re, sys


def initials(given):
    if not given:
        return ''
    parts = re.split(r'[\s\-]+', given.strip())
    return ' '.join(p[0].upper() + '.' for p in parts if p)


def author_str(authors, style):
    if isinstance(authors, str):
        return authors.strip()
    names = []
    for a in authors:
        fam, giv = a.get('family', ''), initials(a.get('given', ''))
        names.append(f'{fam}, {giv}'.rstrip(', ') if giv else fam)
    if not names:
        return ''
    if len(names) == 1:
        return names[0]
    if style == 'apa' and len(names) > 20:
        names = names[:19] + ['...'] + names[-1:]
    return ', '.join(names[:-1]) + ', & ' + names[-1]


def sentence_case(t):
    if not t:
        return t
    words = t.split(' ')
    out = []
    cap_next = True
    for w in words:
        if cap_next or (len(w) > 1 and w.isupper()) or re.match(r'^[A-Z][a-z]*[A-Z]', w):
            out.append(w)
        else:
            out.append(w[0].lower() + w[1:] if w else w)
        cap_next = w.endswith(':') or w.endswith('?')
    return ' '.join(out)


def pages(p):
    return p.replace('-', '–') if p else ''


def fmt(r, style, sc):
    au = author_str(r.get('authors', ''), style)
    yr = r.get('year', 'n.d.')
    title = sentence_case(r.get('title', '')) if sc else r.get('title', '')
    typ = (r.get('type') or ('book' if r.get('publisher') and not r.get('container') else 'journal-article'))
    cont, vol, iss, pg = r.get('container', ''), r.get('volume'), r.get('issue'), pages(r.get('pages'))
    if style == 'amr':
        head = f'{au} {yr}. {title.rstrip(".")}.'
        if typ == 'book':
            return f'{head} {r.get("place", "")}{": " if r.get("place") else ""}{r.get("publisher", "")}.'
        if typ == 'book-chapter':
            eds = r.get('editors', '')
            return f'{head} In {eds} (Ed{"s" if " & " in eds or "," in eds else ""}.), {r.get("book_title", "")}: {pg}. {r.get("place", "")}{": " if r.get("place") else ""}{r.get("publisher", "")}.'
        v = f' {vol}' if vol else ''
        i = f'({iss})' if iss and r.get('keep_issue') else ''
        return f'{head} {cont},{v}{i}: {pg}.'.replace(',:', ':')
    # apa
    head = f'{au} ({yr}). '
    doi = f' https://doi.org/{r["doi"]}' if r.get('doi') else ''
    if typ == 'book':
        return f'{head}{title.rstrip(".")}. {r.get("publisher", "")}.{doi}'
    if typ == 'book-chapter':
        eds = r.get('editors', '')
        return f'{head}{title.rstrip(".")}. In {eds} (Ed{"s" if " & " in eds or "," in eds else ""}.), {r.get("book_title", "")} (pp. {pg}). {r.get("publisher", "")}.{doi}'
    v = f', {vol}' if vol else ''
    i = f'({iss})' if iss else ''
    return f'{head}{title.rstrip(".")}. {cont}{v}{i}, {pg}.{doi}'.replace(', .', '.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('records'); ap.add_argument('--style', default='amr', choices=['amr', 'apa'])
    ap.add_argument('--sort', action='store_true'); ap.add_argument('--sentence-case', action='store_true')
    ap.add_argument('-o', '--out')
    a = ap.parse_args()
    recs = json.load(open(a.records))
    lines = [fmt(r, a.style, a.sentence_case) for r in recs]
    if a.sort:
        lines.sort(key=lambda s: s.lower())
    if a.out:
        json.dump(lines, open(a.out, 'w'), indent=1, ensure_ascii=False)
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
