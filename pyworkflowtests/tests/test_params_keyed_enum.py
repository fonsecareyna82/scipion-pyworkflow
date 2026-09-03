#!/usr/bin/env python
"""Coverage for KeyedEnumParam (pyworkflow/protocol/params.py) -- the
EnumParam variant whose stored/compared value is a stable string key
instead of a positional index, used by CapabilityProvider-driven choice
lists that can differ in size/order between runs (see
pyworkflow.capability / test_capability.py)."""
import pyworkflow.object as pwobj
import pyworkflow.protocol as pwprot
from pyworkflow.protocol.params import KeyedEnumParam


def test_choicesNormalizeTuplesAndPlainStrings():
    param = KeyedEnumParam(choices=[('cryosparc', 'cryoSPARC'), 'xmipp3'])
    assert param.choices == [('cryosparc', 'cryoSPARC'), ('xmipp3', 'xmipp3')]
    assert param.getChoiceKeys() == ['cryosparc', 'xmipp3']


def test_getChoiceLabelFallsBackToKeyWhenNotFound():
    param = KeyedEnumParam(choices=[('cryosparc', 'cryoSPARC')])
    assert param.getChoiceLabel('cryosparc') == 'cryoSPARC'
    # A previously-selected format that is no longer registered (e.g. its
    # plugin got uninstalled) must not raise -- just echo the key back.
    assert param.getChoiceLabel('gone') == 'gone'


def test_valueIsStoredAsString():
    param = KeyedEnumParam(choices=['files'])
    assert param.paramClass is pwobj.String


class _ProtKeyedEnum(pwprot.Protocol):
    """ Minimal protocol exercising a KeyedEnumParam-gated conditional
    field, mirroring how ProtImportFiles/ProtImportParticles will use it:
    a selector param plus one field per choice, each condition tied to a
    string KEY rather than an ordinal. """

    def _defineParams(self, form):
        form.addSection('Import')
        form.addParam('importFrom', KeyedEnumParam,
                     choices=[('files', 'Files'), ('cryosparc', 'cryoSPARC')],
                     default='files')
        form.addParam('csFile', pwprot.FileParam,
                     condition="importFrom == 'cryosparc'")


def test_conditionEvaluatesByStringKeyNotIndex():
    prot = _ProtKeyedEnum(importFrom='cryosparc')

    assert prot.importFrom.get() == 'cryosparc'
    assert prot._definition.evalParamCondition('csFile') is True


def test_conditionIsFalseForOtherKeys():
    prot = _ProtKeyedEnum(importFrom='files')

    assert prot._definition.evalParamCondition('csFile') is False


def test_defaultAppliesWhenNotProvided():
    prot = _ProtKeyedEnum()

    assert prot.importFrom.get() == 'files'
    assert prot._definition.evalParamCondition('csFile') is False
