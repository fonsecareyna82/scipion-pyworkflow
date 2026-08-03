# **************************************************************************
# *
# * Authors:     Pablo Conesa (pconesa@cnb.csic.es) [1]
# *              J.M. De la Rosa Trevin (delarosatrevin@scilifelab.se) [2]
# *
# * [1] Unidad de  Bioinformatica of Centro Nacional de Biotecnologia , CSIC
# * [2] SciLifeLab, Stockholm University
# *
# * This program is free software; you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation; either version 3 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; if not, write to the Free Software
# * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# * 02111-1307  USA
# *
# *  All comments concerning this program package may be sent to the
# *  e-mail address 'scipion@cnb.csic.es'
# *
# **************************************************************************
import os

import pytest

import pyworkflow as pw
import pyworkflow.mapper as pwmapper
import pyworkflow.object as pwobj
import pyworkflow.protocol as pwprot
from pyworkflow.project import Project
from pyworkflowtests import Domain, MockObject
from pyworkflowtests.protocols import ProtOutputTest

from .conftest import launchProtocol


def _assertOutput(prot, value=20):
    # Check there is an output
    assert hasattr(prot, 'oBoxSize'), "Protocol output boxSize (OInteger) not registered as attribute."
    assert value == prot.oBoxSize.get(), (
        "oBoxSize value is wrong: %s , expected %s" % (prot.oBoxSize, value)
    )


def test_basicObjectOutput(testOutputPath):
    """Test the list with several Complex"""
    pw.Config.setDomain("pyworkflowtests")

    fn = os.path.join(testOutputPath, "protocol.sqlite")

    # Discover objects and protocols
    mapperDict = Domain.getMapperDict()

    mapper = pwmapper.SqliteMapper(fn, mapperDict)
    # Associate the project
    proj = Project(Domain, path=testOutputPath)

    prot = ProtOutputTest(mapper=mapper, n=2, project=proj, workingDir=testOutputPath)

    # Add and old style o, not in the outputs dictionary
    prot.output1 = MockObject()

    assert not prot._useOutputList.get(), "useOutputList wrongly initialized"

    outputs = [o for o in prot.iterOutputAttributes()]
    assert len(outputs) >= 1

    prot._stepsExecutor = pwprot.StepExecutor(hostConfig=None)

    # Create the logs folder
    prot.makeWorkingDir()

    prot.run()

    assert prot._steps[0].getStatus() == pwprot.STATUS_FINISHED

    # Check there is an output
    _assertOutput(prot)

    outputs = [o for o in prot.iterOutputAttributes()]

    # We are intentionally ignoring a protocol with o (EMObject)
    # That has been continued, We do not find a real case now.
    assert len(outputs) == 1, "Integer o not registered properly."

    outputs = [o for o in prot.iterOutputAttributes(pwobj.Integer)]

    # Test passing a filter
    assert len(outputs) == 1, "Integer not matched when filtering outputs."

    # Test with non existing class
    class NotRealClass:
        pass

    outputs = [o for o in prot.iterOutputAttributes(NotRealClass)]

    # Test passing a class
    assert len(outputs) == 0, "Filter by class in iterOutputAttributes does not work."

    assert prot._useOutputList.get(), "useOutputList not activated"


def test_basicObjectInProject(testProject):
    prot = testProject.newProtocol(ProtOutputTest, objLabel='to generate basic input')
    print("working dir: %s" % prot.getWorkingDir())
    # Define a negative output for later tests
    prot._defineOutputs(negative=pwobj.Integer(-20))
    launchProtocol(testProject, prot)

    # Default value is 10 so output is 20
    _assertOutput(prot)

    # Second protocol to test linking
    prot2 = testProject.newProtocol(ProtOutputTest, objLabel='to read basic input')

    # Set the pointer for the integer
    prot2.iBoxSize.setPointer(pwobj.Pointer(prot, extended="oBoxSize"))
    launchProtocol(testProject, prot2)
    _assertOutput(prot2, value=40)

    # Test validation: only positive numbers are allowed
    prot3 = testProject.newProtocol(ProtOutputTest, objLabel='invalid input', iBoxSize=-10)
    # We expect this to fail
    with pytest.raises(Exception):
        launchProtocol(testProject, prot3)
    # Test validation: pointer value is validated
    prot4 = testProject.newProtocol(ProtOutputTest, objLabel='invalid pointer input')
    # Now use negative pointer output
    prot4.iBoxSize.setPointer(pwobj.Pointer(prot, extended="negative"))

    # We expect this to fail
    with pytest.raises(Exception):
        launchProtocol(testProject, prot4)
