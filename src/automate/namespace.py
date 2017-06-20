from __future__ import unicode_literals
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

from automate.systemobject import SystemObject
from automate.common import Group
from automate.service import AbstractService
from automate.callable import AbstractCallable


class Namespace(dict):
    """
        Namespace dictionary object for Automate System.
        Contains all SystemObjects stored in System by their names.
    """

    def __init__(self, system=None, *args, **kwargs):
        self.allow_overwrite = []
        self['system'] = self.system = system
        self['reverse'] = self.reverse = {}
        self['logger'] = self.logger = system.logger.getChild('logger')
        self['__name__'] = self.system.name + '_namespace'
        super(Namespace, self).__init__(*args, **kwargs)

    def give_systemobjects(self, system, tags=None):
        objs = []
        if not tags:
            tags = set()
        import inspect
        for name, obj in inspect.getmembers(system):
            if isinstance(obj, SystemObject):
                objs.append((name, obj, tags))
            if isinstance(obj, type) and issubclass(obj, Group):
                add_tags = tags.copy()
                if hasattr(obj, 'tags'):
                    add_tags = add_tags | set(obj.tags.split(','))
                objs.extend(self.give_systemobjects(obj, add_tags | {'group:%s' % name}))
        return objs

    def set_system(self, loadstate=None):
        if loadstate:
            objs = [(i._passed_arguments[1]['name'], i, []) for i in loadstate]
        else:
            objs = self.give_systemobjects(self.system)

        def order(x):
            if isinstance(x[1], AbstractCallable):
                # first handle plain callables
                ord = float('-inf')
            else:
                ord = x[1]._order
            return ord

        objs.sort(key=order)
        if objs:
            SystemObject._count = max(SystemObject._count, objs[-1][1]._order + 1)

        self.system.logger.info('Setup obj.system and names in namespace')

        for name, obj, groups in objs:
            obj.system = self.system
            if name in self:
                raise NameError('%s already in namespace!' % name)
            self[name] = obj

        self.logger.info('Set up system and groups into object tags')
        for name, obj, groups in objs:
            obj.setup_system(self.system, name, loadstate=loadstate)

            if not loadstate:
                is_groups = False
                for g in groups:
                    obj.tags.add(g)
                    if g.startswith('group:'):
                        is_groups = True
                if not is_groups:
                    obj.tags.add('group:root')

        # flush, so that sensor default initial statuses are up to date
        self.system.worker_thread.manual_flush()

        self.system.logger.info('Setup callables. This activates program features.')

        def order(x):
            if isinstance(x[1], AbstractCallable):
                # first handle plain callables
                ord = float('inf')
            else:
                # then programs starting from highest priority
                ord = getattr(x[1], 'priority', -1)
            return ord

        objs.sort(key=order, reverse=True)

        for name, obj, groups in objs:
            obj.setup_callables()

    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, super(Namespace, self).__repr__())

    def __delitem__(self, key):
        o = self[key]
        try:
            if o in self.reverse:
                del self.reverse[o]
        except TypeError as e:
            if not str(e).startswith("unhashable type"):
                raise

        if isinstance(o, SystemObject) and o in self.system.objects:
            self.system.objects.remove(o)
        super(Namespace, self).__delitem__(key)

    def update(self, d):
        for key, value in list(d.items()):
            self[key] = value

    def __setitem__(self, name, value):
        is_alias = False
        if name in self and name not in self.allow_overwrite:
            if isinstance(self[name], SystemObject):
                raise ValueError('Cannot overwrite %s in AutomateNamespace of %s' % (name, self.system.name))
            self.logger.warning('Overwriting %s in AutomateNamespace %s', name, self.system.name)

        try:
            if value in self.get('reverse', []):
                is_alias = True
        except TypeError as e:
            if not str(e).startswith("unhashable type"):
                raise

        super(Namespace, self).__setitem__(name, value)

        if name in self.allow_overwrite or is_alias:
            return
        if isinstance(value, AbstractService):
            self.system.services.append(value)
        elif isinstance(value, SystemObject):
            self.reverse[value] = name
            value.name_changed_event = True
            self.system.objects.add(value)

            if not value.system:
                value.setup_system(self.system, name)
                value.setup_callables()
