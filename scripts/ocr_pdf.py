#!/usr/bin/env python3
"""OCR an image-only PDF (e.g., a ProQuest or JSTOR scan without a text layer).

Usage:  ocr_pdf.py paper.pdf out.txt [--dpi 200]

Uses Apple's Vision framework through the `ocrmac` package (pip install ocrmac) — pure
Python wheels, no compiler, no admin rights. Pages are separated by form feeds so page
numbers can be recovered. Falls back to tesseract if ocrmac is unavailable and tesseract is
installed. Requires pdftoppm (poppler).
"""
import argparse, glob, os, shutil, subprocess, sys, tempfile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf'); ap.add_argument('out'); ap.add_argument('--dpi', type=int, default=200)
    a = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix='ocr_')
    subprocess.run(['pdftoppm', '-r', str(a.dpi), '-png', a.pdf, os.path.join(tmp, 'p')], check=True)
    pages = sorted(glob.glob(os.path.join(tmp, 'p-*.png')))
    texts = []
    try:
        from ocrmac import ocrmac
        for pg in pages:
            ann = ocrmac.OCR(pg, recognition_level='accurate').recognize()
            texts.append('\n'.join(t for t, _, _ in ann))
    except ImportError:
        if not shutil.which('tesseract'):
            sys.exit('neither ocrmac (pip install ocrmac) nor tesseract is available')
        for pg in pages:
            r = subprocess.run(['tesseract', pg, '-', '--psm', '1'], capture_output=True, text=True)
            texts.append(r.stdout)
    open(a.out, 'w').write('\f'.join(texts))
    shutil.rmtree(tmp, ignore_errors=True)
    print(f'{len(pages)} pages, {sum(len(t.split()) for t in texts)} words -> {a.out}')


if __name__ == '__main__':
    main()
