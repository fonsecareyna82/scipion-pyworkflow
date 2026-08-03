#!/usr/bin/env python
# coding: latin-1
"""
Created on Mar 25, 2014

@author: airen
@author: roberto.marabini
"""
import datetime
import tempfile
import time
from io import StringIO
from subprocess import Popen

import pytest

import pyworkflow as pw
import pyworkflow.utils as pwutils
from pyworkflow import APPS
from pyworkflow.utils import ProgressBar, getListFromValues, prettyDict, strToDuration
from pyworkflow.utils.process import killWithChilds


def test_bibtexParsing():
    """ Some minor tests to the bibtexparser library. """
    bibtex = """

@article{delaRosaTrevin2013,
title = "Xmipp 3.0: An improved software suite for image processing in electron microscopy ",
journal = "Journal of Structural Biology ",
volume = "184",
number = "2",
pages = "321 - 328",
year = "2013",
issn = "1047-8477",
doi = "http://dx.doi.org/10.1016/j.jsb.2013.09.015",
url = "http://www.sciencedirect.com/science/article/pii/S1047847713002566",
author = "J.M. de la Rosa-Trevín and J. Otón and R. Marabini and A. Zaldívar and J. Vargas and J.M. Carazo and C.O.S. Sorzano",
keywords = "Electron microscopy, Single particles analysis, Image processing, Software package "
}

@incollection{Sorzano2013,
title = "Semiautomatic, High-Throughput, High-Resolution Protocol for Three-Dimensional Reconstruction of Single Particles in Electron Microscopy",
booktitle = "Nanoimaging",
year = "2013",
isbn = "978-1-62703-136-3",
volume = "950",
series = "Methods in Molecular Biology",
editor = "Sousa, Alioscka A. and Kruhlak, Michael J.",
doi = "10.1007/978-1-62703-137-0_11",
url = "http://dx.doi.org/10.1007/978-1-62703-137-0_11",
publisher = "Humana Press",
keywords = "Single particle analysis; Electron microscopy; Image processing; 3D reconstruction; Workflows",
author = "Sorzano, CarlosOscar and Rosa Trevín, J.M. and Otón, J. and Vega, J.J. and Cuenca, J. and Zaldívar-Peraza, A. and Gómez-Blanco, J. and Vargas, J. and Quintana, A. and Marabini, Roberto and Carazo, JoséMaría",
pages = "171-193",
}
"""
    prettyDict(pwutils.parseBibTex(bibtex))


def test_process():
    """ Some tests for utils.process module. """
    prog = pw.join(APPS, 'pw_sleep.py')
    p = Popen('python %s 500' % prog, shell=True)
    print("pid: %s" % p.pid)
    time.sleep(5)
    killWithChilds(p.pid)


@pytest.mark.parametrize(
    "inputString, expected",
    [
        ("1,5-8,10", [1, 5, 6, 7, 8, 10]),
        ("2,6,9-11", [2, 6, 9, 10, 11]),
        ("2 5, 6-8", [2, 5, 6, 7, 8]),
        ("1-4 8", [1, 2, 3, 4, 8]),
    ],
)
def test_getListFromRangeString(inputString, expected):
    assert expected == pwutils.getListFromRangeString(inputString)
    # Check that also works properly with spaces as delimiters
    assert expected == pwutils.getListFromRangeString(inputString.replace(',', ' '))


@pytest.mark.parametrize(
    "strValue, expected, length, caster",
    [
        ('1 1 2x2 4 4', ['1', '1', '2x2', '4', '4'], None, str),
        ('1 1 2x2 4 4', [1, 1, 2, 2, 4, 4], None, int),
        ('2,3,4,1', [2, 3, 4, 1], None, int),
        ('2 , 3 , 4 , 1', [2, 3, 4, 1], None, int),
        ('2,3.3,4', [2.0, 3.3, 4.0], None, float),
    ],
)
def test_getListFromValues(strValue, expected, length, caster):
    """ Test numeric list definitions like:
        '1 1 2x2 4 4' -> ['1', '1', '2', '2', '4', '4']
        '2x3, 3x4, 1' -> ['3', '3', '4', '4', '4', '1']"
    """
    result = getListFromValues(strValue, length, caster)
    assert result == expected, "List from string does not work for %s" % strValue


@pytest.mark.parametrize(
    "fmt, total, step, resultGold",
    [
        (ProgressBar.DOT, 1000000, 10000, '.' * (int(1000000 / 10000) + 1)),
        (
            ProgressBar.DEFAULT, 3, 1,
            '\rProgress: [                                        ] '
            '  0%\rProgress: [=============                         '
            '  ]  33%\rProgress: [==========================        '
            '      ]  66%\rProgress: [=============================='
            '==========] 100%',
        ),
        (
            ProgressBar.FULL, 3, 1,
            '\r[                                        ] 0/3 (  0%)'
            ' 3 to go\r[=============                           ] '
            '1/3 ( 33%) 2 to go\r[==========================      '
            '        ] 2/3 ( 66%) 1 to go\r[======================'
            '==================] 3/3 (100%) 0 to go',
        ),
        (
            ProgressBar.OBJID, 3, 1,
            '\r[                                        ] 0/3 (  0%)'
            ' (objectId=33)\r[=============                         '
            '  ] 1/3 ( 33%) (objectId=33)\r[========================'
            '==              ] 2/3 ( 66%) (objectId=33)\r[=========='
            '==============================] 3/3 (100%) '
            '(objectId=33)',
        ),
    ],
    ids=["dot", "default", "full", "objectid"],
)
def test_progressBar(fmt, total, step, resultGold):
    ti = time.time()
    result = StringIO()
    pb = ProgressBar(total=total, fmt=fmt, output=result, extraArgs={'objectId': 33})

    pb.start()
    for i in range(total):
        if i % step == 0:
            pb.update(i + 1)
    pb.finish()
    assert resultGold.strip() == result.getvalue().strip()
    result.close()
    tf = time.time()
    print("%d iterations in %f sec" % (total, tf - ti))


def test_fileModificationTime():
    since = datetime.datetime.now()
    time.sleep(1)

    tmpFile = tempfile.NamedTemporaryFile()
    assert not pwutils.isFileFinished(tmpFile.name), "File is NOT finished"
    time.sleep(1)

    assert pwutils.isFileFinished(tmpFile.name, duration=0.5), "File is finished after 2 seconds"

    assert pwutils.hasChangedSince(tmpFile.name, since), "hasChanged should have returned true. False negative."
    since = datetime.datetime.now()
    assert not pwutils.hasChangedSince(tmpFile.name, since), "hasChanged should have returned false. False positive."


def test_durationStrings():
    assert 70 == strToDuration("1m 10s"), "String duration wrongly converted"
