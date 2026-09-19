# Verification agent prompt

Spawn one general-purpose subagent per batch of 12–15 references, all in the same turn so
they finish together. Fill in the `<...>` placeholders. Each agent writes one JSON file;
merge them afterwards.

---

You are verifying citations for an academic paper. Read `<path>/claims_batch<N>.json`.
Each entry has a `key`, a short `ref` (author, year, venue), and `claims` — what our
paper attributes to that work, each with the sentence it comes from.

For EACH entry:

1. **Published metadata.** Find the DOI and the published bibliographic record with the
   CrossRef API, e.g.
   `python3 <skill>/scripts/crossref_lookup.py --query "<author year title words>"`
   then `--doi <DOI>`. Record: full author list, year, exact title, journal or book,
   volume, issue, pages, DOI. For books, teaching notes, or chapters with no DOI, use the
   publisher's page, WorldCat, or Google Books for publisher, city, year, and (for chapters)
   editor and page range. Note when the year people usually cite differs from the version
   of record (online-first vs. print) and when a working paper has since been published
   under a different title — that is the most common bibliographic error.

2. **Obtain the text.** Try in order: the publisher's HTML page via WebFetch (often
   abstract only); an open-access or author-posted PDF — `crossref_lookup.py` reports an
   `oa_pdf` URL from Unpaywall/Semantic Scholar; WebSearch for the title plus "pdf";
   NBER, SSRN, arXiv, university repositories, author homepages; JSTOR previews. Use only
   legitimate sources (publisher, author, institutional repository, preprint server) —
   never Sci-Hub or similar, and never try to get around a paywall, login, or CAPTCHA. If
   you find a PDF, download it with curl to `<papers_dir>/<key>.pdf`, confirm it is really
   a PDF (`file`), delete it if it is an HTML error page, and extract text with
   `pdftotext "<pdf>" "<scratch>/<key>.txt"`. If the PDF is an image-only scan (pdftotext
   returns a few hundred words of boilerplate), OCR it: render pages with
   `pdftoppm -r 200 -png` and run `python3 <skill>/scripts/ocr_pdf.py <pdf> <out.txt>`
   (Apple Vision via the `ocrmac` package on macOS; `pip install ocrmac` if missing — no
   compiler or admin rights needed). Many publisher sites block automated access; when they
   do, say so and move on to other sources rather than retrying.

3. **Verify each claim.** Read the abstract, introduction, the relevant sections, and the
   conclusion, and judge whether the work actually says, shows, or exemplifies what we
   attribute to it. Use exactly one of: SUPPORTED, PARTLY SUPPORTED, NOT SUPPORTED,
   UNVERIFIABLE (could not access enough text). Give a short quote (under 25 words) or a
   specific paraphrase with a page number when you have one. Say what the nuance is:
   the paper says something related but not this; the claim held in the working paper but
   the published version changed; the paper is a reasonable *example* of a category even
   though it does not make the claim itself; the claim is really from a different paper
   (name it). Watch especially for inherited citations — a work cited for the way some
   *other* paper cited it — and check the actual text rather than the secondary reading.
   Be specific and honest; the authors will edit their paper from your notes.

4. Record which version you checked: "published" (typeset article or author-accepted
   manuscript with final pagination), "preprint/working paper", "abstract only", "book
   description", or "secondary source".

Write a JSON array to `<path>/verify_batch<N>.json`, one object per entry:
```
{key, doi, authors, year, title, journal, volume, issue, pages, publisher (books only),
 pdf_downloaded (true/false), version_checked,
 claims: [{claim, verdict, evidence, notes}], overall_notes}
```
Then reply with a short summary listing every NOT SUPPORTED and PARTLY SUPPORTED verdict
and any bibliographic surprises (changed titles, wrong years, working papers now published).

---

## Notes for the orchestrator

- Give agents the absolute paths for `<skill>`, `<papers_dir>` (e.g. `<manuscript dir>/cited
  papers/`), and `<scratch>`. Tell them not to create anything else in the papers folder.
- If a published PDF already exists locally (the authors' own copy, a reference-papers
  folder), point the agent at it so it does not re-download.
- Agents typically need 15–25 minutes and ~150–200k tokens per batch of 15. Do other
  work while they run (draft the grammar pass, prepare the edit tooling); do not poll.
