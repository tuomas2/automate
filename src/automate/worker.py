from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import object
# -*- coding: utf-8 -*-
# (c) 2015 Tuomas Airaksinen
#
# This file is part of Automate.
#
# Automate is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Automate is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Automate.  If not, see <http://www.gnu.org/licenses/>.
#
# ------------------------------------------------------------------
#
# If you like Automate, please take a look at this page:
# http://evankelista.net/automate/

import queue
import logging
import threading


class StatusWorkerTask(object):

    def __init__(self, func, args, object):
        self.func = func
        self.args = args
        self.object = object

    @property
    def status(self):
        return self.args[0]

    def run(self):
        with self.object._status_lock:
            if self is self.object._queued_job:
                self.object.logger.debug('Running task %s', self)
                try:
                    self.func(*self.args)
                except Exception as e:
                    self.object.logger.error('Error running Task: %s', e)
                self.object._queued_job = None
            else:
                self.object.logger.debug('Task %s was not executed (was removed or replaced)', self)

    def __repr__(self):
        try:
            return '<Task %s %s>' % (self.object, self.args)
        except NameError:
            return '<Task *>'


class DummyStatusWorkerTask(object):

    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.func(*self.args, **self.kwargs)

    def __repr__(self):
        return '<Dummy %s %s %s>' % (self.func, self.args, self.kwargs)


class StatusWorkerThread(threading.Thread):

    def _set_stop(self):
        self._stop = True
        self.logger.debug('Stop set')

    def __init__(self, *args, **kwargs):
        self.queue = queue.Queue()
        self._stop = False
        self.logger = logging.getLogger('automate.StatusWorkerThread')
        super(StatusWorkerThread, self).__init__(*args, **kwargs)

    def manual_flush(self):
        if self.is_alive():
            self.logger.error('Worker thread is running, cannot flush manually')
            return

        self.logger.info('Flushing queue manually (worker thread not yet alive)')
        while self.queue.queue:
            self.process_job()

    def process_job(self):
        job = self.queue.get()
        try:
            job.run()
        except Exception as e:
            self.logger.error('Error occurred when executing job %s: %s', job, e)
        self.queue.task_done()

    def run(self):
        self.logger.debug('StatusWorkerThread starting')
        while not self._stop:
            self.process_job()

        self.logger.debug('StatusWorkerThread exiting, entries: %s', self.queue.queue)

    def flush(self):
        """
        This only needs to be called manually
        from unit tests
        """
        self.logger.debug('Flush joining')
        self.queue.join()
        self.logger.debug('Flush joining ready')

    def put(self, job):
        self.logger.debug('Putting now %s', id(job))
        self.queue.put(job)

    def stop(self):
        self.logger.debug('Stopping: pre-flush')
        self.flush()

        self.put(DummyStatusWorkerTask(self._set_stop))

        self.logger.debug('Stopping')
        self.logger.debug('... entries: %s', self.queue.queue)
        self.flush()
        self.logger.debug('Stopping ready')
