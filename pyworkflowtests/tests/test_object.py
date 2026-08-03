#!/usr/bin/env python
# -*- coding: utf-8 -*-
# **************************************************************************
# *
# * Authors:     J.M. De la Rosa Trevin (delarosatrevin@scilifelab.se) [1]
# *
# * [1] SciLifeLab, Stockholm University
# *
# * This program is free software: you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation, either version 3 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program.  If not, see <https://www.gnu.org/licenses/>.
# *
# *  All comments concerning this program package may be sent to the
# *  e-mail address 'scipion@cnb.csic.es'
# *
# **************************************************************************
import datetime as dt
import os
from logging import DEBUG, lastResort
from time import sleep

try:
    from datetime import UTC  # python 3.11+
except ImportError:
    UTC = dt.timezone.utc

import pytest

import pyworkflow.object as pwobj
from pyworkflow.mapper.sqlite import CREATION, ID
from pyworkflowtests.objects import (Complex, MockAcquisition, MockImage,
                                      MockMicrograph, MockObject, MockSetOfImages)

from .conftest import assertIsNotEmpty, assertSetSize, compareSetProperties

IMAGES_STK = "images.stk"

NUMERIC_ATRIBUTE_NAME = "1"

NUMERIC_ATTRIBUTE_VALUE = "numeric_attribute"


class ListContainer(pwobj.Object):
    def __init__(self, **args):
        pwobj.Object.__init__(self, **args)
        self.csv = pwobj.CsvList()


def test_ObjectsDict():
    # Validate that the object dict is populated correctly
    basicObjNames = [
        'Scalar', 'Integer', 'Float', 'String', 'Pointer', 'Boolean',
        'OrderedObject', 'List', 'CsvList', 'PointerList', 'Set'
    ]
    assert all(name in pwobj.OBJECTS_DICT for name in basicObjNames)


def test_Object():
    value = 2
    i = pwobj.Integer(value)
    assert value == i.get()
    # compare objects
    i2 = pwobj.Integer(value)
    assert i == i2

    value = 2.
    f = pwobj.Float(value)
    assert value == pytest.approx(f.get())

    f.multiply(5)
    assert value * 5 == pytest.approx(f.get())

    a = pwobj.Integer()
    assert a.hasValue() is False
    c = Complex.createComplex()
    # Check values are correct
    assert c.imag.get() == Complex.cGold.imag
    assert c.real.get() == Complex.cGold.real

    # Test Boolean logic
    b = pwobj.Boolean(False)
    assert not b.get()

    b.set('True')
    assert b.get()

    b = pwobj.Boolean()
    b.set(False)
    assert not b.get()

    # CsvList should be empty if set to ''
    l = pwobj.CsvList()
    l.set('')
    assert len(l) == 0

    # Test emptiness
    assertIsNotEmpty(b)


def test_WithPointer():
    obj = pwobj.Integer(10)

    assert not obj.hasPointer(), "Default instantiation off Integer has a pointer."
    assert obj.get() == 10, "Integer.get(), without pointer fails."

    pointee = pwobj.Object()
    setattr(pointee, "value", pwobj.Integer(20))

    # Set a pointer (not a real case though, but enough here)
    obj.setPointer(pwobj.Pointer(pointee, extended='value'))

    assert obj.get() == 20, "Integer.get() fails with a pointer."


def test_String():
    value = 'thisisastring'
    s = pwobj.String(value)
    assert value == s.get()
    assert s.hasValue() is True

    s2 = pwobj.String()
    # None value is considered empty
    assert s2.empty(), "s2 string should be empty if None"
    s2.set(' ')
    # Only spaces is also empty
    assert s2.empty(), "s2 string should be empty if only spaces"
    s2.set('something')
    # No empty after some value
    assert not s2.empty(), "s2 string should not be empty after value"

    now = dt.datetime.now()
    s.set(now)
    assert now == s.datetime()

    # Ranges and values
    s2.set("1 2 3 4")
    assert s2.getListFromValues(caster=float) == [1., 2., 3., 4.]
    assert s2.getListFromRange() == [1, 2, 3, 4]

    # Values ...
    s2.set("2x4, 4, 7")
    assert s2.getListFromValues() == [4, 4, 4, 7]

    # Values ...
    assert s2.getListFromValues(caster=str) == ["2x4", "4", "7"]

    # Ranges
    s2.set("2-8, 1-2, 7")
    assert s2.getListFromRange() == [2, 3, 4, 5, 6, 7, 8, 1, 2, 7]


def test_Pointer(testOutputPath):
    c = Complex.createComplex()
    p = pwobj.Pointer()
    p.set(c)
    p.setExtended('Name')
    c.Name = pwobj.String('Paquito')

    assert p.get() == 'Paquito'
    stackFn = IMAGES_STK
    mrcsFn = "images.mrcs"
    fn = os.path.join(testOutputPath, 'test_images.sqlite')
    imgSet = MockSetOfImages(filename=fn)
    imgSet.setSamplingRate(1.0)
    for i in range(10):
        img = MockImage()
        img.setLocation(i + 1, stackFn)
        imgSet.append(img)

    imgSet.write()

    # Test that image number 7 is correctly retrieved
    # from the set
    img7 = imgSet[7]
    assert img7.getFileName() == stackFn

    # Modify some properties of image 7 to test update
    img7.setFileName(mrcsFn)
    img7.setSamplingRate(2.0)
    imgSet.update(img7)
    # Write changes after the image 7 update
    imgSet.write()

    # Read again the set to be able to retrieve elements
    imgSet = MockSetOfImages(filename=fn)

    # Validate that image7 was properly updated
    img7 = imgSet[7]
    assert img7.getFileName() == mrcsFn

    o = MockObject()

    o.pointer = pwobj.Pointer()
    o.pointer.set(imgSet)

    # This is not true anymore and is allowed unless we see is needed
    # The main reason is a boost in performance.
    # o.refC = o.pointer.get()
    # attrNames = [k for k, a in o.getAttributes()]
    # # Check that 'refC' should not appear in attributes
    # # since it is only an "alias" to an existing pointed value
    # assert 'refC' not in attrNames

    assert not o.pointer.hasExtended(), 'o.pointer should not have extended at this point'

    o.pointer.setExtended(7)

    assert o.pointer.hasExtended()
    assert o.pointer.hasExtended()
    assert o.pointer.getExtended() == "7"

    # Check that the Item 7 of the set is properly
    # retrieved by the pointer after setting the extended to 7
    assert imgSet[7].getObjId() == o.pointer.get().getObjId()

    # Test the keyword arguments of Pointer constructor
    # repeat above tests with new pointer
    ptr = pwobj.Pointer(value=imgSet, extended=7)
    assert ptr.hasExtended()
    assert ptr.hasExtended()
    assert ptr.getExtended() == "7"

    # Check that the Item 7 of the set is properly
    # retrieved by the pointer after setting the extended to 7
    assert imgSet[7] == ptr.get()

    o2 = pwobj.Object()
    o2.outputImages = imgSet
    ptr2 = pwobj.Pointer()
    ptr2.set(o2)
    # Test nested extended attributes
    ptr2.setExtended('outputImages.7')
    assert imgSet[7] == ptr2.get()

    # Same as ptr2, but setting extended in constructor
    ptr3 = pwobj.Pointer(value=o2, extended='outputImages.7')
    assert imgSet[7] == ptr3.get()

    # Test copy between pointer objects
    ptr4 = pwobj.Pointer()
    ptr4.copy(ptr3)
    assert imgSet[7] == ptr4.get()
    assert ptr4.getExtended() == 'outputImages.7'

    # Test numeric attributes.
    setattr(o2, NUMERIC_ATRIBUTE_NAME, NUMERIC_ATTRIBUTE_VALUE)
    ptr5 = pwobj.Pointer(value=o2, extended=NUMERIC_ATRIBUTE_NAME)
    assert NUMERIC_ATTRIBUTE_VALUE == ptr5.get()


def test_Sets(testOutputPath):
    stackFn = IMAGES_STK
    fn = os.path.join(testOutputPath, 'test_images2.sqlite')

    imgSet = MockSetOfImages(filename=fn)

    halfTimeStamp = None

    for i in range(10):
        img = MockImage()
        img.setLocation(i + 1, stackFn)
        img.setSamplingRate(i % 3)
        imgSet.append(img)
        if i == 4:
            sleep(1)
            halfTimeStamp = dt.datetime.now(UTC).replace(microsecond=0)
    imgSet.write()

    # Test size is 10
    assertSetSize(imgSet, 10)

    # Test hasChangedSince
    timeStamp = dt.datetime.now()
    assert not imgSet.hasChangedSince(timeStamp), "Set.hasChangedSince returns true when it hasn't changed."
    # Remove 10 seconds
    assert imgSet.hasChangedSince(timeStamp - dt.timedelta(0, 10)), "Set.hasChangedSince returns false when it has changed."

    # PERFORMANCE functionality
    def checkSetIteration(limit, skipRows=None):
        expectedId = 1 if skipRows is None else skipRows + 1
        index = 0
        for item in imgSet.iterItems(limit=(limit, skipRows)):
            assert item.getIndex() == expectedId + index, "Wrong item in set when using limits."
            index += 1

        assert index == limit, "Number of iterations wrong with limits"

    # Check iteration with limit
    checkSetIteration(2)

    # Check iteration with limit and skip rows
    checkSetIteration(3, 2)

    # Tests unique method
    # Requesting 1 unique value as string
    result = imgSet.getUniqueValues("_samplingRate")
    assert len(result) == 3, "Unique values wrong for 1 attribute and 3 value"

    # Requesting 1 unique value as list
    result = imgSet.getUniqueValues(["_samplingRate"])
    assert len(result) == 3, "Unique values wrong for 1 attribute and one value as list"

    # Requesting several unique values as string
    result = imgSet.getUniqueValues("_index")
    assert len(result) == 10, "Unique values wrong for id attribute"

    # Requesting several unique values with several columns
    result = imgSet.getUniqueValues(["_filename", "_samplingRate"])
    # Here we should have 2 keys containing 2 list
    assert len(result) == 2, "Unique values dictionary length wrong"
    assert len(result["_filename"]) == 3, "Unique values dict item size wrong"

    # Requesting unique values with where
    result = imgSet.getUniqueValues("_index", where="_samplingRate = 2")
    # Here we should have 2 values
    assert len(result) == 3, "Unique values with filter not working"

    # Request id list
    result = imgSet.getUniqueValues(ID)
    # Here we should have 10 values
    assert len(result) == 10, "Unique values with ID"

    # Use creation timestamp
    # Request id list
    result = imgSet.getUniqueValues(ID, where="%s>=%s" % (CREATION, imgSet.fmtDate(halfTimeStamp)))
    assert len(result) == 5, "Unique values after a time stamp does not work"

    # Test getIdSet
    ids = imgSet.getIdSet()
    assert isinstance(ids, set), "getIdSet does not return a set"
    assert isinstance(next(iter(ids)), int), "getIdSet items are not integer"
    assert len(ids) == 10, "getIdSet does not return 10 items"

    # Request item by id
    item = imgSet[1]
    assert item.getObjId() == 1, "Item accessed by [] and id does not work"

    # Request item by field
    item = imgSet.getItem("id", 2)
    assert item.getObjId() == 2, "Item accessed field id does not work"

    # Test load properties queries
    from pyworkflow.mapper.sqlite_db import logger
    logger.setLevel(DEBUG)
    lastResort.setLevel(DEBUG)
    imgSetVerbose = MockSetOfImages(filename=fn)
    imgSetVerbose.loadAllProperties()

    # Compare sets are "equal"
    compareSetProperties(imgSet, imgSetVerbose, ignore=[])


def test_copyAttributes():
    """ Check that after copyAttributes, the values
    were properly copied.
    """
    c1 = Complex(imag=10., real=11.)
    c2 = Complex(imag=0., real=1.0001)

    # Float values are different, should not be equal
    assert not c1.equalAttributes(c2)
    c2.copyAttributes(c1, 'imag', 'real')

    assert c1.equalAttributes(c2), (
        'Complex c1 and c2 have not equal attributes'
        '\nc1: %s\nc2: %s\n' % (c1, c2)
    )

    c1.score = pwobj.Float(1.)

    # If we copyAttributes again, score dynamic attribute should
    # be set in c2
    c2.copyAttributes(c1, 'score')
    assert hasattr(c2, 'score')


def test_equalAttributes():
    """ Check that equal attributes function behaves well
    to compare floats with a given precision.
    """
    c1 = Complex(imag=0., real=1.)
    c2 = Complex(imag=0., real=1.0001)

    # Since Float precision is 0.001, now c1 and c2
    # should have equal attributes
    assert c1.equalAttributes(c2)
    # Now if we set a more restrictive precision
    # c1 and c2 are not longer equals
    pwobj.Float.setPrecision(0.0000001)
    assert not c1.equalAttributes(c2)


def test_formatString():
    """ Test that Scalar objects behave well
    when using string formatting such as: %f or %d
    """
    i = pwobj.Integer(10)
    f = pwobj.Float(3.345)

    s1 = "i = %d, f = %0.3f" % (i, f)

    assert s1 == "i = 10, f = 3.345"


def test_getObjDict():
    """ Test retrieving an object dictionary with its attribute values."""
    acq1 = MockAcquisition(magnification=50000,
                            voltage=200,
                            sphericalAberration=2.7,
                            dosePerFrame=1)
    m1 = MockMicrograph(
        'my_movie.mrc', objId=1, objLabel='test micrograph',
        objComment='Testing store and retrieve from dict.')
    m1.setSamplingRate(1.6)
    m1.setAcquisition(acq1)
    m1Dict = m1.getObjDict(includeBasic=True)

    goldDict1 = dict([
        ('object.id', 1),
        ('object.label', 'test micrograph'),
        ('object.comment', 'Testing store and retrieve from dict.'),
        ('_index', 0),
        ('_filename', 'my_movie.mrc'),
        ('_samplingRate', 1.6),
        ('_micName', None),
        ('_acquisition', None),
        ('_acquisition._magnification', 50000.0),
        ('_acquisition._voltage', 200.0),
        ('_acquisition._sphericalAberration', 2.7),
        ('_acquisition._amplitudeContrast', None),
        ('_acquisition._doseInitial', 0.0),
        ('_acquisition._dosePerFrame', 1.0),
    ])

    assert goldDict1 == m1Dict


def test_Dict():
    d = pwobj.Dict(default='missing')
    d.update({1: 'one', 2: 'two'})

    # Return default value for any non-present key
    assert d[10] == 'missing'

    # Return true for any 'contains' query
    assert 100 in d


def test_ListsFunctions():
    """ Test of some methods that retrieve lists from string. """
    from pyworkflow.utils import getBoolListFromValues, getFloatListFromValues, getListFromValues

    results = [
        ('2x1 2x2 4 5', getListFromValues, ['2x1', '2x2', '4', '5'], None),
        ('2x1 2x2 4 5', getFloatListFromValues, [1., 1., 2., 2., 4., 5.], None),
        ('1 2 3x3 0.5', getFloatListFromValues, [1., 2., 3., 3., 3., 0.5, 0.5, 0.5], 8),
        ('3x1 3x0 1', getBoolListFromValues, [True, True, True, False, False, False, True, True], 8),
    ]

    for s, func, goldList, length in results:
        l = func(s, length=length)
        for i in range(0, len(goldList)):
            assert l[i] == goldList[i]

        assert len(goldList) == len(l)


def test_Environ():
    """ Test the Environ class with its utilities. """
    from pyworkflow.utils import Environ

    env = Environ({'PATH': '/usr/bin:/usr/local/bin',
                    'LD_LIBRARY_PATH': '/usr/lib:/usr/lib64'})
    env1 = Environ(env)
    env1.set('PATH', '/usr/local/xmipp')
    assert env1['PATH'] == '/usr/local/xmipp'
    assert env1['LD_LIBRARY_PATH'] == env['LD_LIBRARY_PATH']

    env2 = Environ(env)
    env2.set('PATH', '/usr/local/xmipp', position=Environ.BEGIN)
    assert env2['PATH'] == '/usr/local/xmipp' + os.pathsep + env['PATH']
    assert env2['LD_LIBRARY_PATH'] == env['LD_LIBRARY_PATH']

    env3 = Environ(env)
    env3.update({'PATH': '/usr/local/xmipp',
                 'LD_LIBRARY_PATH': '/usr/local/xmipp/lib'},
                position=Environ.END)
    assert env3['PATH'] == env['PATH'] + os.pathsep + '/usr/local/xmipp'
    assert env3['LD_LIBRARY_PATH'] == env['LD_LIBRARY_PATH'] + os.pathsep + '/usr/local/xmipp/lib'


def test_dottedAttributeAccess():
    o = pwobj.Object()
    o.child = pwobj.Object()
    o.child.value = pwobj.Integer(5)

    assert o.hasAttributeExt('child.value')
    assert not o.hasAttributeExt('child.missing')
    assert not o.hasAttributeExt('missing.value')

    assert o.getAttributeValue('child.value') is None  # getAttributeValue does not resolve dots
    assert o.child.getAttributeValue('value') == 5

    o.setAttributeValue('child.value', 10)
    assert o.child.value.get() == 10

    # Missing attrName is ignored by default
    o.setAttributeValue('child.missing', 1)
    with pytest.raises(Exception):
        o.setAttributeValue('child.missing', 1, ignoreMissing=False)


def test_getNestedValue():
    o = pwobj.Object()
    o.child = pwobj.Object()
    o.child.value = pwobj.Integer(7)

    assert o.getNestedValue('child.value') == 7


def test_cleanObjId():
    parent = pwobj.Object()
    parent.setObjId(1)
    parent.child = pwobj.Integer(5)
    parent.child.setObjId(2)

    assert parent.hasObjId()
    assert parent.child.hasObjId()

    parent.cleanObjId()

    assert not parent.hasObjId()
    assert not parent.child.hasObjId()


def test_getNameIdAndLastName():
    o = pwobj.Object()
    assert o.getNameId() == ''

    o.setObjId(3)
    o.setName('grandparent.parent.myself')
    assert o.getNameId() == 'grandparent.parent.myself.3'
    assert o.getLastName() == 'myself'

    o.setObjLabel('a nice label')
    assert o.getNameId() == 'a nice label'


def test_isEnabled():
    o = pwobj.Object()
    assert o.isEnabled()
    o.setEnabled(False)
    assert not o.isEnabled()
    o.setEnabled(1)
    assert o.isEnabled() is True


def test_evalCondition():
    o = pwobj.Object()
    o.hasCTF = pwobj.Boolean(True)
    o.hasAlignment = pwobj.Boolean(False)

    assert o.evalCondition('hasCTF')
    assert not o.evalCondition('hasAlignment')
    assert o.evalCondition('hasCTF and not hasAlignment')
    assert not o.evalCondition('hasCTF and hasAlignment')


@pytest.mark.parametrize(
    "value, expectedType",
    [
        (5, pwobj.Integer),
        (True, pwobj.Boolean),
        (5.0, pwobj.Float),
        ([1, 2, 3], pwobj.CsvList),
        ("hello", pwobj.String),
    ],
)
def test_ObjectWrap(value, expectedType):
    wrapped = pwobj.ObjectWrap(value)
    assert isinstance(wrapped, expectedType)


def test_ObjectWrap_passthroughForObject():
    i = pwobj.Integer(5)
    assert pwobj.ObjectWrap(i) is i


def test_List():
    l = pwobj.List()
    assert l.isEmpty()
    assert l.getSize() == 0

    i1 = pwobj.Integer(1)
    i2 = pwobj.Integer(2)
    l.append(i1)
    l.append(i2)

    assert l.getSize() == 2
    assert not l.isEmpty()
    assert l[0] is i1
    assert l[1] is i2

    names = [name for name, _ in l.getAttributes()]
    assert names == ['__item__000001', '__item__000002']

    l.clear()
    assert l.isEmpty()


def test_List_setFromList():
    l = pwobj.List()
    l.set([pwobj.Integer(1), pwobj.Integer(2), pwobj.Integer(3)])
    assert l.getSize() == 3

    with pytest.raises(Exception):
        l.set("not a list")


def test_PointerList_appendWrapsObjectsInPointers():
    pl = pwobj.PointerList()
    target = pwobj.Integer(5)

    pl.append(target)
    assert isinstance(pl[0], pwobj.Pointer)
    assert pl[0].get() == 5

    p = pwobj.Pointer(target)
    pl.append(p)
    assert pl[1] is p

    with pytest.raises(Exception):
        pl.append("not an object")


def test_CsvList_fromStringAndList():
    csv = pwobj.CsvList(pType=int)
    csv.set("1,2,3")
    assert list(csv) == [1, 2, 3]
    assert csv.get() == "1,2,3"

    csv2 = pwobj.CsvList(pType=int)
    csv2.set([1, 2, 3])
    assert csv == csv2

    assert not csv.isEmpty()
    csv.clear()
    assert csv.isEmpty()


def test_Scalar_comparisons():
    a = pwobj.Integer(1)
    b = pwobj.Integer(2)

    assert a < b
    assert a <= b
    assert a <= pwobj.Integer(1)
    assert b > a
    assert b >= a
    assert a != b
    assert not (a == b)


def test_Scalar_swap():
    a = pwobj.Integer(1)
    b = pwobj.Integer(2)
    a.swap(b)
    assert a.get() == 2
    assert b.get() == 1


def test_Integer_increment():
    i = pwobj.Integer(1)
    i.increment()
    assert i.get() == 2


def test_Float_equalAttributes_bothNone():
    f1 = pwobj.Float()
    f2 = pwobj.Float()
    assert f1.equalAttributes(f2)

    f1.set(1.0)
    assert not f1.equalAttributes(f2)
