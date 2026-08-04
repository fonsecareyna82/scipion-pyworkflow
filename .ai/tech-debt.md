# Tech debt — scipion-pyworkflow

Findings from a real audit of this repo (2026-08-04), not a wishlist. Cited so they're checkable, not just asserted.

## Explicit TODO/FIXME markers worth knowing about

- `pyworkflow/gui/graph.py:32` — `# TODO: all LevelTree code is DEPRECATED...remove it after cleaning`
- `pyworkflow/viewer.py:181` — `# FIXME: REMOVE THIS METHOD AFTER RE-FACTORING`
- `pyworkflow/viewer.py:333` — `# TODO deprecate this method, it's duplicate of one from pwutils.utils` (self-acknowledged duplication)
- `pyworkflow/utils/dataset.py:364` — `# FIXME: Move this to scipion-em? Maybe remove the whole module that is not used?` — a direct signal this module may be misplaced or dead; worth checking usage before touching it.
- `pyworkflow/gui/project/project.py:324` — `# FIXME: This import should not be here`
- `pyworkflow/object.py:100,110,114` — `hasAttribute`/`setAttributeValue` marked in comments as inconsistently named/asymmetric, unresolved.
- `pyworkflow/object.py:1347` — `# FIXME: Incrementing always!! When updating this is wrong.` — potential real bug in core object logic, not yet triaged.
- `pyworkflow/plugin.py:610,733` — `# FIXME: quick and dirty way to filter` and fragile basename-based matching.

60 total TODO/FIXME/XXX/HACK markers repo-wide as of this audit — the above are the ones that describe a concrete problem, not noise.

## Cross-repo layering issues

- `pyworkflow/utils/process.py:103-104` rewrites the program name `xmipp` → `xmipp_mpi` inside the generic command-execution engine — Xmipp-specific (EM-plugin-specific) logic living in the domain-agnostic core layer.
- `pyworkflow/gui/text.py` and `pyworkflow/gui/canvas.py:893` reference `xmippLib` directly, with a comment noting "these are not used and depend on xmippLib" — dead code with an unwanted dependency, candidate for removal.

## Duplication

- `progInPath()` in `scipion-app`'s `scipion/install/funcs.py:63` reimplements what `pyworkflow/utils/which.py` (`which()`/`whichall()`/`whichgen()`) already provides — done deliberately per its own comment ("has to run with all python versions... so it is simplified"), but still a maintenance-burden duplication worth being aware of if `which.py` ever changes.
- Download/HTTP handling is reimplemented independently in `pyworkflow/webservices/{workflowhub.py,notifier.py}` rather than sharing one helper — not necessarily wrong, but no shared abstraction exists if one were ever wanted.

## Largest files (size as a complexity signal, not a verdict)

`pyworkflow/protocol/protocol.py` (2996 lines), `pyworkflow/gui/form.py` (2728 lines), `pyworkflow/project/project.py` (2132 lines). All three are central, high-traffic files — expect any change here to have wide blast radius; don't assume a quick local fix stays local.

## Runtime deprecation check

`python -W error::DeprecationWarning -c "import pyworkflow"` (Python 3.8, `scipion-devel` env) exits clean — no active `DeprecationWarning`s fire on import as of this audit. The debt above is structural/documented-in-comments, not currently surfacing as runtime warnings.
