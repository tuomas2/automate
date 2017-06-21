# -*- coding: utf-8 -*-
# (c) 2015 Tuomas Airaksinen
#
# This file is part of automate-rpc.
#
# automate-rpc is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# automate-rpc is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with automate-rpc.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
from builtins import object
from . import wsgi_xmlrpc
from traits.api import CSet, Str, Any

from automate.extensions.wsgi.abstractwsgi import TornadoService


class ExternalApi(object):

    def __init__(self, system, tag):
        self.system = system
        self.tag = tag

    def set_status(self, name, status):
        """
            Set sensor ``name`` status to ``status``.
        """
        getattr(self.system, name).status = status
        return True

    def get_status(self, name):
        """
            Get status of object with name ``name``.
        """
        return getattr(self.system, name).status

    def set_object_status(self, statusdict):
        """
            Set statuses from a dictionary of format ``{name: status}``
        """
        for name, value in statusdict.items():
            getattr(self.system, name).status = value
        return True

    def toggle_object_status(self, objname):
        """
            Toggle boolean-valued sensor status between ``True`` and ``False``.
        """
        o = getattr(self.system, objname)
        o.status = not o.status
        self.system.flush()
        return o.status

    def get_sensors(self):
        """
            Get sensors as a dictionary of format ``{name: status}``
        """
        return {i.name: i.status for i in self.system.sensors}

    def get_websensors(self):
        """
            Get sensors with defined tag as a dictionary of format ``{name: status}``
        """
        return {i.name: i.status for i in self.system.sensors if self.tag & i.tags}

    def get_actuators(self):
        """
            Get actuators as a dictionary of format ``{name: status}``
        """
        return {i.name: i.status for i in self.system.actuators}

    def flush(self):
        """
            Flush the system queue. If you have just set a status and then read a value,
            it might be necessary to flush queue first, such that related changes have been
            applied.
        """
        self.system.flush()

    def is_alive(self):
        """
            Simple RPC command that returns always True.
        """
        return True

    def log(self):
        """
            Return recent log entries as a string.
        """
        logserv = self.system.request_service('LogStoreService')
        return logserv.lastlog(html=False)


class RpcService(TornadoService):

    #: Tags that are displayed via get_websensors RPC function
    view_tags = CSet(trait=Str, value={'rpc'})

    #: If you want to define custom api (similar to, or derived from :class:`.ExternalApi`, it can be given here.
    api = Any

    def get_wsgi_application(self):
        instance = self.api or ExternalApi(self.system, tag=self.view_tags)
        wsgiapp = wsgi_xmlrpc.WSGIXMLRPCApplication(instance=instance)
        return wsgiapp
