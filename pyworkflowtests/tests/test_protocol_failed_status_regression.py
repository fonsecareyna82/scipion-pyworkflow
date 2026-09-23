# -*- coding: utf-8 -*-
from datetime import timedelta
import unittest
from unittest.mock import MagicMock

import pyworkflow.protocol as pwprot


class TestProtocolFailedStatusRegression(unittest.TestCase):

    def test_FailedStepStatusIsNotOverwrittenByLaterFinishedStep(self):
        protocol = MagicMock()
        protocol.lastStatus = pwprot.STATUS_RUNNING
        protocol._cpuTime.get.return_value = 0.0
        protocol.modeParallel.return_value = False
        protocol.getProject.return_value.getName.return_value = "test-project"
        protocol.getObjId.return_value = 1
        protocol.getClassName.return_value = "TestProtocol"

        def makeStep(status, index):
            step = MagicMock()
            step.getStatus.return_value = status
            step.isInteractive.return_value = False
            step.isFailed.return_value = status == pwprot.STATUS_FAILED
            step.getErrorMessage.return_value = "boom"
            step.getElapsedTime.return_value = timedelta(seconds=0)
            step.funcName.get.return_value = "testStep"
            step._index = index
            step.endTime.datetime.return_value = None
            return step

        failedStep = makeStep(
            pwprot.STATUS_FAILED,
            1,
        )
        finishedStep = makeStep(
            pwprot.STATUS_FINISHED,
            2,
        )

        pwprot.Protocol._stepFinished(
            protocol,
            failedStep,
        )

        self.assertEqual(
            pwprot.STATUS_FAILED,
            protocol.lastStatus,
        )

        pwprot.Protocol._stepFinished(
            protocol,
            finishedStep,
        )

        self.assertEqual(
            pwprot.STATUS_FAILED,
            protocol.lastStatus,
            "A FINISHED step that completes after a FAILED step must "
            "not make the protocol finish successfully.",
        )


if __name__ == "__main__":
    unittest.main()
