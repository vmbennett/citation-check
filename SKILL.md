---
name: citation-check
description: Verify the citations in an academic manuscript (Word .docx or LaTeX .tex/.bib) — extract every reference and the claim attached to it, obtain the cited papers (published versions where possible), check that each paper actually says or shows what the manuscript attributes to it, correct the bibliographic details from CrossRef, and apply the fixes as Word tracked changes or as a candidate file to diff for LaTeX, with a spreadsheet of verdicts. Use this whenever a user asks to check, verify, audit, or "make sure" the citations, references, sources, or bibliography of a paper, chapter, proposal, or dissertation; whenever they ask whether cited papers really say what the draft claims; whenever they want the reference list completed or corrected (volumes, pages, years, working papers now published); or whenever they ask to download the papers a manuscript cites — even if they don't say "citation check" and even if they only want the report and no edits.
---

# Citation check

A citation check answers two questions for every reference in a manuscript: is the
bibliographic record right, and does the work actually support what the sentence citing it
claims? The second question is the valuable one and the one nobody does by hand, because it
means reading fifty papers. The workflow below splits the reading across subagents, keeps
everything auditable (every verdict has evidence, every change is visible to the authors),
and never touches the original file.

Deliverables, unless the user asks for a subset:
1. A spreadsheet (`citation_verification.xlsx`) with one row per attributed claim: verdict,
   evidence, which version of the paper was checked, and what was changed in the manuscript.
2. The corrected manuscript: for `.docx`, a new dated copy with text changes as tracked
   changes (author "Claude") and the reference list replaced; for `.tex`, candidate
   `_citecheck` copies of the `.tex` and `.bib` plus a unified diff.
3. A `cited papers/` folder with the PDFs that could be obtained from legitimate sources.
4. A summary message: counts, every unsupported or partly supported attribution and what
   was done about it, bibliographic corrections, what could not be verified and why, and
   anything that needs the authors' judgment rather than yours.

## Step 1 — Extract references and claims

```bash
python3 <skill>/scripts/extract_citations.py manuscript.docx -o citations.json      # or .tex [--bib refs.bib]
```

The script splits off the reference list, finds every sentence that cites each reference,
and flags references with no in-text mention. It does not know what the sentence *claims* —
write that yourself. For each reference produce a `claims` list: a one-sentence statement of
what the manuscript attributes to the work, kept close to the manuscript's wording, with
the citing sentence attached. Distinguish "X shows that …" from "e.g., X" from "X is an
example of …", because the verifier needs to know how strong the attribution is. A
reference cited in three places gets three claims. Save as `claims.json`:

```json
[{"key": "Barney1986", "ref": "Barney (1986) Management Science",
  "claims": ["Firms earn profits from resources acquired in strategic factor markets only when they have more accurate expectations than other participants, or when lucky. (sentence: …)"]}]
```

Ask before starting only if something is genuinely unknowable from the files: which file is
the current version, or whether the authors want text edits at all. Don't ask about
citation style, output names, or whether to track changes — pick the sensible default
(target journal's style if stated, otherwise keep the manuscript's; track text changes;
new dated file) and say what you chose.

## Step 2 — Decide how you will get the papers

Check before spending an hour on it:

- **CrossRef is always available** (`scripts/crossref_lookup.py`) and is the authority for
  volumes, pages, titles, and whether a working paper has been published. Use it for every
  reference regardless of whether you can read the paper.
- **Library access.** If the user offers a library login, test it once on a gated paper with
  the browser tool before relying on it. Institutional proxy domains are often blocked for
  automated browsing, and publisher sites (INFORMS, Wiley, Elsevier, AOM, SAGE) show bot
  checks to automated sessions. Never try to get past a CAPTCHA or login wall. If access
  doesn't work, say so once and fall back to open copies.
- **Open copies** come from Unpaywall and Semantic Scholar (`crossref_lookup.py` reports an
  `oa_pdf`), NBER, SSRN, arXiv, institutional repositories, and author homepages. Only
  publisher, author, or repository postings. Do not download from shadow libraries or
  third-party mirrors (personal wikis, course-page uploads, file-sharing sites); a paper
  available only that way is checked from its abstract and listed for the user to obtain
  through their library.
- **Local copies first.** Before anything is downloaded, look for PDFs the user already has:
  a `cited papers/` or `references/` folder next to the manuscript, a reference-papers
  folder, their own published work. Match them to references by first page (pdftotext), and
  hand the matches to the agents as the copy to read — these are usually the published
  versions, which beats anything the web will give you for gated journals. The most reliable path for gated papers is
  often the simplest: report which ones could only be checked from abstracts, let the user
  download them through their library, and re-run the check on those (`scripts/ocr_pdf.py`
  handles scans without a text layer). Design the report so that second pass is easy.

Record for every reference which version was actually read — published, preprint, abstract
only — because a check against a working paper can miss changes made in review, which is
exactly the kind of error the user is trying to catch.

## Step 3 — Verify in parallel

Split `claims.json` into batches of 12–15 and spawn one subagent per batch in the same turn,
using the prompt in `references/verification-agent-prompt.md`. Each agent looks up the
record, obtains the text, reads it, and writes `verify_batch<N>.json` with a verdict
(SUPPORTED / PARTLY SUPPORTED / NOT SUPPORTED / UNVERIFIABLE), evidence with a page number
where possible, and notes on the nuance. While they run, do the parts of the job that don't
depend on them: the grammar pass if one was requested, and the edit tooling.

Merge the batches into `verify_all.json` when they finish and tally the verdicts.

## Step 4 — Decide the fixes

Read `references/verdict-guide.md` before touching the manuscript. The short version:

- A NOT SUPPORTED verdict usually means an inherited citation (copied from how another
  paper cited it), an over-reaching sentence, or the right claim in the wrong paper by the
  same authors. Each has a different fix — swap, reword, or re-cite — and the guide maps them.
- PARTLY SUPPORTED is where over-correction happens. A paper cited for a *concept* is
  usually a fine anchor even when its specific model differs; reword or co-cite rather than
  remove. Removing a canonical concept paper because a verifier read it narrowly is a
  mistake the authors will catch and lose trust over.
- Never change text on the strength of an abstract. List gated papers as "needs manual
  check" instead.
- Take bibliographic details only from CrossRef or the publisher page, never from another
  paper's reference list.

Anything that changes what a sentence claims or which work supports it must be visible to
the authors — a tracked change in Word, a diff for LaTeX — because they have to be able to
reject it. Reference-list corrections are routine and go in untracked unless asked. If the
user specifies a different split (e.g., "track only grammar"), follow it; when in doubt,
track. Keep tracked spans minimal: change the word, not the sentence.

Write the edits down before applying them, as `edits.json` (see `scripts/docx_edit.py` for
the schema), and an `actions.json` mapping each reference key to a one-line description of
what was done — the spreadsheet's last column comes from it.

## Step 5 — Apply

**Word.** Never edit the file the user gave you; write a new dated copy (Word may have the
original open). Then:

```bash
python3 <skill>/scripts/format_refs.py records.json --style amr --sort -o refs.json   # or apa
python3 <skill>/scripts/docx_edit.py "Draft 9 17.docx" "Draft 9 18.docx" edits.json
python3 -c "import docx; docx.Document('Draft 9 18.docx')"                             # opens?
pandoc --track-changes=all "Draft 9 18.docx" -t markdown | grep -c '{.insertion'         # changes present?
pandoc --track-changes=accept "Draft 9 18.docx" -t plain > accepted.txt                  # then cross-check
```

`docx_edit.py` applies the reference list first, then each edit as `<w:del>`/`<w:ins>`
under the given author, and stops with a clear message if an `old` string isn't found
exactly once — fix the string or add a `context` and rerun. After building, confirm that
every in-text citation has a reference entry and every entry is cited (a short script over
`accepted.txt`), and that the works you removed no longer appear anywhere.

**LaTeX.** Follow `references/latex-workflow.md`: candidate `_citecheck.tex` / `.bib`
copies edited with the Edit tool, plus `diff -u` (and `latexdiff` if installed). The
original files are never modified.

## Step 6 — Report

```bash
python3 <skill>/scripts/make_report.py verify_all.json -o citation_verification.xlsx --actions actions.json
```

This writes the spreadsheet (Claims and Summary sheets, verdict cells coloured) and prints
a markdown summary you can build the final message from. In that message, lead with the
counts and the unsupported attributions; state which version each contested paper was
checked against; separate what you changed from what you are only flagging; and say plainly
what you could not verify and why (blocked proxy, gated publisher). Send the files.

## Judgment calls that come up

- The verifier says a famous paper doesn't support the sentence, but the sentence cites it
  for the general idea the paper is known for. Keep it, narrow the sentence to the idea, and
  co-cite a paper that supports the specific mechanism. Say why in the notes.
- A co-author's sentence over-reaches slightly. Flag it in the summary rather than
  rewriting it; accuracy fixes are yours to make, taste is theirs.
- A working paper has been published under a new title. Update the reference and the
  in-text year, and re-check the claim against the published abstract — findings change.
- The same paper is cited for several claims with different verdicts. Fix each sentence on
  its own; don't remove the reference unless every use fails.
- The user asks only for the report. Then produce the spreadsheet and summary and stop —
  don't hand back an edited file they didn't ask for.

## Requirements

`pandoc`, `pdftotext` (poppler), `curl`; Python with `lxml`, `openpyxl`, `python-docx`
(for verification only). Subagents (the Agent tool) for parallel reading — without them,
run the batches yourself sequentially. Browser tools optional, for library access.
