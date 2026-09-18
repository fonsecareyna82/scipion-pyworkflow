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

import pyworkflow.mapper as pwmapper
import pyworkflow.protocol as pwprot
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
