# citation-check

A [Claude Code](https://claude.com/claude-code) skill that audits the citations in an academic manuscript.

Given a Word (`.docx`) or LaTeX (`.tex` + `.bib`) manuscript it:

1. extracts every reference and the sentence(s) that cite it, and writes down the claim each citation is being asked to support;
2. looks up the published record for each reference on CrossRef (volumes, pages, DOIs, working papers that have since been published);
3. obtains the papers from legitimate sources (publisher open access, author pages, repositories, NBER/SSRN/arXiv) or from a local `cited papers/` folder, OCR-ing scans that have no text layer;
4. reads them — in parallel, using subagents — and records whether each paper actually says, shows, or exemplifies what the manuscript attributes to it (SUPPORTED / PARTLY SUPPORTED / NOT SUPPORTED / UNVERIFIABLE), with a quote and page;
5. applies the fixes: for Word, as tracked changes in a new dated copy plus a replaced reference list; for LaTeX, as candidate `_citecheck` copies and a unified diff;
6. produces a spreadsheet of verdicts and a summary that separates what was changed from what is only flagged.

## Install

Copy the folder to `~/.claude/skills/citation-check/` (or add the `.skill` package from Releases). Requires `pandoc`, `pdftotext` (poppler), `curl`, and Python with `lxml`, `openpyxl`, and `python-docx`; `ocrmac` (macOS) or `tesseract` for scanned PDFs.

## Layout

- `SKILL.md` — the workflow and judgment calls
- `scripts/` — `extract_citations.py`, `crossref_lookup.py`, `docx_edit.py` (tracked changes), `format_refs.py` (AMR/APA), `make_report.py` (spreadsheet), `ocr_pdf.py`
- `references/` — the verification-agent prompt, the verdict-to-edit guide, the LaTeX workflow
- `evals/` — test prompts and small fixture manuscripts with deliberately bad citations

Built by Victor Bennett with Claude while auditing a working paper; the guide's judgment calls (concept citations vs. specific models, inherited citations, working-paper drift) come from that audit.
