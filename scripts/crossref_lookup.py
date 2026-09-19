#!/usr/bin/env python3
"""Look up the published record for a reference (CrossRef) and any open-access copy
(Unpaywall, Semantic Scholar). Prints normalized JSON.

Usage:
  crossref_lookup.py --doi 10.1287/mnsc.32.10.1231
  crossref_lookup.py --query "Barney 1986 strategic factor markets expectations luck" [--rows 3]
  crossref_lookup.py --query "..." --email you@example.com   (polite pool; also used for Unpaywall)

Output fields: doi, type, authors [{family, given}], year, title, container, volume,
issue, pages, publisher, oa_pdf (url or null), candidates (for --query: top matches with scores)
"""
import argparse, json, re, sys, urllib.parse, urllib.request

UA = 'citation-check-skill/1.0 (mailto:{email})'


def get(url, email):
    req = urllib.request.Request(url, headers={'User-Agent': UA.format(email=email)})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def normalize(item):
    issued = item.get('issued', {}).get('date-parts', [[None]])[0]
    print_date = item.get('published-print', {}).get('date-parts', [[None]])[0]
    year = (print_date[0] or issued[0]) if (print_date and print_date[0]) else issued[0]
    return {
        'doi': item.get('DOI'),
        'type': item.get('type'),
        'authors': [{'family': a.get('family'), 'given': a.get('given')} for a in item.get('author', [])],
        'year': year,
        'online_year': issued[0],
        'title': ' '.join(item.get('title', [''])),
        'container': ' '.join(item.get('container-title', [''])),
        'volume': item.get('volume'),
        'issue': item.get('issue'),
        'pages': item.get('page'),
        'publisher': item.get('publisher'),
        'abstract': re.sub(r'<[^>]+>', '', item.get('abstract', ''))[:2000] or None,
    }


def oa_pdf(doi, email):
    out = None
    try:
        u = get(f'https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email={email}', email)
        loc = u.get('best_oa_location') or {}
        out = loc.get('url_for_pdf') or loc.get('url')
    except Exception:
        pass
    if not out:
        try:
            s = get(f'https://api.semanticscholar.org/graph/v1/paper/DOI:{urllib.parse.quote(doi)}?fields=openAccessPdf', email)
            out = (s.get('openAccessPdf') or {}).get('url')
        except Exception:
            pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--doi')
    ap.add_argument('--query')
    ap.add_argument('--rows', type=int, default=3)
    ap.add_argument('--email', default='citation-check@example.com')
    ap.add_argument('--no-oa', action='store_true', help='skip open-access lookup')
    a = ap.parse_args()
    if a.doi:
        item = get(f'https://api.crossref.org/works/{urllib.parse.quote(a.doi)}?mailto={a.email}', a.email)['message']
        rec = normalize(item)
        rec['oa_pdf'] = None if a.no_oa else oa_pdf(rec['doi'], a.email)
        print(json.dumps(rec, indent=1, ensure_ascii=False))
    elif a.query:
        q = urllib.parse.quote(a.query)
        items = get(f'https://api.crossref.org/works?query.bibliographic={q}&rows={a.rows}&mailto={a.email}', a.email)['message']['items']
        cands = []
        for it in items:
            r = normalize(it)
            r['score'] = it.get('score')
            cands.append(r)
        best = cands[0] if cands else None
        if best and not a.no_oa and best['doi']:
            best['oa_pdf'] = oa_pdf(best['doi'], a.email)
        print(json.dumps({'best': best, 'candidates': cands}, indent=1, ensure_ascii=False))
    else:
        sys.exit('give --doi or --query')


if __name__ == '__main__':
    main()
