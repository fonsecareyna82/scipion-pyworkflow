# Roadmap — scipion-pyworkflow

**Status: draft, pending review with Yunior (repo co-owner).** This is seeded from a rough team Google Doc plus findings surfaced while doing the test/CI/Python-3.8-3.12 work on this repo (2026-08-04). Treat as a starting point, not a committed plan — confirm before acting on anything here beyond what's already merged.

## This repo specifically

- Audit whether code flagged in [`.ai/tech-debt.md`](tech-debt.md) as possibly misplaced (`pyworkflow/utils/dataset.py`, the `xmipp`-specific rewrite in `pyworkflow/utils/process.py`) should actually move to `scipion-em` or be removed.
- Review core package responsibilities more broadly — what in `pyworkflow/` could be moved/eliminated now that `scipion-em`/`scipion-app` exist as separate layers.
- Keep closing real test-coverage gaps (this repo's own `pyworkflowtests/tests/` suite is modern pytest now — extend it as new gaps are found, following the same "verify against actual behavior, not assumed" discipline used when it was set up).

## Ecosystem-wide (applies to all 5 repos, not just this one)

- **Branch/release cleanup**: drop the redundant `master` branch, rename `devel` → `main` as the single branch, replace the push-triggered publish workflow with a manual `workflow_dispatch` release gated by a protected GitHub deployment environment. `I2PC/scipion-em-xmipp`'s `.github/workflows/release.yml` is a concrete, working reference (`workflow_dispatch` only, `environment: {name: release-approval}` as the approval gate, `python -m build --no-isolation`, auto-generated changelog/tag/release).
- **Remove Tkinter entirely** (`pyworkflow/gui/`) once ScipionAPI + ScipionWeb fully replace it — ScipionWeb replaces both the legacy Tkinter GUI and an intermediate NiceGUI attempt that didn't ship.
- **Convert buildbot to a GitHub Actions self-hosted runner.**
- **Set up a dependency manager (Renovate)** across all 5 repos.
- Python 3.13/3.14 support — blocked on `numpy` wheel availability and Xmipp ABI coordination, not a local decision.
