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
import os
import time
import threading
import unittest

import pytest

import pyworkflow.mapper as pwmapper
import pyworkflow.protocol as pwprot
from pyworkflow.object import Object
from pyworkflow.project import Project
from pyworkflow.protocol.constants import VOID_GPU
from pyworkflowtests import Domain

# TODO: this test seems not to be finished.
from pyworkflowtests.protocols import SleepingProtocol


def test_StepExecutor(testOutputPath):
    """Test the list with several Complex"""
    fn = os.path.join(testOutputPath, "protocol.sqlite")
    print("Writing to db: %s" % fn)

    # Discover objects and protocols
    mapperDict = Domain.getMapperDict()

    # Associate the project
    proj = Project(Domain, path=testOutputPath)

    # Check that the protocol has associated package
    mapper = pwmapper.SqliteMapper(fn, mapperDict)
    prot = SleepingProtocol(mapper=mapper, n=2, project=proj, workingDir=testOutputPath)
    domain = prot.getClassDomain()
    domain.printInfo()

    prot.setStepsExecutor(pwprot.StepExecutor(hostConfig=None))
    prot.makeWorkingDir()
    prot.run()
    mapper.commit()
    mapper.close()

    assert prot._steps[0].getStatus() == pwprot.STATUS_FINISHED

    mapper2 = pwmapper.SqliteMapper(fn, mapperDict)
    prot2 = mapper2.selectById(prot.getObjId())

    assert prot.endTime.get() == prot2.endTime.get()


def test_gpu_anonimization():
    assert pwprot.anonimizeGPUs([0, 1, 2]) == [0, 1, 2], "Anonimization of GPUs does not work"
    assert pwprot.anonimizeGPUs([2, 1, 0]) == [0, 1, 2], "Anonimization of GPUs does not work"
    assert pwprot.anonimizeGPUs([2, 1, 2]) == [0, 1, 0], "Anonimization of GPUs does not work"
    assert pwprot.anonimizeGPUs([2, 1, 2, 4]) == [0, 1, 0, 2], "Anonimization of GPUs does not work"


def test_threadStepExecutorWakesWhenStepFinishes():
    class FastStep(pwprot.Step):
        def _run(self):
            time.sleep(0.05)

    first = FastStep(needsGPU=False)
    first.setObjId(1)
    second = FastStep(needsGPU=False)
    second.setObjId(2)
    second.addPrerequisites(1)

    executor = pwprot.ThreadStepExecutor(None, 1, gpuList=None)
    started = time.perf_counter()
    executor.runSteps([first, second], lambda step: None, lambda step: True, lambda: None, stepsCheckSecs=5)
    elapsed = time.perf_counter() - started

    assert first.getStatus() == pwprot.STATUS_FINISHED
    assert second.getStatus() == pwprot.STATUS_FINISHED
    assert elapsed < 1.0


def test_threadStepExecutorChecksWaitingStepsImmediatelyAfterCompletion():
    class FastStep(pwprot.Step):
        def _run(self):
            time.sleep(0.05)

    first = FastStep(needsGPU=False)
    first.setObjId(1)
    second = FastStep(needsGPU=False)
    second.setObjId(2)
    second.addPrerequisites(1)
    second.setStatus(pwprot.STATUS_WAITING)

    def checkSteps():
        if first.isFinished() and second.isWaiting():
            second.setStatus(pwprot.STATUS_NEW)

    executor = pwprot.ThreadStepExecutor(None, 1, gpuList=None)
    started = time.perf_counter()
    executor.runSteps([first, second], lambda step: None, lambda step: True, checkSteps, stepsCheckSecs=5)
    elapsed = time.perf_counter() - started

    assert first.getStatus() == pwprot.STATUS_FINISHED
    assert second.getStatus() == pwprot.STATUS_FINISHED
    assert elapsed < 1.0


def test_gpuSlots():
    """ Test gpu slots are properly composed in combination of threads"""
    # Test basic GPU setu methods
    stepExecutor = pwprot.ThreadStepExecutor(None, 1, gpuList=None)

    assert stepExecutor.cleanVoidGPUs([0, 1]) == [0, 1], "CleanVoidGpus does not work in absence of void GPUS"
    assert stepExecutor.cleanVoidGPUs([0, VOID_GPU]) == [0], "CleanVoidGpus does not work with a void GPU"
    assert stepExecutor.cleanVoidGPUs([VOID_GPU, VOID_GPU]) == [], "CleanVoidGpus does not work with all void GPU"

    currThread = threading.current_thread()

    def needForGPU():
        return True

    currThread.needsGPU = needForGPU
    currThread.thId = 1
    assert stepExecutor.getGpuList() == [], "Gpu list should be empty"

    # 2 threads 1 GPU
    stepExecutor = pwprot.ThreadStepExecutor(None, 2, gpuList=[1])
    assert stepExecutor.getGpuList() == [1], "Gpu list should be [1]"

    currThread.thId = 2
    assert stepExecutor.getGpuList() == [], "Gpu list should be empty after a second request"

    # 2 threads 3 GPUs
    stepExecutor = pwprot.ThreadStepExecutor(None, 2, gpuList=[0, 1, 2])
    assert stepExecutor.getGpuList() == [0, 1], "Gpu list should be [0,1]"

    currThread.thId = 1
    assert stepExecutor.getGpuList() == [2], "Gpu list should be [2] after a second request"

    # 2 threads 4 GPUs with void gpus
    stepExecutor = pwprot.ThreadStepExecutor(None, 2, gpuList=[0, 1, 2, VOID_GPU])
    assert stepExecutor.getGpuList() == [0, 1], "Gpu list should be [0,1]"

    currThread.thId = 2
    assert stepExecutor.getGpuList() == [2], "Gpu list should be [2] after a second request without the void gpu"

    # less GPUs than threads. No extension should happen
    stepExecutor = pwprot.ThreadStepExecutor(None, 4, gpuList=[0, VOID_GPU, 2])
    assert stepExecutor.getGpuList() == [0], "Gpu list should not be extended"

    currThread.thId = 1
    assert stepExecutor.getGpuList() == [2], "Gpu list should be [2] after a second request, skipping the VOID gpu"

    currThread.thId = 3
    assert stepExecutor.getGpuList() == [], "Gpu list should be empty ather all GPU slots are busy"


def test_FunctionStepIdentityPreservesScipionObjectArguments():
    firstArg = Object()
    firstArg.setObjId(101)

    secondArg = Object()
    secondArg.setObjId(202)

    def processObject(_obj):
        pass

    firstStep = pwprot.FunctionStep(
        processObject,
        "processObject",
        firstArg,
    )
    secondStep = pwprot.FunctionStep(
        processObject,
        "processObject",
        secondArg,
    )

    assert firstStep.argsStr.get() != secondStep.argsStr.get(), (
        "FunctionStep persistence must preserve the identity of distinct "
        "Scipion Object arguments instead of serializing both as null."
    )
    assert firstStep != secondStep, (
        "Resume matching must not consider steps for different Scipion "
        "Object arguments equivalent."
    )


def test_threadStepExecutorDoesNotJoinUnrelatedThreads(monkeypatch):
    class UnrelatedThread:
        def join(self):
            raise AssertionError(
                "ThreadStepExecutor must not join threads it did not create."
            )

    currentThread = threading.current_thread()
    unrelatedThread = UnrelatedThread()

    monkeypatch.setattr(
        threading,
        "enumerate",
        lambda: [currentThread, unrelatedThread],
    )

    executor = pwprot.ThreadStepExecutor(
        None,
        1,
        gpuList=None,
    )

    executor.runSteps(
        [],
        lambda step: None,
        lambda step: True,
        lambda: None,
        stepsCheckSecs=0,
    )


def test_threadStepExecutorUsesStepIndexWithoutPersistedObjId():
    step = pwprot.Step(needsGPU=True)
    step.setIndex(7)

    assert step.getObjId() is None

    executor = pwprot.ThreadStepExecutor(
        None,
        1,
        gpuList=[3],
    )

    assert executor._isStepRunnable(step)

    assert executor.gpuDict.get(7) == [3], (
        "A Step without a persisted objId must reserve its GPU slot "
        "using the protocol step index."
    )

    stepThread = pwprot.StepThread(
        step,
        threading.Lock(),
    )

    assert stepThread.thId == 7, (
        "StepThread must use the protocol step index when alternative "
        "step persistence has not assigned an objId."
    )


def test_threadStepExecutorFinalizesRunningSiblingsAfterStop():
    secondStarted = threading.Event()
    allowSecondFinish = threading.Event()
    finishedCallbacks = []

    class FirstStep(pwprot.Step):
        def _run(self):
            assert secondStarted.wait(timeout=2)

    class SecondStep(pwprot.Step):
        def _run(self):
            secondStarted.set()
            assert allowSecondFinish.wait(timeout=2)

    first = FirstStep(needsGPU=False)
    first.setObjId(1)

    second = SecondStep(needsGPU=False)
    second.setObjId(2)

    def stepFinished(step):
        finishedCallbacks.append(step.getObjId())

        if step is first:
            allowSecondFinish.set()
            return False

        return True

    executor = pwprot.ThreadStepExecutor(
        None,
        2,
        gpuList=None,
    )

    executor.runSteps(
        [first, second],
        lambda step: None,
        stepFinished,
        lambda: None,
        stepsCheckSecs=5,
    )

    assert first.isFinished()
    assert second.isFinished()
    assert finishedCallbacks == [1, 2], (
        "Every started StepThread must reach stepFinishedCallback even when "
        "another parallel step stops further scheduling."
    )


class TestThreadStepExecutorFailureCleanup(unittest.TestCase):
    def testWaitsForRunningStepsWhenStepsCheckFails(self):
        workerStarted = threading.Event()
        workerFinished = threading.Event()

        class SlowStep(pwprot.Step):
            def _run(self):
                workerStarted.set()
                time.sleep(0.25)
                workerFinished.set()

        step = SlowStep(needsGPU=False)
        step.setObjId(1)

        def failingStepsCheck():
            self.assertTrue(workerStarted.wait(timeout=1))
            raise RuntimeError("steps check failed")

        executor = pwprot.ThreadStepExecutor(
            None,
            1,
            gpuList=None,
        )

        with self.assertRaisesRegex(
                RuntimeError,
                "steps check failed",
        ):
            executor.runSteps(
                [step],
                lambda currentStep: None,
                lambda currentStep: True,
                failingStepsCheck,
                stepsCheckSecs=0,
            )

        finishedBeforeReturn = workerFinished.is_set()
        workerFinished.wait(timeout=1)

        self.assertTrue(
            finishedBeforeReturn,
            "ThreadStepExecutor must wait for its running StepThreads before "
            "propagating an exception raised by stepsCheckCallback.",
        )

    def testProtocolFailsWhenStepsCheckRaises(self):
        workerStarted = threading.Event()
        workerFinished = threading.Event()

        class FailingStepsCheckProtocol(pwprot.Protocol):
            stepsExecutionMode = pwprot.STEPS_PARALLEL

            def _defineParams(self, form):
                pass

            def validate(self):
                return []

            def _insertAllSteps(self):
                self._insertFunctionStep(
                    self.workerStep,
                    prerequisites=[],
                    needsGPU=False,
                )

            def workerStep(self):
                workerStarted.set()
                time.sleep(0.2)
                workerFinished.set()

            def _stepsCheck(self):
                self.assertWorkerStarted()
                raise RuntimeError("steps check failed")

            def assertWorkerStarted(self):
                if not workerStarted.wait(timeout=1):
                    raise AssertionError("Worker step did not start.")

            def loadSteps(self):
                return []

            def _storeSteps(self):
                pass

            def _store(self, *objects):
                pass

            def _stepStarted(self, step):
                pass

            def _stepFinished(self, step):
                self.lastStatus = step.getStatus()
                return True

        protocol = FailingStepsCheckProtocol(
            runMode=pwprot.MODE_RESTART,
        )

        protocol.setStepsExecutor(
            pwprot.ThreadStepExecutor(
                None,
                1,
                gpuList=None,
            )
        )

        pwprot.Step.run(protocol)

        self.assertTrue(workerFinished.is_set())
        self.assertTrue(protocol.isFailed())
        self.assertIn(
            "steps check failed",
            protocol.getErrorMessage(),
        )

def test_resumeRerunsStepWhenPrerequisiteWasInvalidated():
    def makeStep(name, argument, index, prerequisite=None, finished=False):
        step = pwprot.FunctionStep(
            lambda value: None,
            name,
            argument,
            needsGPU=False,
        )
        step.setIndex(index)

        if prerequisite is not None:
            step.addPrerequisites(prerequisite)

        if finished:
            step.setFinished()

        return step

    oldFirst = makeStep("first", "same", 1, finished=True)
    oldSecond = makeStep("second", "old", 2, prerequisite=1, finished=True)
    oldThird = makeStep("third", "same", 3, prerequisite=2, finished=True)

    newFirst = makeStep("first", "same", 1)
    newSecond = makeStep("second", "new", 2, prerequisite=1)
    newThird = makeStep("third", "same", 3, prerequisite=2)

    class ResumeProtocolStub:
        runMode = pwprot.MODE_RESUME

        def __init__(self):
            self._steps = [
                newFirst,
                newSecond,
                newThird,
            ]
            self._prevSteps = []

        def loadSteps(self):
            return [
                oldFirst,
                oldSecond,
                oldThird,
            ]

        def debug(self, *args, **kwargs):
            pass

        def info(self, *args, **kwargs):
            pass

    protocol = ResumeProtocolStub()

    doneSteps = pwprot.Protocol._Protocol__updateDoneSteps(
        protocol
    )

    assert newFirst.isFinished()
    assert newSecond.isNew()
    assert newThird.isNew(), (
        "Resume must rerun a finished step when one of its prerequisites "
        "was invalidated and must be recomputed."
    )
    assert doneSteps == 1

