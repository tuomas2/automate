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

from __future__ import unicode_literals
from past.builtins import basestring
import re
from traits.api import cached_property, on_trait_change, CList, Dict, Instance, Set, Event, Property
from automate.common import CompareMixin, Lock, deep_iterate, Object, is_iterable, AbstractStatusObject, DictObject, SystemNotReady
from automate.systemobject import SystemObject

import logging


class AbstractCallable(SystemObject, CompareMixin):

    """

    A base class for subclassing Callables that are used in Program conditions and action attributes.

    Callables are configured by giving them arguments and keyword arguments.They must always define :meth:`.call`
    method which defines their functionality.
    """

    #: Arguments given for callable are stored here
    _args = CList

    #: Keyword arguments given for callable are stored here
    _kwargs = Dict

    #: Lock must be used when accessing :attr:`.state`
    _lock = Instance(Lock, transient=True)

    #: Property that gives set of all *triggers* of this callable and it's children callables.
    #: Triggers are all those StatusObjects that alter the status (return value of :meth:`.call`) of
    #: Callable.
    triggers = Property(trait=Set(trait=AbstractStatusObject),
                        depends_on='_args, _args_items, _args.triggers, _kwargs, _kwargs_items, _kwargs.triggers')

    #: Property that gives set of all *targets* of this callable and it's children callables. Targets are
    #: all those StatusObjects of which status the callable might alter in :meth:`.call`.
    targets = Property(trait=Set(trait=AbstractStatusObject),
                       depends_on='_args, _args_items, _args.targets, _kwargs, _kwargs_items, _kwargs.targets')

    # Status property not yet used anywhere. In the future, Program.active could be changed to Property
    # which uses this status.
    # Remark: isn't it used in web?

    #: Read-only status property of the callable. Usefull only when callable is used as a condition.
    #: This automatically depends on all the StatusObjects below the Callable tree.
    status = Property(depends_on='_args.status, _kwargs.status')

    #: State dictionary that is used by :meth:`.call` and :meth:`.cancel` if some state variables are needed to be saved
    #: Remember to clean data in subclasses when it is no longer needed.
    state = Dict(transient=True)

    def get_state(self, caller):
        """
            Get per-program state.
        """

        if caller in self.state:
            return self.state[caller]
        else:
            rv = self.state[caller] = DictObject()
            return rv

    def del_state(self, caller):
        """
            Delete per-program state.
        """
        if caller in self.state:
            del self.state[caller]

    @cached_property
    def _get_status(self):
        if not self.system:
            # Raising exception prevents invalid value from being cached when system is in pre-mature state
            raise SystemNotReady('System not ready yet -- this is normal when loading dump.')
        return self.call(None)

    #: Event that can be used to execute code right after callable setup. See :class:`.OfType`.
    #: Something that needs to be done manually this way, because Traits does not allow
    #: defining the order of subscribed function calls.
    on_setup_callable = Event

    def setup_callables(self):
        super(AbstractCallable, self).setup_callables()
        self.setup_callable_system(self.system, init=True)

    @on_trait_change('_args, _args_items', post_init=True)
    def objects_changed(self, name, old, new):
        if not self.system:
            return
        for o in new.added:
            if isinstance(o, AbstractCallable):
                o.setup_callable_system(self.system)

    @on_trait_change('_kwargs, _kwargs_items', post_init=True)
    def kwargs_changed(self, name, old, new):
        if not self.system:
            return
        for o in list(new.added.values()):
            if isinstance(o, AbstractCallable):
                o.setup_callable_system(self.system)

    @cached_property
    def _get_triggers(self):
        if not self.system:
            # Raising exception prevents invalid value from being cached when system is in pre-mature state
            raise SystemNotReady('System not ready yet -- this is normal when loading dump.')
        return self.collect('triggers')

    @cached_property
    def _get_targets(self):
        if not self.system:
            # Raising exception prevents invalid value from being cached when system is in pre-mature state
            raise SystemNotReady('System not ready yet -- this is normal when loading dump.')
        return self.collect('targets')

    def __getitem__(self, item):
        return self._args[item]

    def __setitem__(self, item, value):
        self._args[item] = value

    def __init__(self, *args, **kwargs):
        self._lock = Lock("Lock for callable " + self.__class__.__name__)
        self._kwargs = kwargs
        super(AbstractCallable, self).__init__()
        super(SystemObject, self).__init__()
        assert self.traits_inited()
        if args:
            self._args = args

    def __setstate__(self, state, trait_change_notify=True):
        self._lock = Lock("Lock for callable ")
        self._passed_arguments = None, state.copy()
        self.logger = logging.getLogger('automate.%s' % self.__class__.__name__)
        state.pop('name', '')
        super(SystemObject, self).__setstate__(state, trait_change_notify)

    def call_eval(self, value, caller, return_value=True, **kwargs):
        """
            Value might be either name registered in System namespace, or object, either
            StatusObject or Callable. If Callable, evaluate :meth:`.call` method. If StatusObject,
            return status.
        """
        value = self.name_to_system_object(value)
        if return_value and isinstance(value, AbstractStatusObject):
            return value.status
        if hasattr(value, 'call'):
            return self.call_eval(value.call(caller, **kwargs), caller, return_value, **kwargs)
        else:
            return value

    def _fix_list(self, lst):
        if isinstance(lst, dict):
            lst2 = list(lst.items())
        elif isinstance(lst, list):
            lst2 = enumerate(lst)
        for idx, obj in lst2:
            if isinstance(obj, basestring):
                lst[idx] = self.name_to_system_object(obj)
            if isinstance(obj, list):
                self._fix_list(obj)

    def setup_callable_system(self, system, init=False):
        """
            This function basically sets up :attr:`.system`, if it is not yet set up. After that,
            other Callable initialization actions are performed.

            :param init: value ``True`` is given when running this at the initialization phase. Then system
                         attribute is set already, but callable needs to be initialized otherwise.

        """
        if not self.system or init:
            self.system = system
            self._fix_list(self._args)
            self._fix_list(self._kwargs)
            for i in self.children:
                if isinstance(i, AbstractCallable):
                    i.setup_callable_system(system, init=init)
                elif isinstance(i, SystemObject):
                    i.system = system
            self.on_setup_callable = 1

    def call(self, *args, **kwargs):
        """
            The basic functionality of the Callable is implemented in this function.
            Needs to be defined in derived subclasses.

            If callable is used as a Program condition, this must return the value of the condition
            (see for example conditions :class:`.And`, :class:`.Sum` etc.), otherwise return value is optional.
        """
        raise NotImplementedError

    @property
    def objects(self):
        """
            Shortcut to :attr:`._args`.
        """
        return self._args

    @property
    def obj(self):
        """
            Shortcut property to the first stored object.
        """
        try:
            return self._args[0]
        except IndexError:
            return None

    @property
    def value(self):
        """
            Shortcut property to the second stored object.
        """
        try:
            return self._args[1]
        except IndexError:
            return None

    def name_to_system_object(self, value):
        """
        Return object for given name registered in System namespace.
        """
        if not self.system:
            raise SystemNotReady

        if isinstance(value, (basestring, Object)):
            rv = self.system.name_to_system_object(value)
            return rv if rv else value
        else:
            return value

    def collect(self, target):
        """Recursively collect all potential triggers/targets in this node and its children.
        Define targets and triggers of this particular callable in :meth:`_give_triggers`
        and :meth:`_give_targets`.

        :param str target: valid values: ``'targets'`` and ``'triggers'``
        """
        statusobjects = set()
        callables = set()
        objs_from_this_obj = getattr(self, '_give_%s' % target)()

        if not is_iterable(objs_from_this_obj):
            objs_from_this_obj = [objs_from_this_obj]

        if is_iterable(objs_from_this_obj):
            for i in (self.name_to_system_object(j) for j in objs_from_this_obj):
                if isinstance(i, AbstractStatusObject):
                    statusobjects.add(i)
                elif isinstance(i, AbstractCallable):
                    callables.add(i)

        for i in (self.name_to_system_object(j) for j in deep_iterate(callables)):
            if isinstance(i, AbstractCallable):
                statusobjects.update(getattr(i, target))

        return statusobjects

    def collect_triggers(self):
        return self.collect('triggers')

    def collect_targets(self):
        return self.collect('targets')

    @property
    def children(self):
        """
            A property giving a generator that goes through all the children of this Callable (not recursive)
        """
        return deep_iterate(self._args + list(self._kwargs.values())) #TODO: chain?

    def _give_triggers(self):
        """Give all triggers of this object (non-recursive)"""
        return self.children

    def _give_targets(self):
        """Give all targets of this object (non-recursive)"""
        return self.children

    def cancel(self, caller):
        """
            Recursively cancel all threaded background processes of this Callable.
            This is called automatically for actions if program deactivates.
        """
        for o in {i for i in self.children if isinstance(i, AbstractCallable)}:
            o.cancel(caller)

    def __repr__(self):
        return self.give_str()

    def __str__(self):
        return self.give_str()

    def _give_str(self, args, kwargs):
        if self in self.system.namespace.reverse:
            return repr(self.name)
        kwstr = u', '.join(k + u'=' + repr(v) for k, v in list(kwargs.items()))
        if kwstr and args:
            kwstr = ', ' + kwstr
        return str(self.__class__.__name__) + u"(" + u", ".join([repr(i) for i in args]) + kwstr + u")"

    def give_str(self):
        """
            Give string representation of the callable.
        """
        args = self._args[:]
        kwargs = self._kwargs
        return self._give_str(args, kwargs)

    @staticmethod
    def strip_color_tags(_str):
        return re.sub('__\w*__', "", _str)

    def _give_str_indented(self, args, kwargs, tags):
        if self in self.system.namespace.reverse:
            rv = repr(self.name)

        def indent(o_str):
            n_strs = []
            for o in o_str.split('\n'):
                n_strs.append(u'  ' + o)
            return '\n'.join(n_strs)

        def indented_str(obj, no_repr=False, no_color=False):
            if hasattr(obj, 'give_str_indented') and not obj in self.system.namespace.reverse:
                rv = obj.give_str_indented(tags)
            else:
                rv = str(obj if no_repr else repr(obj))
                if not no_color:
                    rv = ('__ACT__' if getattr(obj, 'status', obj) else '__INACT__') + rv
            return indent(rv)

        def in_one_line(obj):
            rv = repr(obj)
            if not isinstance(obj, AbstractCallable):
                rv = ('__ACT__' if getattr(obj, 'status', obj) else '__INACT__') + rv
            return rv

        kwstrs = [k + u'=' + in_one_line(v) for k, v in list(kwargs.items())]

        argstr = u"(\n" + indent(u", \n".join([indented_str(i) for i in args] +
                                              [indented_str(i, no_repr=True, no_color=True) for i in kwstrs]) + u"\n)")
        if len(self.strip_color_tags(argstr)) < 35:
            argstr = u"(" + u", ".join([in_one_line(i) for i in args] + kwstrs) + u")"

        rv = str(self.__class__.__name__) + argstr
        if tags:
            rv = ('__ACT__' if self.status else '__INACT__') + rv
        return rv

    def give_str_indented(self, tags=False):
        """
            Give indented string representation of the callable.
            This is used in :ref:`automate-webui`.
        """
        args = self._args[:]
        kwargs = self._kwargs
        rv = self._give_str_indented(args, kwargs, tags)
        if not tags:
            rv = self.strip_color_tags(rv)
        return rv

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self._args, self._kwargs) == (other._args, other._kwargs)
        return False

    def __hash__(self):
        return id(self)