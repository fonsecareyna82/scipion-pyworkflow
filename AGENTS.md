# scipion-pyworkflow — developer manual for AI agents

Read this before making changes here. It's written for an AI coding agent, not end users — see `README.rst` for that.

For deeper, less-frequently-needed context, see:
- [`.ai/tech-debt.md`](.ai/tech-debt.md) — known problem areas, with file:line
- [`.ai/roadmap.md`](.ai/roadmap.md) — planned/likely future work (draft, pending team review)

## What this repo is

The core workflow engine underlying Scipion. Domain-agnostic by design — it knows nothing about electron microscopy specifically. It's the bottom of a dependency chain: `scipion-pyworkflow` ← `scipion-em` (EM domain layer) ← `scipion-app` (installer/launcher) ← external plugins (scipion-em-xmipp, scipion-em-relion, etc., not in this workspace).

## Architecture map

- `pyworkflow/object.py` — the ORM/data-model base: `Object`, `Pointer`, `List`, `Set` (SQLite-backed, lazy-loaded via `_getMapper()`), scalar wrappers (`String`, `Integer`, ...). Nearly everything else in the ecosystem is built on this.
- `pyworkflow/protocol/protocol.py` (~3000 lines) — `Step`, `FunctionStep`, and `Protocol(Step)`, the base class every EM protocol (in scipion-em and external plugins) inherits from.
- `pyworkflow/mapper/` — generic SQLite persistence layer (`mapper.py`, `sqlite.py`, `sqlite_db.py`).
- `pyworkflow/plugin.py` — `Domain` (plugin discovery via `importlib_metadata.entry_points(group='pyworkflow.plugin')`) and `Plugin` (abstract base every plugin module subclasses). This is how the whole ecosystem wires together at runtime instead of via hard imports.
- `pyworkflow/project/` — project/manager/config: on-disk project structure, `hosts.conf` handling.
- `pyworkflow/gui/` — the Tkinter desktop UI. **Being phased out** — ScipionAPI (state/event API) + ScipionWeb (React frontend) are the intended replacement. Don't invest effort here beyond what's asked.
- `pyworkflow/apps/` — CLI entry-point scripts (`pw_project.py`, `pw_manager.py`, `pw_viewer.py`, ...), each runnable directly with `python pyworkflow/apps/pw_X.py`.
- `pyworkflow/tests/tests.py` — defines `BaseTest`/`DataSet`, the **public, ecosystem-shared test base classes**. Confirmed (via GitHub code search) to be subclassed by real external plugins including `scipion-em-relion`, `scipion-em-prody`, `scipion-em-spider`, `scipion-em-imagic`, and `I2PC/scipion-em-xmipp` itself. **Never rewrite or restructure this file** — it's outside this repo's control to coordinate a breaking change.
- `pyworkflowtests/tests/` — this repo's own test suite, pytest-native (`test_*` functions, fixtures, `conftest.py`). Free to modify — nothing external depends on it.

## Conventions actually used here (not aspirational)

- **camelCase** throughout the public API (`getObjId`, `setObjLabel`, `_insertFunctionStep`, ...) — this is the real, established convention, not something to "fix" toward snake_case without a deliberate, separately-scoped, additive migration.
- Informal triple-quote docstrings, not strict Sphinx/NumPy format. Some methods use `:param x:` style, most don't — match whatever the surrounding file already does.
- Every `.py` file starts with a ~25-line GPL header/authors block. Keep it when editing existing files; don't add one to new small helper files unless matching a sibling.
- Deferred/inline imports (inside functions/methods, not at module top) are used deliberately in places to avoid import cycles — don't "clean up" one without checking why it's there.
- Default to writing no comments explaining *what* code does; only comment non-obvious *why* (a hidden constraint, a workaround, a subtle invariant).

## Testing

- Two test suites coexist on purpose: `pyworkflow/tests/tests.py` (`BaseTest`, legacy-style, public/shared — do not touch) and `pyworkflowtests/tests/` (this repo's own, modern pytest, safe to extend).
- Run: `pip install -e .[test]` then `pytest -m "not gui"` (GUI/tkinter tests are marked `gui` and need `xvfb-run`; see `.github/workflows/test.yml` for the exact CI invocation).
- `[project.optional-dependencies] test` in `pyproject.toml` pins `pytest`/`pytest-cov`/`pytest-env` conditionally on `python_version` — each tool's newer major version raises its own floor (verified against PyPI `requires-python` metadata). Don't collapse this back to a single version without re-checking those floors.
- CI matrix: Python 3.8–3.12, two jobs (`test`, `gui`). 3.13/3.14 are explicitly out of scope — `numpy`'s pin here has no wheels past cp312, and bumping it needs cross-repo (Xmipp ABI) coordination, not a local decision.

## Known gotchas

- **`SCIPION_HOME` must be set before `pyworkflow.config.Config` is first imported**, or it silently defaults to `os.getcwd()` and breaks path resolution downstream (e.g. `Project._loadHosts`). This is why `pyproject.toml` sets it via `pytest-env`'s `D:` prefix rather than a plain `conftest.py` — a `conftest.py` living inside a package whose `__init__.py` imports pyworkflow is already too late.
- `List.__getattr__`/`__setattr__` (`pyworkflow/object.py:982-993`) has magic-attribute behavior — attributes starting with `__item__` are treated as list indices, and `setattr` with an empty name does an `append`. Easy to misread as a bug.
- `Set` (`pyworkflow/object.py` ~line 1112) is lazy and SQLite-backed — it opens a connection on demand via `_getMapper()`. Iterating it twice, or across processes, needs understanding `_mapperPath`/`load()` first.
- `Domain.registerPlugin` (`pyworkflow/plugin.py:87-134`) swallows plugin import errors with just a log warning — a broken external plugin won't crash startup, which also means it's easy to silently "lose" a plugin's protocols/viewers without noticing.
- Plugin name collisions are resolved by priority/logging, not by raising — see `pyworkflow/plugin.py:269-291`.

## If you're about to touch `pyworkflow/tests/tests.py`, `object.py`, or `plugin.py`

These are the highest-blast-radius files in the ecosystem (used directly or transitively by every downstream repo and every external plugin). Prefer additive changes; if a change looks like it needs to be behavioral, flag it explicitly rather than proceeding — the actual impact usually can't be assessed from this repo alone (see `.ai/tech-debt.md` for confirmed cross-repo dependents).
