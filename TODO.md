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

Status: feasibility not yet spiked — see
`Tesi/Notebooks/004_Claude_Notebook_jsymbolic_feasibility.ipynb`
(sibling thesis-project repo) once it exists for the hands-on test
(does a real jSymbolic jar run against this app's own MIDI output,
on real Palestrina data, in an isolated environment).

What it's for: jSymbolic (McKay & Cumming, jMIR project) extracts
1497 numeric features per piece (pitch/rhythm/texture statistics) —
useful for the kind of corpus-wide statistical/ML comparison this
app's per-piece annotation view doesn't otherwise offer. Most natural
fit: one more column-set in the existing bulk analysis-data CSV export
(`_bulk_analysis_csv_bytes`/the Browse "Analysis data (CSV)" button) —
a feature-vector-per-piece table, alongside the cadence/presentation-
type/homorhythm/density CSVs already there — rather than a new
single-piece UI panel, since 1497 numbers per piece aren't something
to browse one at a time.

What's blocking it: jSymbolic is Java, not pip-installable — needs a
JRE added via Streamlit Cloud's `packages.txt` (a real new system
dependency, though a much more standard/lower-risk one than the
already-rejected LilyPond system-binary — a JRE via `packages.txt` is
a common, well-trodden path there). License not yet checked. Whether
it's worth the added deployment complexity for what is, in this app,
a secondary use case (this app's core is single-piece annotation, not
corpus-wide feature-vector export) is a real open question, not yet
decided either way.
