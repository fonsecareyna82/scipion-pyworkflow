#!/usr/bin/env python
"""Coverage for pyworkflow.capability.CapabilityProvider and its discovery
through pyworkflow.plugin.Domain.getCapabilityProviders/findCapabilityProviders
-- the registry backing plugin-contributed import (and future) capabilities."""
import pytest

from pyworkflow.capability import CapabilityProvider, ImportCapabilityProvider
from pyworkflow.plugin import Domain


class _FakeEntryPoint:
    """ Minimal stand-in for importlib_metadata.EntryPoint: a name plus a
    lazy `load()` -- exactly the surface Domain._discoverCapabilityProviders
    relies on. Mirrors the real EntryPoint.load() contract: it resolves and
    returns the target object (here, a CapabilityProvider *class*),
    unstantiated -- Domain does the instantiation itself. """

    def __init__(self, name, providerClass):
        self.name = name
        self._providerClass = providerClass

    def load(self):
        return self._providerClass


class _FakeImportProvider(ImportCapabilityProvider):
    TARGET_PROTOCOLS = ['ProtImportParticles']
    KEY = 'fake'
    LABEL = 'Fake format'

    def __init__(self):
        self.definedFor = None

    def defineParams(self, form, condition):
        self.definedFor = condition

    def importFrom(self, protocol):
        return 'imported:%s' % protocol


class _OtherCapabilityProvider(CapabilityProvider):
    """ A provider for a different capability family -- must never be
    returned by an 'import'-scoped query. """
    CAPABILITY = 'export'
    TARGET_PROTOCOLS = ['ProtImportParticles']
    KEY = 'fake-export'
    LABEL = 'Fake export'


class _UnrelatedTargetProvider(ImportCapabilityProvider):
    TARGET_PROTOCOLS = ['ProtImportMovies']
    KEY = 'unrelated'
    LABEL = 'Unrelated'


class _NotACapabilityProvider:
    """ Loads fine, but does not extend CapabilityProvider -- must be
    rejected, not crash discovery. """
    CAPABILITY = 'import'
    KEY = 'bogus'


class _BrokenLoader:
    name = 'broken'

    @staticmethod
    def load():
        raise ImportError('plugin not installed')


class _MissingKeyProvider(ImportCapabilityProvider):
    TARGET_PROTOCOLS = ['ProtImportParticles']
    KEY = None
    LABEL = 'Missing key'


class ProtImportParticles:
    """ Stand-in mro() target -- real class lives in scipion-em, not a
    dependency of this repo's tests. """


class ProtImportMovies:
    pass


@pytest.fixture(autouse=True)
def _resetDomainCapabilityCache():
    """ Domain caches discovery results as class attributes -- reset before
    and after each test so tests don't leak state into each other. """
    Domain._capabilityProviders = {}
    Domain._capabilityProvidersLoaded = False
    yield
    Domain._capabilityProviders = {}
    Domain._capabilityProvidersLoaded = False


def _patchEntryPoints(monkeypatch, entryPoints):
    def fakeEntryPoints(group):
        assert group == 'pyworkflow.capability_provider'
        return entryPoints

    monkeypatch.setattr(
        'pyworkflow.plugin.importlib_metadata.entry_points', fakeEntryPoints)


def test_noProvidersRegistered(monkeypatch):
    _patchEntryPoints(monkeypatch, [])
    assert Domain.getCapabilityProviders() == []
    assert Domain.findCapabilityProviders('import', ProtImportParticles) == []


def test_matchingProviderIsDiscoveredAndFiltered(monkeypatch):
    _patchEntryPoints(monkeypatch, [
        _FakeEntryPoint('fake', _FakeImportProvider),
        _FakeEntryPoint('fake-export', _OtherCapabilityProvider),
    ])

    allProviders = Domain.getCapabilityProviders()
    assert len(allProviders) == 2

    importProviders = Domain.getCapabilityProviders('import')
    assert [p.KEY for p in importProviders] == ['fake']

    matched = Domain.findCapabilityProviders('import', ProtImportParticles)
    assert len(matched) == 1
    assert matched[0].KEY == 'fake'
    assert matched[0].LABEL == 'Fake format'


def test_targetProtocolMismatchIsExcluded(monkeypatch):
    _patchEntryPoints(monkeypatch, [
        _FakeEntryPoint('unrelated', _UnrelatedTargetProvider),
    ])

    assert Domain.findCapabilityProviders('import', ProtImportParticles) == []
    matched = Domain.findCapabilityProviders('import', ProtImportMovies)
    assert [p.KEY for p in matched] == ['unrelated']


def test_brokenProviderIsSkippedNotFatal(monkeypatch):
    _patchEntryPoints(monkeypatch, [
        _BrokenLoader(),
        _FakeEntryPoint('fake', _FakeImportProvider),
    ])

    providers = Domain.getCapabilityProviders('import')
    assert [p.KEY for p in providers] == ['fake']


def test_nonCapabilityProviderClassIsRejected(monkeypatch):
    _patchEntryPoints(monkeypatch, [
        _FakeEntryPoint('bogus', _NotACapabilityProvider),
    ])

    assert Domain.getCapabilityProviders() == []


def test_providerMissingKeyIsRejected(monkeypatch):
    _patchEntryPoints(monkeypatch, [
        _FakeEntryPoint('missing-key', _MissingKeyProvider),
    ])

    assert Domain.getCapabilityProviders() == []


def test_discoveryOnlyRunsOnce(monkeypatch):
    callCount = {'n': 0}

    def fakeEntryPoints(group):
        callCount['n'] += 1
        return [_FakeEntryPoint('fake', _FakeImportProvider)]

    monkeypatch.setattr(
        'pyworkflow.plugin.importlib_metadata.entry_points', fakeEntryPoints)

    Domain.getCapabilityProviders()
    Domain.getCapabilityProviders()
    Domain.findCapabilityProviders('import', ProtImportParticles)

    assert callCount['n'] == 1


def test_defineParamsReceivesTheDispatchedCondition():
    provider = _FakeImportProvider()
    provider.defineParams(form=None, condition="importFrom == 'fake'")
    assert provider.definedFor == "importFrom == 'fake'"


def test_importCapabilityProviderRequiresOverride():
    class Incomplete(ImportCapabilityProvider):
        KEY = 'incomplete'
        LABEL = 'Incomplete'
        TARGET_PROTOCOLS = ['ProtImportParticles']

    with pytest.raises(NotImplementedError):
        Incomplete().importFrom(protocol=None)
