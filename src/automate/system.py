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

from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
from past.builtins import basestring
from collections import defaultdict

from future import standard_library
standard_library.install_aliases()
from builtins import input
import threading
import operator
import sys
import os
import logging
import pickle
import pkg_resources

from traits.api import (CStr, Instance, CBool, CList, Property, CInt, CUnicode, Event, CSet, Str, cached_property,
                        on_trait_change)

from automate.common import (SystemBase, ExitException, has_baseclass, Object)
from automate.namespace import Namespace
from automate.service import AbstractService, AbstractUserService, AbstractSystemService
from automate.statusobject import AbstractSensor, AbstractActuator
from automate.systemobject import SystemObject
from automate.worker import StatusWorkerThread
from automate.callable import AbstractCallable

import sys

if sys.version_info >= (3, 0):
    TimerClass = threading.Timer
else:
    TimerClass = threading._Timer

def get_autoload_services():
    import automate.services
    return (i for i in list(automate.services.__dict__.values()) if has_baseclass(i, AbstractService) and i.autoload)


def get_service_by_name(name):
    import automate.services
    return getattr(automate.services, name)


class System(SystemBase):
    #: Name of the system (shown in WEB UI for example)
    name = CStr

    #: Allow referencing objects by their names in Callables. If disabled, you can still refer to objects by names
    #: by Object('name')
    allow_name_referencing = CBool(True)

    #: Filename to where to dump the system state
    filename = Str

    # LOGGING
    ###########

    #: Name of the file where logs are stored
    logfile = CUnicode

    #: Log level for the handler that writes to stdout
    print_level = CInt(logging.INFO, transient=True)

    @on_trait_change('print_level', post_init=True)
    def print_level_changed(self, new):
        self.print_handler.setLevel(new)

    #: Reference to logger instance (read-only)
    logger = Instance(logging.Logger)

    #: Instance to the log handler that writes to stdout
    log_handler = Instance(logging.Handler)

    #: Format string of the log handler that writes to stdout
    log_format = Str('%(asctime)s %(log_color)s%(name)s%(reset)s %(message)s')

    #: Instance to the log handler that writes to logfile (read-only)
    print_handler = Instance(logging.Handler)

    #: Format string of the log handler that writes to logfile
    logfile_format = Str('%(process)d:%(threadName)s:%(name)s:%(asctime)s:%(levelname)s:%(message)s')

    #: Log level of the handler that writes to logfile
    log_level = CInt(logging.DEBUG, transient=True)

    @on_trait_change('log_level', post_init=True)
    def log_level_changed(self, new):
        if not self.logfile:
            self.logger.error('No logfile specified')
            return
        self.log_handler.setLevel(new)

    # SERVICES
    ###########

    #: Add here services that you want to be added automatically. This is meant to be re-defined in subclass.
    default_services = CList(trait=Str)

    #: List of services that are loaded in the initialization of the System.
    services = CList(trait=Instance(AbstractService))

    #: List of servicenames that are desired to be avoided (even if normally autoloaded).
    exclude_services = CSet(trait=Str)

    #: Reference to the worker thread (read-only)
    worker_thread = Instance(StatusWorkerThread, transient=True)

    #: System namespace (read-only)
    namespace = Instance(Namespace)

    # Set of all SystemObjects within the system. This is where SystemObjects are ultimately stored
    # in the System initialization. (read-only)
    objects = CSet(trait=SystemObject)

    #: Property giving objects sorted alphabetically (read-only)
    objects_sorted = Property(depends_on='objects')

    @cached_property
    def _get_objects_sorted(self):
        return sorted(list(self.objects), key=operator.attrgetter('_order'))

    #: Read-only property giving all sensors of the system
    sensors = Property(depends_on='objects[]')

    @cached_property
    def _get_sensors(self):
        return {i for i in self.objects_sorted if isinstance(i, AbstractSensor)}

    #: Read-only property giving all actuator of the system
    actuators = Property(depends_on='objects[]')

    @cached_property
    def _get_actuators(self):
        return {i for i in self.objects_sorted if isinstance(i, AbstractActuator)}

    #: Read-only property giving all objects that have program features in use
    programs = Property(depends_on='objects[]')

    @cached_property
    def _get_programs(self):
        from .program import Program, DefaultProgram
        return {i for i in self.objects_sorted if isinstance(i, (Program, DefaultProgram))}

    #: Read-only property giving all :class:`~program.Program` objects
    ordinary_programs = Property(depends_on='programs[]')

    @cached_property
    def _get_ordinary_programs(self):
        from . import program
        return {i for i in self.programs if isinstance(i, program.Program)}

    #: Start worker thread automatically after system is initialized
    worker_autostart = CBool(True)

    #: Trigger which is triggered after initialization is ready (used by Services)
    post_init_trigger = Event

    #: Trigger which is triggered before quiting (used by Services)
    pre_exit_trigger = Event

    #: Read-only property that gives list of all object tags
    all_tags = Property(depends_on='objects.tags[]')

    @cached_property
    def _get_all_tags(self):
        newset = set([])
        for i in self.system.objects:
            for j in i.tags:
                if j:
                    newset.add(j)
        return newset

    #: Enable experimental two-phase queue handling technique (not recommended)
    two_phase_queue = CBool(False)

    @classmethod
    def load_or_create(cls, filename=None, **kwargs):
        """
            Load system from a dump, if dump file exists, or create a new system if it does not exist.
        """

        def savefile_more_recent():
            time_savefile = os.path.getmtime(filename)
            time_program = os.path.getmtime(sys.argv[0])
            return time_savefile > time_program

        def load():
            print('Loading %s' % filename)
            file = open(filename, 'rb')
            state = pickle.load(file)
            file.close()
            system = System(loadstate=state, filename=filename, **kwargs)
            return system

        def create():
            print('Creating new system')
            return cls(filename=filename, **kwargs)

        if filename and os.path.isfile(filename):
            if savefile_more_recent():
                return load()
            else:
                while True:
                    answer = input('Program file more recent. Do you want to load it? (y/n) ')
                    if answer == 'y':
                        return create()
                    elif answer == 'n':
                        return load()
        else:
            return create()

    def save_state(self):
        """
            Save state of the system to a dump file :attr:`System.filename`
        """
        if not self.filename:
            self.logger.error('Filename not specified. Could not save state')
            return
        self.logger.debug('Saving system state to %s', self.filename)
        with open(self.filename, 'wb') as file, self.worker_thread.queue.mutex:
            pickle.dump((list(self.objects)), file, 2)

    @property
    def cmd_namespace(self):
        """
            A read-only property that gives the namespace of the system for evaluating commands.
        """
        import automate
        ns = dict(list(automate.__dict__.items()) + list(self.namespace.items()))
        return ns

    def __getattr__(self, item):
        if self.namespace and item in self.namespace:
            return self.namespace[item]
        raise AttributeError

    def get_unique_name(self, obj, name='', name_from_system=''):
        """
            Give unique name for an Sensor/Program/Actuator object
        """
        ns = self.namespace
        newname = name
        if not newname:
            newname = name_from_system

        if not newname:
            newname = u"Nameless_" + obj.__class__.__name__

        if not newname in ns:
            return newname

        counter = 0
        while True:
            newname1 = u"%s_%.2d" % (newname, counter)
            if not newname1 in ns:
                return newname1
            counter += 1

    @property
    def services_by_name(self):
        """
            A property that gives a dictionary that contains services as values and their names as keys.
        """
        srvs = defaultdict(list)
        for i in self.services:
            srvs[i.__class__.__name__].append(i)
        return srvs

    @property
    def service_names(self):
        """
            A property that gives the names of services as a list
        """
        return set(self.services_by_name.keys())

    def flush(self):
        """
            Flush the worker queue. Usefull in unit tests.
        """
        self.worker_thread.flush()

    def name_to_system_object(self, name):
        """
            Give SystemObject instance corresponding to the name
        """
        if isinstance(name, basestring):
            if self.allow_name_referencing:
                name = name
            else:
                raise NameError('System.allow_name_referencing is set to False, cannot convert string to name')
        elif isinstance(name, Object):
            name = str(name)
        return self.namespace.get(name, None)

    def eval_in_system_namespace(self, exec_str):
        """
            Get Callable for specified string (for GUI-based editing)
        """
        ns = self.cmd_namespace
        try:
            return eval(exec_str, ns)
        except Exception as e:
            self.logger.warning('Could not execute %s, gave error %s', exec_str, e)
            return None

    def register_service_functions(self, *funcs):
        """
            Register function in the system namespace. Called by Services.
        """
        for func in funcs:
            self.namespace[func.__name__] = func

    def register_service(self, service):
        """
            Register service into the system. Called by Services.
        """
        if service not in self.services:
            self.services.append(service)

    def request_service(self, type, id=0):
        """
            Used by Sensors/Actuators/other services that need to use other services for their
            operations.
        """
        srvs = self.services_by_name.get(type)
        if not srvs:
            return

        ser = srvs[id]

        if not ser.system:
            ser.setup_system(self)
        return ser

    def cleanup(self):
        """
            Clean up before quitting
        """

        self.pre_exit_trigger = True

        self.logger.info("Shutting down %s, please wait a moment.", self.name)
        for t in threading.enumerate():
            if isinstance(t, TimerClass):
                t.cancel()
        self.logger.debug('Timers cancelled')

        for i in self.objects:
            i.cleanup()
            del i

        self.logger.debug('Sensors etc cleanups done')

        for ser in (i for i in self.services if isinstance(i, AbstractUserService)):
            ser.cleanup_system()
        self.logger.debug('User services cleaned up')

        self.worker_thread.stop()
        self.logger.debug('Worker thread really stopped')

        for ser in (i for i in self.services if isinstance(i, AbstractSystemService)):
            ser.cleanup_system()
        self.logger.debug('System services cleaned up')

    def cmd_exec(self, cmd):
        """
            Execute commands in automate namespace
        """

        if not cmd:
            return
        ns = self.cmd_namespace
        import copy
        rval = True
        nscopy = copy.copy(ns)
        try:
            r = eval(cmd, ns)
            if isinstance(r, SystemObject) and not r.system:
                r.setup_system(self)
            if callable(r):
                r = r()
                cmd += "()"
            self.logger.info("Eval: %s", cmd)
            self.logger.info("Result: %s", r)
        except SyntaxError:
            r = {}
            try:
                exec (cmd, ns)
                self.logger.info("Exec: %s", cmd)
            except ExitException:
                raise
            except Exception as e:
                self.logger.info("Failed to exec cmd %s: %s.", cmd, e)
                rval = False
            for key, value in list(ns.items()):
                if key not in nscopy or not value is nscopy[key]:
                    if key in self.namespace:
                        del self.namespace[key]
                    self.namespace[key] = value
                    r[key] = value
            self.logger.info("Set items in namespace: %s", r)
        except ExitException:
            raise
        except Exception as e:
            self.logger.info("Failed to eval cmd %s: %s", cmd, e)
            return False

        return rval

    def __init__(self, loadstate=None, **traits):
        super(System, self).__init__(**traits)
        if not self.name:
            self.name = os.path.split(sys.argv[0])[-1].replace('.py', '')

        self.worker_thread = StatusWorkerThread(name="Status worker thread")

        self._initialize_logging()
        self.logger.info('Initializing services')
        self._initialize_services()
        self.logger.info('Initializing namespace')
        self._initialize_namespace(loadstate)
        self.logger.info('Initialize user services')
        self._setup_user_services()

        if self.worker_autostart:
            self.logger.info('Starting worker thread')
            self.worker_thread.start()

        self.post_init_trigger = True

    def _initialize_logging(self):
        self.logger = logging.getLogger()
        if len(self.logger.handlers) > 0:
            self.logger.warning('Logging has been setup already')
            return

        self.logger.setLevel(logging.DEBUG)

        # Why is threre StreamHandler when running gpiotest.py from raspi2?
        # Reason: RPIO uses logging.error etc directly, which adds handler
        # to root. .

        formatter = logging.Formatter(fmt=self.logfile_format)

        if self.logfile:
            self.log_handler = log_handler = logging.FileHandler(self.logfile)
            log_handler.setLevel(self.log_level)
            log_handler.setFormatter(formatter)
            self.logger.addHandler(log_handler)

        self.print_handler = streamhandler = logging.StreamHandler()
        streamhandler.setLevel(self.print_level)

        from colorlog import ColoredFormatter, default_log_colors
        colors = default_log_colors.copy()
        colors['DEBUG'] = 'purple'

        streamhandler.setFormatter(ColoredFormatter(self.log_format, datefmt='%H:%M:%S', log_colors=colors))

        self.logger.addHandler(streamhandler)
        self.logger = logging.getLogger(self.name)
        self.logger.info('Logging setup ready')

    def _initialize_namespace(self, loadstate=None):
        self.namespace = Namespace(system=self)
        self.namespace.set_system(loadstate)

        self.logger.info('Setup loggers per object')
        for k, v in list(self.namespace.items()):
            if isinstance(v, SystemObject):
                ctype = v.__class__.__name__
                v.logger = self.logger.getChild('%s.%s' % (ctype, k))

    def _initialize_services(self):
        # Add default_services, if not already
        for servname in self.default_services:
            if servname not in self.service_names | self.exclude_services:
                self.services.append(get_service_by_name(servname)())

        # Add autorun services if not already
        for servclass in get_autoload_services():
            if servclass.__name__ not in self.service_names | self.exclude_services:
                self.services.append(servclass())

    def _setup_user_services(self):
        for ser in (i for i in self.services if isinstance(i, AbstractUserService)):
            self.logger.info('...%s', ser.__class__.__name__)
            ser.setup_system(self)


# Load extensions

from . import services, sensors, actuators, callables
print('Loading extensions')
for entry_point in pkg_resources.iter_entry_points('automate.extension'):
    print('Trying to load extension %s' % entry_point)
    try:
        ext_classes = entry_point.load(require=False)
    except ImportError:
        print('Loading extension %s failed. Perhaps missing requirements? Skipping.' % entry_point)
        continue
    for ext_class in ext_classes:
        print('... %s' % ext_class.__name__)
        if issubclass(ext_class, AbstractService):
            setattr(services, ext_class.__name__, ext_class)
        elif issubclass(ext_class, AbstractSensor):
            setattr(sensors, ext_class.__name__, ext_class)
        elif issubclass(ext_class, AbstractActuator):
            setattr(actuators, ext_class.__name__, ext_class)
        elif issubclass(ext_class, AbstractCallable):
            setattr(callables, ext_class.__name__, ext_class)
