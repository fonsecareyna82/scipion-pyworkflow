#!/usr/bin/env python
"""Coverage for the Validator hierarchy in pyworkflow/protocol/params.py -
previously entirely untested despite being real, pure validation logic
used by every protocol param definition."""
import pytest

from pyworkflow.protocol.params import (
    GE, GT, LE, LT, Conditional, FreqValidator, IntParam, NonEmptyCondition,
    NonEmptyBoolCondition, NumericListValidator, NumericRangeValidator, Param,
    Positive, Range,
)


def test_LT_GT_LE_GE():
    assert LT(5)(3) == []
    assert LT(5)(5) != []
    assert GT(5)(6) == []
    assert GT(5)(5) != []
    assert LE(5)(5) == []
    assert LE(5)(6) != []
    assert GE(5)(5) == []
    assert GE(5)(4) != []
    assert GE(5)(None) != []  # GE explicitly rejects None


def test_Range():
    validator = Range(1, 10)
    assert validator(5) == []
    assert validator(1) == []
    assert validator(10) == []
    assert validator(0) != []
    assert validator(11) != []


def test_NonEmptyCondition():
    validator = NonEmptyCondition()
    assert validator("something") == []
    assert validator("") != []
    assert validator([1]) == []
    assert validator([]) != []


def test_NonEmptyBoolCondition():
    validator = NonEmptyBoolCondition()
    assert validator(True) == []
    assert validator(False) == []  # False is a valid, non-empty boolean value
    assert validator(None) != []


@pytest.mark.parametrize(
    "value, valid",
    [
        ("5", True),
        ("5 10", True),
        ("2x3", True),
        ("2x3 4", True),
        ("not a number", False),
    ],
)
def test_NumericListValidator(value, valid):
    errors = NumericListValidator()(value)
    assert (errors == []) == valid


@pytest.mark.parametrize(
    "value, valid",
    [
        ("1", True),
        ("1-5", True),
        ("1-5, 8", True),
        ("not a range", False),
    ],
)
def test_NumericRangeValidator(value, valid):
    errors = NumericRangeValidator()(value)
    assert (errors == []) == valid


def test_allowsNull():
    # allowsNull isn't exposed on the GT/LT/... convenience subclasses'
    # __init__ (they hardcode the base Conditional.__init__ call without
    # forwarding it) - only Conditional itself takes it directly.
    validator = Conditional("must be positive", allowsNull=True)
    validator._condition = lambda value: value > 0

    assert validator(None) == []  # allowsNull skips the condition entirely
    assert validator(-1) != []
    assert validator(1) == []


def test_customErrorMessage():
    validator = GT(0, error="must be positive")
    assert validator(-1) == ["must be positive"]


def test_predefinedValidators():
    assert Positive(1) == []
    assert Positive(0) != []
    assert Positive(-1) != []

    assert FreqValidator(0.25) == []
    assert FreqValidator(0.5) == []
    assert FreqValidator(0.6) != []


def test_Param_validate_aggregatesAllValidatorErrors():
    param = IntParam(validators=[GT(0), LT(100)])

    assert param.validate(50) == []

    errors = param.validate(-5)
    assert len(errors) == 1  # only GT fails

    errors = param.validate(200)
    assert len(errors) == 1  # only LT fails


def test_Param_addValidator():
    param = Param()
    assert param.validate("anything") == []

    param.addValidator(NonEmptyCondition())
    assert param.validate("") != []
    assert param.validate("value") == []


def test_Param_defaultValue():
    param = Param(default=5)
    assert param.getDefault() == '5'  # default is stored as a String

    param.setDefault(10)
    assert param.getDefault() == '10'
