# CapabilityProvider — plugin registry contract

Introduced to replace the pattern where a pwem protocol (e.g. `ProtImportParticles`) hardcodes
the full list of external-plugin formats it supports, plus each plugin's specific form fields,
plus a manual `elif` dispatch keyed to `Domain.importFromPlugin(...)`. The menu was always shown
in full regardless of whether the plugin was actually installed — failure only surfaced at
execution time. See `scipion-em`'s `.ai/` docs for how `ProtImportFiles`/`ProtImportParticles`
consume this; this file documents the contract itself, which lives here because it is generic —
import is the first consumer, not the only one intended.

## The contract

`pyworkflow.capability.CapabilityProvider` is the base class. A plugin subclasses it (or, more
commonly, a capability-specific subclass such as `ImportCapabilityProvider`) and declares:

- `CAPABILITY` — identifies the family of capability (`'import'` today). Each capability family
  gets its own `CapabilityProvider` subclass adding whatever execution method(s) it needs — the
  base class stays deliberately minimal (`CAPABILITY`, `TARGET_PROTOCOLS`, `KEY`, `LABEL`,
  `defineParams`) so a brand-new capability family never requires touching the discovery
  machinery in `pyworkflow/plugin.py`.
- `TARGET_PROTOCOLS` — list of **plain protocol class names** (not fully-qualified), matched
  against `protocolClass.mro()` the same way `Wizard._targets`/`Domain.findWizards` already do.
- `KEY` — a stable string identity. Persisted as the value of the protocol's selector param
  (`pyworkflow.protocol.params.KeyedEnumParam`, not `EnumParam`) and used verbatim inside a
  `condition=` expression (e.g. `"importFrom == 'cryosparc'"`). **Must never change once
  released** — unlike a plain `EnumParam` ordinal, this is not a list position, so the choice
  list can grow/shrink/reorder between runs (a plugin gets installed/uninstalled) without
  invalidating previously-saved protocol runs. This is the whole point of the design — see
  `pyworkflowtests/tests/test_params_keyed_enum.py` for the direct evidence that condition
  evaluation works on the string value, not an index.
- `LABEL` — text shown in the dropdown.
- `defineParams(self, form, condition)` — the plugin adds its own fields here, each gated by the
  exact `condition` string passed in, so they only render once this provider is selected. This is
  what lets ScipionAPI/ScipionWeb render the plugin's form fragment without either of those repos
  knowing anything about the plugin — see their own `.ai/`/`AGENTS.md` notes.

`ImportCapabilityProvider(CapabilityProvider)` additionally declares `importFrom(self, protocol)`,
replacing the logic that used to live inline in each import protocol's `getImportClass()`-style
dispatch.

## Discovery: entry-points, not submodule scan

Unlike `Wizard`/`Viewer` (discovered via `Domain.__getSubclasses`, which imports every installed
plugin's fixed-name submodule — `wizards.py`, `viewers.py` — just to inspect it), capability
providers are discovered through a single setuptools entry-point group:

```
pyworkflow.capability_provider
```

A plugin registers one entry point per provider class in its `pyproject.toml`/`setup.py`, e.g.:

```toml
[project.entry-points."pyworkflow.capability_provider"]
cryosparc-particles-import = "cryosparc2.convert.dataimport:CryoSparcParticlesImport"
```

`Domain._discoverCapabilityProviders` (`pyworkflow/plugin.py`) reads this group via
`importlib_metadata.entry_points(group=...)` and only calls `entry_point.load()` — which resolves
and imports the target class — once, on first use (cached via `_capabilityProviders`/
`_capabilityProvidersLoaded`, same lazy-once pattern as `Domain.getPlugins()`). This is a
deliberate departure from the submodule-scan pattern: entry-point metadata is readable from the
installed package's metadata without importing the plugin at all, so listing "what capability
providers exist" never has the cost or risk of importing N unrelated plugin packages. The cost
plugin authors pay is real, not free: registering requires editing packaging metadata, not just
dropping a class into a conventionally-named module.

`Domain.getCapabilityProviders(capability=None)` returns provider instances, optionally filtered
by `CAPABILITY`. `Domain.findCapabilityProviders(capability, protocolClass)` additionally filters
by `TARGET_PROTOCOLS` against `protocolClass.mro()`.

## Failure handling

A provider that fails to load (`entry_point.load()` raises — plugin not installed, broken import,
...), that doesn't subclass `CapabilityProvider`, or that is missing `CAPABILITY`/`KEY` is logged
and skipped — it never appears in `getCapabilityProviders()`/`findCapabilityProviders()`, and it
never crashes discovery for the other providers. This is the direct fix for the original problem:
the choice list a protocol builds from `findCapabilityProviders(...)` only ever contains formats
that are genuinely usable right now, instead of a hardcoded list that fails late.

## Keeping this document current

This is new infrastructure — if the discovery mechanism, the contract's required attributes, or
the entry-point group name change, update this file in the same change, not as a follow-up.
