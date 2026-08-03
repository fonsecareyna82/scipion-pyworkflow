#!/usr/bin/env python
"""Coverage for pyworkflow/config.py - previously entirely untested despite
being load-bearing for every other test's hermeticity (this is exactly what
parses SCIPION_HOME/SCIPION_DOMAIN/SCIPION_TEST_NOSYNC)."""
import pytest

from pyworkflow.config import Config, Variable, VariablesRegistry


def test_Variable_defaultTracking():
    v = Variable("MY_VAR", "desc", "pyworkflow", "default", "default")
    assert v.isDefault

    v.setValue("changed")
    assert not v.isDefault
    assert v.value == "changed"

    v.setToDefault()
    assert v.isDefault
    assert v.value == "default"


def test_VariablesRegistry_registerAndIterateAlphabetically():
    VariablesRegistry.register(Variable("Z_VAR", "d", "pyworkflow", "1", "1"))
    VariablesRegistry.register(Variable("A_VAR", "d", "pyworkflow", "1", "1"))

    # __iter__ is a classmethod, not hooked into the standard iteration
    # protocol (VariablesRegistry is never instantiated, and `type` has no
    # __iter__), so `for x in VariablesRegistry` doesn't work - it must be
    # called explicitly, exactly like VariablesRegistry.save() does.
    names = [v.name for v in VariablesRegistry.__iter__()]
    # Registry is shared/global and other variables are registered elsewhere
    # (Config itself registers dozens at import time) - just check relative
    # ordering of the two we just added, not the full list.
    assert names.index("A_VAR") < names.index("Z_VAR")


def test_Config_get_castingFallsBackToDefaultOnFailure(monkeypatch):
    monkeypatch.setenv("PYWF_TEST_INT_VAR", "not-an-int")
    value = Config._get("PYWF_TEST_INT_VAR", 42, caster=int)
    assert value == 42


def test_Config_get_castingSucceeds(monkeypatch):
    monkeypatch.setenv("PYWF_TEST_INT_VAR2", "7")
    value = Config._get("PYWF_TEST_INT_VAR2", 0, caster=int)
    assert value == 7


def test_Config_get_emptyStringFallsBackToDefault(monkeypatch):
    monkeypatch.setenv("PYWF_TEST_EMPTY_VAR", "")
    value = Config._get("PYWF_TEST_EMPTY_VAR", "fallback")
    assert value == "fallback"


def test_Config_get_expandsUserAndVars(monkeypatch):
    monkeypatch.delenv("PYWF_TEST_PATH_VAR", raising=False)
    monkeypatch.setenv("PYWF_TEST_EXPAND_TARGET", "expanded")
    monkeypatch.setenv("PYWF_TEST_PATH_VAR", "$PYWF_TEST_EXPAND_TARGET/sub")
    value = Config._get("PYWF_TEST_PATH_VAR", "")
    assert value == "expanded/sub"


def test_Config_get_usesDefaultWhenUnset(monkeypatch):
    monkeypatch.delenv("PYWF_TEST_UNSET_VAR", raising=False)
    value = Config._get("PYWF_TEST_UNSET_VAR", "the-default")
    assert value == "the-default"


def test_Config_notFalse():
    assert Config._notFalse("True")
    assert Config._notFalse("anything")
    assert not Config._notFalse("False")


def test_Config_bool():
    # __bool is name-mangled (double underscore, no public alias exists
    # unlike _get/_notFalse) but it's real logic worth pinning down since
    # it's what casts boolean env vars.
    boolCaster = Config._Config__bool
    for truthy in ("true", "TRUE", "yes", "on", "1"):
        assert boolCaster(truthy)
    for falsy in ("false", "no", "0", "anything else"):
        assert not boolCaster(falsy)


def test_Root_join_relativePath():
    root = Config.Root("/scipion/home")
    assert root.join("software", "bindings") == "/scipion/home/software/bindings"


def test_Root_join_absoluteSecondArgOverridesRoot():
    # Documented quirk found while wiring CI: Root.join uses os.path.join,
    # which discards earlier components once a later one is itself
    # absolute. Config.SCIPION_HOSTS etc. are already absolute paths (built
    # via this same Root.join against SCIPION_HOME), so joining them again
    # against a project-relative prefix silently returns just the absolute
    # path, not a path under the project. See Project.getLocalConfigHosts.
    root = Config.Root("/scipion/home")
    assert root.join(".config", "/already/absolute/hosts.conf") == "/already/absolute/hosts.conf"
