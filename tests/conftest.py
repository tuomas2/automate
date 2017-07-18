from __future__ import unicode_literals

from pytest_capturelog import CaptureLogHandler
import pytest
import logging

from automate.test_utils import sysloader, check_log

@pytest.fixture(scope='function')
def caplog(caplog):
    logger = logging.getLogger('automate')
    handler = CaptureLogHandler()
    logger.addHandler(handler)
    yield caplog
    logger.removeHandler(handler)
