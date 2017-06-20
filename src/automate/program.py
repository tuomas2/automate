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

from traits.api import cached_property, on_trait_change, CFloat, Instance, CBool, CSet, Property

from automate.common import (LogicStr, Lock, NameOrSensorActuatorBaseTrait,
                             AbstractStatusObject)
from automate.systemobject import SystemObject
from automate.callable import AbstractCallable


class ProgrammableSystemObject(SystemObject):

    """
        System object with standard program features (i.e. conditions & actions).
    """

    simple_view = ['active']
    view = ["name", "priority", "tags", "active_condition_str", "update_condition_str",
            "on_activate_str", "on_deactivate_str", "on_update_str", "triggers_str"] + SystemObject.view

    callables = ['on_activate', 'on_deactivate', 'on_update', 'active_condition', 'update_condition']

    def get_default_callables(self):
        from automate.callables import Value, Empty
        return dict(
            active_condition=Value(True),
            update_condition=Value(True),
            on_activate=Empty(),
            on_update=Empty(),
            on_deactivate=Empty(),
        )

    #: A condition Callable which determines the condition, when the program is activated. Program deactivates, when
    #: condition turns to False. When program is activated, on_activate action is executed. When program
    #: deactivates. on_deactivate is executed.
    active_condition = Instance(AbstractCallable)

    #: An action Callable to be executed when Program actives.
    on_activate = Instance(AbstractCallable)

    #: An action Callable to be executed when Program deactivates.
    on_deactivate = Instance(AbstractCallable)

    #: When program is active, this is the condition Callable that must equal to ``True`` in order to
    #: on_update action to be executed. Whenever a trigger is changed, this condition is checked and
    #: if ``True``, on_update is executed.
    update_condition = Instance(AbstractCallable)

    #: Action Callable to be executed if Program is active and update_condition is ``True``.
    on_update = Instance(AbstractCallable)

    #: When programs sets Actuator status, the actual status of Actuator is determined by a program that has highest
    #: priority. Lower priority programs are stacked and used only if higher priority programs are deactivated.
    priority = CFloat(1)

    #: Is program active? Automatically changed. In UIs you can fake the program active status by changing this.
    #: Normally do not change manually.
    active = CBool(False, transient=True)

    #: Status property is introduced to have interface compability with Status objects.
    #: For plain Programs, status equals to the result of its active condition Callable.
    status = Property(depends_on='active')

    @cached_property
    def _get_status(self):
        return self.active

    # Lock for trigger.
    _trigger_lock = Instance(Lock, transient=True)

    def __init__(self, *args, **kwargs):
        self._trigger_lock = Lock('triggerlock')
        super(ProgrammableSystemObject, self).__init__(*args, **kwargs)

    def __setstate__(self, *args, **kwargs):
        self._trigger_lock = Lock('triggerlock')
        return super(ProgrammableSystemObject, self).__setstate__(*args, **kwargs)

    #: (read-only property) Set of triggers, that cause this Program conditions to be checked
    #: (and actions to be executed). This data is updated from custom triggers list, conditions and actions.
    actual_triggers = Property(trait=CSet(trait=Instance(AbstractStatusObject)),
                               depends_on='triggers, triggers_items, exclude_triggers, exclude_triggers_items, '
                               'update_condition.triggers, active_condition.triggers, on_update.triggers, '
                               'on_activate.triggers')

    #: (read-only property) Set of targets that this Program might touch. This data is updated
    #: from custom targets list and actions.
    actual_targets = Property(trait=CSet(trait=Instance(AbstractStatusObject)),
                              depends_on='targets, targets_items, on_update.targets, on_activate.targets, '
                                         'on_deactivate.targets')

    #: Custom set of additional triggers, whose status change will trigger this Program conditions/actions
    triggers = CSet(trait=NameOrSensorActuatorBaseTrait)

    #: Triggers in this set do not trigger the program actions/conditions even if they are introduced by
    #: Callables etc.
    exclude_triggers = CSet(trait=NameOrSensorActuatorBaseTrait)

    #: Additional targets. Not usually needed, but if you want to set status for some reason by some custom function,
    #: for example, then you need to use this.
    targets = CSet(trait=NameOrSensorActuatorBaseTrait)

    logger = Instance(logging.Logger, transient=True)

    # Getter and setter used by _str versions of conditions, actions and targets&triggers lists.
    def _str_getter(self, name, trait):
        attr_name = name[:-4]
        attr = getattr(self, attr_name)
        if hasattr(attr, "give_str"):
            return attr.give_str()
        else:
            return str(attr)

    def _str_setter(self, name, value):
        attr_name = name[:-4]
        f = self.system.eval_in_system_namespace(value)
        if f is not None:
            setattr(self, attr_name, f)

    # For UIs, string versions of the Callables
    update_condition_str = Property(depends_on="update_condition, actual_triggers.name, actual_targets.name",
                                    trait=LogicStr, transient=True, fset=_str_setter, fget=_str_getter)
    on_update_str = Property(depends_on="on_update, actual_triggers.name, actual_targets.name", trait=LogicStr,
                             transient=True, fset=_str_setter, fget=_str_getter)
    active_condition_str = Property(depends_on="active_condition, actual_triggers.name, actual_targets.name",
                                    trait=LogicStr, transient=True, fset=_str_setter, fget=_str_getter)
    on_activate_str = Property(depends_on="on_activate, actual_triggers.name, actual_targets.name", trait=LogicStr,
                               transient=True, fset=_str_setter, fget=_str_getter)
    on_deactivate_str = Property(depends_on="on_deactivate, actual_triggers.name, actual_targets.name",
                                 trait=LogicStr, transient=True, fset=_str_setter, fget=_str_getter)

    targets_str = Property(depends_on="targets, targets.name", trait=LogicStr,
                           transient=True, fset=_str_setter, fget=_str_getter)
    triggers_str = Property(depends_on="triggers, triggers.name", trait=LogicStr,
                            transient=True, fset=_str_setter, fget=_str_getter)

    @cached_property
    def _get_actual_triggers(self):
        for c in [self.update_condition, self.active_condition, self.on_update, self.on_activate]:
            c.setup_callable_system(self.system)
        return (self.triggers | self.update_condition.triggers | self.active_condition.triggers
                | self.on_update.triggers | self.on_activate.triggers) - self.exclude_triggers

    @cached_property
    def _get_actual_targets(self):
        for c in [self.on_update, self.on_activate, self.on_deactivate]:
            c.setup_callable_system(self.system)
        return self.targets | self.on_update.targets | self.on_activate.targets | self.on_deactivate.targets

    @on_trait_change('actual_triggers')
    def actual_triggers_changed(self, obj, name, old, new):
        if old is None:
            old = set()
        if old == new:
            return
        self.logger.debug('Actual triggers changed by %s: %s->%s', name, old, new)
        for t in old - new:
            self.logger.debug("Removing trigger %s", t)
            t.on_trait_change(self.trigger_status_changed, "status", remove=True)

        for t in new - old:
            self.logger.debug("Adding trigger %s", t)
            t.on_trait_change(self.trigger_status_changed, "status")

        old_active = self.active
        self.active = bool(self.active_condition.call(self))
        if self.active != old_active:
            self.update_activation(self.active)

    @on_trait_change('actual_targets')
    def actual_targets_changed(self, obj, name,  old, new):
        if old == new:
            return
        if old is None:
            old = set()
        self.logger.debug('Actual targets changed %s->%s', old, new)
        old_active = self.active
        new_active = self.active = bool(self.active_condition.call(self))
        if new_active != old_active:
            self.update_activation(new_active)

        if old_active == new_active == True:
            for i in old - new:
                i.deactivate_program(self)

            for i in new - old:
                i.activate_program(self)

    def update_activation(self, new_active, trigger=None):
        if new_active:
            for t in self.actual_targets:
                t.activate_program(self)
            self.on_activate.setup_callable_system(self.system)
            self.on_activate.call(self, trigger=trigger)
            if bool(self.update_condition.call(self, trigger=trigger)):
                self.on_update.setup_callable_system(self.system)
                self.on_update.cancel(self)
                self.on_update.call(self, trigger=trigger)
        else:
            self.on_deactivate.setup_callable_system(self.system)
            self.on_deactivate.call(self, trigger=trigger)
            self.on_update.cancel(self)
            self.on_activate.cancel(self)
            for t in self.actual_targets:
                t.deactivate_program(self)

    def trigger_status_changed(self, obj, name, old, new):
        self.logger.debug("Trigger status changed from %s %s: %s->%s", obj, name, old, new)
        with self._trigger_lock:
            old_active = self.active
            new_active = self.active = bool(self.active_condition.call(self, trigger=obj))
            if new_active != old_active:
                self.update_activation(new_active, trigger=obj)
            if old_active == new_active == True:
                if bool(self.update_condition.call(self, trigger=obj)):
                    self.on_update.cancel(self)
                    self.on_update.call(self, trigger=obj)
        self.logger.debug("Trigger status changing ready")

    @on_trait_change("active_condition, on_activate, on_deactivate")
    def _update_activation_actions(self, name, new):
        self.logger.debug('Update activation actions %s', name)
        getattr(self, name).setup_callable_system(self.system)

        if name == 'active_condition':
            old_active = self.active
            self.active = bool(self.active_condition.call(self))
            if old_active != self.active:
                self.update_activation(self.active)

        elif name == 'on_activate' and self.active:
            self.on_activate.cancel(self)
            self.on_activate.call(self)

    @on_trait_change('update_condition, on_update')
    def _update_update_actions(self, name, new):
        self.logger.debug('Update update actions %s', name)
        getattr(self, name).setup_callable_system(self.system)

        if self.active and bool(self.update_condition.call(self)):
            self.on_update.cancel(self)
            self.on_update.call(self)

    def setup_system(self, system, *args, **kwargs):
        from .callables import Value
        c = self.get_default_callables()
        c.pop('active_condition')  # We do not want to activate program at this phase.
        c.pop('update_condition')  # nor do we want to run on_update
        self.active_condition = Value(False)
        self.update_condition = Value(False)
        for key, value in list(c.items()):
            setattr(self, key, value)

        super(ProgrammableSystemObject, self).setup_system(system, *args, **kwargs)

    def _priority_changed(self):
        self.logger.debug('Priority changed')
        for t in self.actual_targets:
            t.update_program_stack()


class Program(ProgrammableSystemObject):
    is_program = True
    editable = True


class DefaultProgram(ProgrammableSystemObject):
    editable = True

    def __init__(self, system, name='', **traits):
        self.logger = logging.getLogger('automate.defaultprogram')
        self._passed_arguments = name, traits
        self.setup_system(system)
        self.setup_callables()

    def get_default_callables(self):
        from automate.callables import Value
        callables = super(DefaultProgram, self).get_default_callables()
        callables['active_condition'] = Value(False)
        return callables
