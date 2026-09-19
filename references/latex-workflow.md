# LaTeX manuscripts

For `.tex` sources there is no tracked-changes mechanism, so the deliverable is a
*candidate* copy the authors can diff, never an edit of the original.

## Extraction

`extract_citations.py paper.tex` finds `\cite`, `\citep`, `\citet`, `\parencite`,
`\textcite`, `\autocite` (with optional arguments) and reads the `.bib` named in
`\bibliography{}` / `\addbibresource{}` (or pass `--bib`). Each record carries `bib_key`,
the parsed `bib_fields`, and the sentences that cite the key. Keys missing from the `.bib`
are flagged with a note. If the paper uses `\input`/`\include`, run the script on each
file or concatenate them first.

## Applying changes

1. Copy the sources: `paper.tex` → `paper_citecheck.tex`, `refs.bib` → `refs_citecheck.bib`
   (same directory, so relative paths still resolve).
2. Text changes: edit the candidate `.tex` with the Edit tool, one sentence at a time,
   exactly the same edits you would have made as tracked changes in Word. For a citation
   swap change only the key inside `\cite{}`; for a wording change change only the words.
3. Bibliography changes: edit the candidate `.bib` entry fields (`year`, `volume`,
   `number`, `pages`, `title`, `journal`); add new entries for added references; leave
   dropped entries in place (BibTeX ignores uncited keys) unless the authors want them
   removed.
4. Produce the diff the authors will read:
   ```bash
   diff -u paper.tex paper_citecheck.tex > paper_citecheck.diff
   diff -u refs.bib refs_citecheck.bib >> paper_citecheck.diff
   ```
   If `latexdiff` is installed, also produce a compilable markup version:
   `latexdiff paper.tex paper_citecheck.tex > paper_diff.tex`.
5. Point the candidate `.tex` at the candidate `.bib` (`\bibliography{refs_citecheck}`)
   only if the authors want to compile the candidate on its own; otherwise leave the
   `\bibliography{}` line alone so the diff stays minimal.

## Reporting

Same spreadsheet and summary as for Word. In the summary, name the candidate files and the
diff, and list each change in the form "line N: old → new (reason)" so the authors can read
the diff with the reasons beside it.
