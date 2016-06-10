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

from __future__ import absolute_import
from __future__ import unicode_literals
import logging
from traits.has_traits import HasStrictTraits, cached_property
from traits.trait_types import Instance, CUnicode, Tuple, Dict, Event, Unicode, Int, CBool
from traits.traits import Property
from automate import SystemBase, TagSet, is_valid_variable_name


class SystemObject(HasStrictTraits):

    """
        Baseclass for Programs, Sensor, Actuators
    """

    #: Names of attributes that accept Callables. If there are custom callables being used, they must be added here.
    #: The purpose of this list is that these Callables will be initialized properly.
    #: :class:`~automate.program.ProgrammableSystemObject` introduces 5 basic callables
    #: (see also :ref:`automate-programs`).
    callables = []

    def get_default_callables(self):
        """ Get a dictionary of default callables, in form {name:callable}. Re-defined in subclasses."""
        return {}

    #: Reference to System object
    system = Instance(SystemBase, transient=True)

    #: Description of the object (shown in WEB interface)
    description = CUnicode

    #: Python Logger instance for this object. System creates each object its own logger instance.
    logger = Instance(logging.Logger, transient=True)

    #: Tags are used for (for example) grouping objects. See :ref:`groups`.
    tags = TagSet(trait=CUnicode)

    #: Name property is determined by System namespace. Can be read/written.
    name = Property(trait=Unicode, depends_on='name_changed_event')

    @cached_property
    def _get_name(self):
        try:
            return self.system.reverse[self]
        except (KeyError, AttributeError):
            return 'System not initialized!'

    def _set_name(self, new_name):
        if not is_valid_variable_name(new_name):
            raise NameError('Illegal name %s' % new_name)
        try:
            if self in list(self.system.namespace.values()):
                del self.system.namespace[self.name]
        except NameError:

            pass
        self.system.namespace[new_name] = self
        self.logger = self.system.logger.getChild('%s.%s' % (self.__class__.__name__, new_name))

    #: If set to *True*, current SystemObject is hidden in the UML diagram of WEB interface.
    hide_in_uml = CBool(False)

    _order = Int
    _count = 0

    #: Attributes that can be edited by user in WEB interface
    view = ['hide_in_uml']

    #: The data type name (as string) of the object. This is written in the initialization, and is used by WEB
    #: interface Django templates.
    data_type = ''

    #: If editable=True, a quick edit widget will appear in the web interface. Define in subclasses.
    editable = False

    # Namespace triggers this event when object name name is changed
    name_changed_event = Event

    _passed_arguments = Tuple(transient=True)
    _postponed_callables = Dict(transient=True)

    @property
    def class_name(self):
        # For Django templates
        return self.__class__.__name__

    @property
    def object_type(self):
        """
            A read-only property that gives the object type as string; sensor, actuator, program, other.
            Used by WEB interface templates.
        """

        from .statusobject import AbstractSensor, AbstractActuator
        from .program import Program
        if isinstance(self, AbstractSensor):
            return 'sensor'
        elif isinstance(self, AbstractActuator):
            return 'actuator'
        elif isinstance(self, Program):
            return 'program'
        else:
            return 'other'

    def __init__(self, name='', **traits):
        # Postpone traits initialization to be launched by System
        self.logger = logging.getLogger('automate.%s' % self.__class__.__name__)
        self._order = SystemObject._count
        SystemObject._count += 1

        self._passed_arguments = name, traits
        if 'system' in traits:
            self.setup_system(traits.pop('system'))
            self.setup_callables()

    def __setstate__(self, state, trait_change_notify=True):
        self.logger = logging.getLogger('automate.%s' % self.__class__.__name__)
        self._order = state.pop('_order')
        self._passed_arguments = None, state

    def get_status_display(self, **kwargs):
        """
            Redefine this in subclasses if status can be represented in human-readable way (units etc.)
        """
        if 'value' in kwargs:
            return str(kwargs['value'])
        return self.class_name

    def get_as_datadict(self):
        """
            Get information about this object as a dictionary.  Used by WebSocket interface to pass some
            relevant information to client applications.
        """
        return dict(type=self.__class__.__name__, tags=list(self.tags))

    def setup(self, *args, **kwargs):
        """
            Initialize necessary services etc. here. Define this in subclasses.
        """
        pass

    def setup_system(self, system, name_from_system='', **kwargs):
        """
            Set system attribute and do some initialization. Used by System.
        """

        if not self.system:
            self.system = system
        name, traits = self._passed_arguments
        new_name = self.system.get_unique_name(self, name, name_from_system)
        if not self in self.system.reverse:
            self.name = new_name
        if name is None and 'name' in traits:  # Only __setstate__ sets name to None. Default is ''.
            del traits['name']

        for cname in self.callables:
            if cname in traits:
                c = self._postponed_callables[cname] = traits.pop(cname)
                c.setup_callable_system(self.system)
            getattr(self, cname).setup_callable_system(self.system)

        if not self.traits_inited():
            super(SystemObject, self).__init__(**traits)
        self.name_changed_event = True
        self.setup()

    def setup_callables(self):
        """
            Setup Callable attributes that belong to this object.
        """
        defaults = self.get_default_callables()
        for key, value in list(defaults.items()):
            self._postponed_callables.setdefault(key, value)
        for key in self.callables:
            value = self._postponed_callables.pop(key)
            value.setup_callable_system(self.system, init=True)
            setattr(self, key, value)

    def cleanup(self):
        """
            Write here whatever cleanup actions are needed when object is no longer used.
        """

    def __str__(self):
        return self.name

    def __repr__(self):
        return u"'%s'" % self.name
