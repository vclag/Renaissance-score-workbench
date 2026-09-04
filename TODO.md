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
