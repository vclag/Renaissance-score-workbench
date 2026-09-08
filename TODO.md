# TODO

Deliberately deferred work — not urgent, not forgotten. Add an entry
when something real gets set aside on purpose; check here before
starting unrelated exploratory work in case it's already covered.

## Fix (or work around) the Verovio tie-rendering crash under
`_compress_multimeasure_rests`

Status: built, verified correct, currently **unused** — reverted from
the live pipeline (2026-09-04) for safety, not deleted.

What it's for: consecutive whole-measure rests in one voice collapse
into a single "N measures rest" symbol (standard notation practice,
via music21's `spanner.MultiMeasureRest` → MusicXML's `<measure-style>
<multiple-rest>`) — real, meaningful page-count reduction confirmed
(Josquin's 24-voice "Qui habitat in adjutorio altissimi": 50 → 37
pages, -26%), for both the PDF and "Download MusicXML" exports, per a
direct user request.

What's blocking it: wiring it into `run_pipeline`/`_annotate_crim_piece`
triggers a severe, reproducible Verovio rendering crash — `[Error]
Staff @n='X' for rendering control event tie ... not found`, hanging/
killing the renderer. Reproduced on a normal, previously-solid 5-voice
Palestrina piece (`Agnus_00`), not just the extreme canon that
prompted this — a systemic risk across the corpus, not an isolated
edge case. The generated MusicXML checks out as standard and correct
(confirmed directly), so this looks like a genuine bug in Verovio's own
tie-rendering path interacting with a nearby compressed rest run, not a
mistake in this function's own output — not independently confirmed
against Verovio's own C++ source, though.

Next step, whenever this gets picked back up: see
`app.py`'s `_compress_multimeasure_rests` docstring for the full
investigation (what was tried, what was ruled out — Verovio's own
`condense` option does something different and doesn't help here).
Start by checking whether the crash is specifically tied to a
compressed run sitting *adjacent to* a tied note (as opposed to
anywhere in the score) — if so, a narrower fix (skip compressing a run
when a tie starts/ends in the measure immediately before/after it)
might dodge the bug without needing to fix Verovio itself.

## Integrate jSymbolic feature extraction into the app

Status: **feasibility spiked, result is negative for now** — see
`Tesi/Notebooks/0004_Claude_Notebook_jsymbolic_feasibility.ipynb`
(sibling thesis-project repo, real hands-on test, not just reading the
manual) and `Tesi/done_by_claude/note_osservazioni_prompt/
library_integration_bugs_and_gotchas.md`'s §4 for the full detail.

**This entry originally said "just needs a JRE via `packages.txt`" —
that was wrong, written before the actual test below was run; corrected
here rather than left standing.**

What was found: jSymbolic 2.2 (the official, recommended stable
release, not an unstable dev build) hangs indefinitely — confirmed
actively burning CPU/memory, not deadlocked — on essentially any real
input. Confirmed via a real Palestrina piece (Agnus_00), a single
monophonic voice of it, and finally on 9+ completely trivial identical
notes (8 succeeds in ~19s, 9 hangs) — ruling out anything Renaissance-,
Palestrina-, or polyphony-specific, and ruling out the JVM version too
(identical hang on Java 21 and Java 8). This is very likely a real,
general bug in jSymbolic 2.2 itself, not a deployment-environment
question at all — the JRE/`packages.txt` concern this entry originally
raised turned out to be moot; the tool doesn't get that far.

A second, separate, real bug was also found and IS fixable: jSymbolic's
own CSV/ARFF export crashes on a non-English-locale JVM (comma vs.
period decimal separator) — fixed via `-Duser.language=en
-Duser.country=US`. Doesn't help with the hang above, though.

License, for the record: GNU GPL v2 (confirmed directly from the
distributed package).

Next step, if this gets revisited: bisect which of jSymbolic's ~246
feature types causes the hang via its own `-configrun` config-file
mechanism (not attempted in the spike above), or report the bug
upstream to the jMIR project. Not urgent — this thesis's own existing
feature set (topology measures, CDM/KL, DEA) doesn't depend on
jSymbolic at all.
