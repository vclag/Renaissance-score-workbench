"""
pattern_search.py -- transposition-invariant melodic/contrapuntal
pattern search, via PatternFinder (Garfinkle, Arthur, Schubert, Cumming
& Fujinaga, "PatternFinder: Content-Based Music Retrieval with
music21," DLFM'17, DOI 10.1145/3144749.3144751 -- github.com/
ELVIS-Project/PatternFinder), pinned in requirements.txt to the exact
commit this module was verified against.

Only algorithms P1 (exact match) and P2 (approximate match, N
mismatches allowed) are exposed here -- deliberately, not all "seven
algorithms" the paper describes. A real feasibility spike (see
Tesi/done_by_claude/note_osservazioni_prompt/patternfinder_feasibility_
spike.md for the full log) found P1/P2 genuinely work once 5 real
Python-2-to-3 compatibility bugs are patched (all patched below,
session-local, none of them touch the upstream package's own files on
disk) -- but P3 and the whole S/W family (time-scaled/time-warped
matching) hit a deeper, unresolved object-identity bug in the
library's own internals, confirmed independently in two different
algorithm families, and are NOT exposed here. This isn't a theoretical
caveat -- the GitHub repo's own description says "P1 (exact matching)
and P2 (approximate matching) currently operational," which this spike
ended up confirming firsthand rather than just quoting.

Public API: find_pattern_occurrences(query, source, algorithm='P1',
**kwargs) -- see its own docstring. Import this module lazily (inside
whatever UI code needs it), not at app.py's top level: if PatternFinder
isn't installed/importable in some deployment (a real, disclosed risk
of depending on a git-only package, not a PyPI one -- see requirements.
txt's own comment), the rest of the app must keep working.
"""
import copy
import os

_PATCHED = False
_IMPORT_ERROR = None


def _apply_patches():
    """Applies all 5 fixes found during the feasibility spike, exactly
    once per process. Idempotent -- safe to call on every request.

    Fix #1 (most important to get right, most dangerous to get wrong):
    PatternFinder's own __init__.py and geometric_helsinki/indexer.py
    both unconditionally overwrite music21's GLOBAL, per-OS-user
    settings file (music21.environment.UserSettings()['directoryScratch'])
    with a relative path that doesn't exist on any machine but the
    original author's own -- confirmed directly (during the spike) to
    break music21.corpus.parse() in every OTHER environment on the same
    machine the instant `import patternfinder` runs anywhere, not just
    in whatever process imported it. Fixed by capturing music21's
    current setting before import and restoring a valid one (this
    process's own temp directory) immediately after -- every import in
    this module goes through _apply_patches() specifically so this
    repair always runs before anything else touches patternfinder.
    """
    global _PATCHED, _IMPORT_ERROR
    if _PATCHED or _IMPORT_ERROR is not None:
        return
    try:
        from music21 import environment
        us = environment.UserSettings()
        import patternfinder  # noqa: F401 -- import alone corrupts directoryScratch; see above
        import tempfile
        us['directoryScratch'] = tempfile.gettempdir()

        # Fix #2: more_itertools.peekable no longer aliases .next() to
        # __next__() (Python 2 iterator convention); algorithms.py
        # still calls .next() directly in several places.
        import more_itertools
        more_itertools.peekable.next = more_itertools.peekable.__next__

        # Fix #3: CmpItQueue (a queue.PriorityQueue subclass) defines
        # next() but not __next__(), so next(instance)/'for x in
        # instance' both fail despite __iter__ correctly returning self.
        from patternfinder.geometric_helsinki.geometric_notes import CmpItQueue
        CmpItQueue.__next__ = CmpItQueue.next

        # Fix #4: CmpItQueue.queue_item is (sortTuple, item); when two
        # items' sortTuples tie, Python 3's heapq falls through to
        # comparing 'item' itself (raw pointer objects with no
        # ordering at all -- Python 2 allowed arbitrary cross-type '<'
        # comparison, Python 3 removed it). Ties are genuinely
        # equivalent for this algorithm's purposes, so comparison is
        # restricted to sortTuple only -- any stable order among ties
        # is fine.
        CmpItQueue.queue_item.__lt__ = lambda self, other: self.sortTuple < other.sortTuple
        CmpItQueue.queue_item.__le__ = lambda self, other: self.sortTuple <= other.sortTuple
        CmpItQueue.queue_item.__gt__ = lambda self, other: self.sortTuple > other.sortTuple
        CmpItQueue.queue_item.__ge__ = lambda self, other: self.sortTuple >= other.sortTuple

        # Fix #5: P2.algorithm() lets a StopIteration (from x.peek() on
        # an exhausted pointer) escape the generator function itself --
        # legal and silent pre-Python-3.7, a hard RuntimeError since
        # PEP 479. Re-implemented with the EXACT same logic (verified
        # against the real GitHub source), just with the escaping
        # StopIteration caught and converted to an explicit return --
        # same semantics, not a guess at "improved" behavior.
        from itertools import groupby
        from patternfinder.geometric_helsinki import algorithms

        def _fixed_p2_algorithm(self):
            try:
                shifts = CmpItQueue(
                    lambda x: (x.peek(), x.peek().noteEndIndex),
                    len(self.patternPointSet),
                )
                for note in self.patternPointSet:
                    shifts.put(note.source_ptrs[1])
                for _k, ptr_group in groupby(shifts, key=lambda gen: gen.peek()):
                    occ_ptrs = list(ptr_group)
                    yield [ptr.next() for ptr in occ_ptrs]
                    for ptr in occ_ptrs:
                        shifts.put(ptr)
            except StopIteration:
                return

        algorithms.P2.algorithm = _fixed_p2_algorithm

        _PATCHED = True
    except Exception as exc:  # pragma: no cover -- environment-dependent
        _IMPORT_ERROR = exc


def is_available():
    """True if PatternFinder is installed and the 5 known fixes applied
    cleanly. Check this before showing any pattern-search UI -- a
    missing/broken git-only dependency in one deployment shouldn't take
    down the rest of the app (see this module's own docstring)."""
    _apply_patches()
    return _PATCHED


def unavailable_reason():
    """Human-readable reason is_available() is False, or None."""
    _apply_patches()
    return str(_IMPORT_ERROR) if _IMPORT_ERROR else None


def extract_query_from_measures(part, start_measure, end_measure):
    """Builds a plain, disconnected music21 Stream of the notes in
    `part` (a Part from an already-parsed Score) between measure
    numbers `start_measure` and `end_measure` (inclusive) -- exactly
    the shape Finder's own doctests expect for a query pattern (a bare
    Stream of Note objects, not a Part still attached to its original
    Score). Rests are skipped -- PatternFinder's own point-set model
    has no representation for a rest, only notes (checked directly:
    NotePointSet only ever processes score.flat.notes)."""
    import music21 as m21

    query = m21.stream.Stream()
    for m in part.getElementsByClass('Measure'):
        if m.number < start_measure or m.number > end_measure:
            continue
        for n in m.recurse().notes:
            query.append(copy.deepcopy(n))
    return query


def find_pattern_occurrences(query, source, algorithm='P1', **kwargs):
    """Runs PatternFinder's Finder(query, source, algorithm=algorithm,
    **kwargs) and returns a list of plain dicts (never raw PatternFinder
    objects -- callers shouldn't need to know its internals), one per
    occurrence found:
        {'notes': [pitch names, e.g. 'G4'], 'measures': (first, last)}

    algorithm: 'P1' (exact match, transposition-invariant) or 'P2'
    (approximate match -- pass mismatches=N as a kwarg for how many
    non-matching notes to tolerate). No other algorithm is supported --
    see this module's own docstring for why (P3 and the S/W family
    have a real, unresolved bug, not exposed here).

    Raises RuntimeError (with the original exception's message) if
    PatternFinder isn't available at all -- check is_available() first
    if you want to show a graceful message instead of catching this.
    """
    if algorithm not in ('P1', 'P2'):
        raise ValueError(f"Only 'P1' or 'P2' are supported (real, verified bugs block "
                          f"every other algorithm) -- got {algorithm!r}.")
    _apply_patches()
    if not _PATCHED:
        raise RuntimeError(f"PatternFinder isn't available: {_IMPORT_ERROR}")

    from patternfinder.geometric_helsinki.finder import Finder

    finder = Finder(query, source, algorithm=algorithm, **kwargs)
    results = []
    for occurrence in finder:
        notes = list(occurrence.notes)
        if not notes:
            continue
        measure_numbers = [n.measureNumber for n in notes if n.measureNumber is not None]
        results.append({
            'notes': [n.pitch.nameWithOctave for n in notes],
            'measures': (min(measure_numbers), max(measure_numbers)) if measure_numbers else None,
        })
    return results
