from __future__ import unicode_literals

import logging
from logging.config import dictConfig

import pytest
from automate.test_utils import CaptureLogHandler



@pytest.fixture(autouse=True, scope='session')
def logging_configuration():
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'verbose': {
                'format': '%(levelname)s %(asctime)s %(module)s %(name)s %(message)s'
            },
            'simple': {
                'format': '%(levelname)s %(message)s'
            },
            'colorful': {
                '()': 'colorlog.ColoredFormatter',
                'format': '%(threadName)s:%(asctime)s %(log_color)s%(name)s%(reset)s %(levelname)s:%(message)s'
                # 'format': "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(message)s"
            },
            'old_caplog_format': {
                'format': '%(threadName)s:%(asctime)s:%(name)s:%(levelname)s:%(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                # 'formatter': 'verbose',
                'formatter': 'colorful',
                'level': 'DEBUG',
            },
            'caplog': {
                'class': 'automate.test_utils.CaptureLogHandler',
                'formatter': 'old_caplog_format',
                'level': 'DEBUG',
            }
        },
        'loggers': {
            '': {
                'handlers': ['caplog', 'console'],
                'level': 'DEBUG',
                'propagate': True,
            },
            'automate': {
                'handlers': ['caplog', 'console'],
                'level': 'DEBUG',
                'propagate': False,
            },
        },
    }
    dictConfig(LOGGING)
    yield None


class LoggingException(Exception):
    pass


@pytest.fixture(scope='function')
def caplog():
    root_logger = logging.getLogger()
    handler = root_logger.handlers[0]
    assert isinstance(handler, CaptureLogHandler)
    yield handler
    handler.reset()


@pytest.fixture(autouse=True, scope='function')
def check_log(request, caplog):
    logger = logging.getLogger('automate')
    logger.info('UNITTEST %s', request)
    yield None
    if not getattr(caplog, 'error_ok', False):
        for i in caplog.records:
            if i.levelno >= logging.ERROR:
                raise LoggingException('Error: %s' % i.getMessage())
    caplog.error_ok = False


@pytest.fixture(params=[1])
def sysloader(request, tmpdir):
    from automate.system import System
    filename = str(tmpdir.join('savefile.dmp'))
    if request.param:
        class Loader(object):

            def new_system(self, sys, *args, **kwargs):
                kwargs.setdefault('exclude_services', ['TextUIService'])
                self.sys = sys(*args, **kwargs)
                self.sys.flush()
                return self.sys
    else:
        class Loader(object):

            def new_system(self, sys, *args, **kwargs):
                kwargs.setdefault('exclude_services', ['TextUIService'])
                sys1 = sys(*args, **kwargs)
                sys1.flush()
                sys1.filename = filename
                sys1.save_state()
                sys1.cleanup()

                self.sys = System.load_or_create(filename, exclude_services=['TextUIService'])
                self.sys.flush()
                return self.sys

    loader = Loader()
    yield loader
    loader.sys.cleanup()


#_count = 0
#@pytest.fixture(autouse=True, scope='function')
#def memory_usage(request):
#    global _count
#    import pympler.muppy
#    import pympler.summary
#    yield None
#    _count += 1
#    if _count % 50 == 0:
#        all_objects = pympler.muppy.get_objects()
#        sum1 = pympler.summary.summarize(all_objects)
#        pympler.summary.print_(sum1)
