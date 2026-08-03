#!/usr/bin/env python
"""Import-smoke coverage for pyworkflow/gui/.

Only ~1 of the ~19 modules here gets imported anywhere else in the test
suite (test_canvas.py). This just makes sure the rest still import
cleanly across the Python version matrix - it does not instantiate any
widgets, drive any GUI interaction, or otherwise test behavior.
"""
import importlib
import pkgutil

import pytest

import pyworkflow.gui


def _guiModuleNames():
    return sorted(
        name
        for _, name, _ in pkgutil.walk_packages(
            pyworkflow.gui.__path__, prefix="pyworkflow.gui."
        )
    )


@pytest.mark.gui
@pytest.mark.parametrize("moduleName", _guiModuleNames())
def test_guiModuleImports(moduleName):
    importlib.import_module(moduleName)
