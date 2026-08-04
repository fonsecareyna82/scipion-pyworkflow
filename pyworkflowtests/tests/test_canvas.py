#!/usr/bin/env python
# To run only the tests in this file, use:
# pytest pyworkflowtests/tests/test_canvas.py -v

import math
import tkinter

import pytest

import pyworkflow.gui.canvas

# IMPORTANT: Tk requires at least that DISPLAY is defined
# hence in some environments (like buildbot) the test may fail,
# check for the TclError exception


def _distance(c1, c2):
    return round(math.hypot(c2[0] - c1[0], c2[1] - c1[1]), 2)


def _allEqual(values):
    return not values or values.count(values[0]) == len(values)


def _allDifferent(values):
    return not values or len(values) == len(set(values))


@pytest.mark.gui
def test_connectorsCoords():
    try:
        root = tkinter.Tk()
        canvas = pyworkflow.gui.canvas.Canvas(root, width=800, height=600)
        tb1 = canvas.createTextbox("First", 100, 100, "blue")

        connectorsCoords = tb1.getConnectorsCoordinates()
        assert _allDifferent(connectorsCoords)

        print(connectorsCoords)

        distances = {}
        for i in range(len(connectorsCoords) - 1):
            distances[i] = _distance(connectorsCoords[i], connectorsCoords[i + 1])

            print(distances)
            assert _allEqual(list(distances.values()))
            assert distances[0] != 0
    except tkinter.TclError as ex:
        print(ex)


@pytest.mark.gui
def test_closestConnectors():
    try:
        root = tkinter.Tk()
        canvas = pyworkflow.gui.canvas.Canvas(root, width=800, height=600)
        tb1 = canvas.createTextbox("Textbox1", 100, 100, "blue")
        tb2 = canvas.createTextbox("Textbox2", 300, 100, "blue")
        tb3 = canvas.createTextbox("Textbox3", 100, 300, "blue")

        c1, c2 = pyworkflow.gui.canvas.findStrictClosestConnectors(tb1, tb2)
        c3, c4 = pyworkflow.gui.canvas.findStrictClosestConnectors(tb1, tb3)
        # tb1 and tb2 are aligned vertically. tb1 and tb3, horizontally.
        # So, their closest connectors must share one coordinate (y in case of c1&c2, x in case of c3&c4)
        assert c1[1] == c2[1]
        assert c3[0] == c4[0]
    except tkinter.TclError as ex:
        print(ex)
