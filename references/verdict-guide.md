# From verdicts to edits

The verification agents tell you what each paper says. Deciding what to *do* about it is
the judgment part of the job, and it is where a mechanical pass goes wrong in both
directions — leaving bad attributions in, or ripping out citations that were fine under
the reading the authors intended. Work through the verdicts with the questions below.

## Reading a verdict

**NOT SUPPORTED** usually means one of four things, each with a different fix:

| Pattern | Typical cause | Fix |
|---|---|---|
| The paper is about something else entirely | inherited citation — the authors copied it from how another paper cited it | swap in the work that actually supports the claim (often the paper the citation was inherited from), and check whether *that* paper supports it |
| The paper says something adjacent | the claim over-reaches or conflates two ideas | reword the sentence to what the paper shows; keep the citation |
| The claim is in a different paper by the same authors | working paper vs. published version, or a follow-up study | cite the right paper (add the reference) |
| The claim is the authors' own inference presented as the paper's finding | the sentence should own the interpretation | reword ("we read X as…", "e.g.") or drop the citation and let the sentence stand on its own |

A NOT SUPPORTED attribution is still edited when you cannot identify the right replacement:
drop the citation, reword the sentence so the manuscript owns the claim (or hedges it), and
say in the summary that a source is still needed. Leaving the wrong citation in place with a
comment is not a fix — the authors asked for corrections, and a reviewer will see the
attribution, not the comment. Do this as a tracked change / diff line like any other edit.

**PARTLY SUPPORTED** is the most common verdict and the one most likely to be over-corrected.
Before changing anything ask: is the citation there for a *finding*, or for a *concept*?
A paper cited for a concept (signal jamming, preemption, absorptive capacity) is usually a
fine anchor even when the specific model in it differs from the manuscript's setting. The
right move there is often a small rewording so the sentence claims the concept rather than
the specific result, or a co-citation, not a removal. Removing a well-known concept paper
because a verifier read the model narrowly is a mistake the authors will notice.

Conversely, "the paper is an example of the category" is genuinely fine for a citation
introduced with "e.g." or "as in", and is not fine for "X shows that …". Match the strength
of the verb to the strength of the support.

**UNVERIFIABLE** (gated, abstract only): do not change the text on the strength of an
abstract. List these for the authors, marked as needing a manual check, and prioritise the
ones where the attributed claim is specific rather than general.

## What kind of change, and whether to track it

Four kinds of change come up, and they differ in how visible they must be:

1. **Citation swap / add / drop** — the sentence stays, the parenthetical changes.
2. **Wording change** — the sentence's claim is narrowed, softened, or re-attributed.
3. **Reference-list correction** — years, volumes, pages, titles, now-published working papers.
4. **Grammar** — if the authors asked for a grammar pass as well.

Anything that changes what a sentence claims or which work is said to support it (kinds 1,
2, 4) should be visible to the authors as a tracked change or a diff, because they must be
able to accept or reject each one. Reference-list corrections are routine; leave them
untracked unless asked, and say in the summary that they were untracked. If the authors
state a different preference (e.g. "track only grammar"), follow it — but when in doubt,
track: an unnoticed change to a claim is far worse than a cluttered review pane.

Keep tracked edits minimal in span — change "was" to "is", not the whole sentence — so
the review pane shows what actually changed. Rewrite a whole sentence only when the claim
itself is being restructured.

## Bibliographic fixes

Take volumes, issues, and pages from the CrossRef record (`crossref_lookup.py`), not from
memory or from other papers' reference lists, which propagate errors. Common corrections:

- working paper cited by its old title; now published under a new title and year
- online-first year vs. print year (cite the version of record's year)
- HBR and other magazines: volume(issue): pages, no DOI
- chapters: editors, book title, page range, city and publisher
- special issues: `S1` issue numbers; supplement pages

Format the list in the target journal's style with `format_refs.py` (`--style amr` or
`apa`). Convert the whole list at once so it is consistent; do not mix styles.

## What to leave alone

- Citations whose only problem is that a *stronger* citation exists — mention it, don't change it.
- Sentences the co-authors wrote where the fix is a matter of taste rather than accuracy —
  flag them in the summary instead ("this clause is a stretch for that paper").
- The manuscript's argument. You are checking attributions, not refereeing the theory.
