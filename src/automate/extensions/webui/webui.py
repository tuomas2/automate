# -*- coding: utf-8 -*-
# (c) 2015 Tuomas Airaksinen
#
# This file is part of automate-webui.
#
# automate-webui is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# automate-webui is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with automate-webui.  If not, see <http://www.gnu.org/licenses/>.
#
# ------------------------------------------------------------------
#
# If you like Automate, please take a look at this page:
# http://evankelista.net/automate/

"""
    Web interface module for Automate
"""

import json
import datetime
import time
import os

import tornado.web
from tornado.websocket import WebSocketHandler, WebSocketClosedError

from traits.api import CBool, Tuple, Int, Str, CSet, List, CInt, Dict, Unicode

from automate.statusobject import StatusObject
from automate.extensions.wsgi import TornadoService
from automate import __version__

from django.contrib.sessions.backends.file import SessionStore


class WebService(TornadoService):

    """
    Web User Interface Service for Automate
    """

    #: Restrict usage to only monitoring statuses (default: ``True``).
    #: If WebService is not in read_only mode, it is possible to run arbitrary Python commands
    #: through eval/exec via web browser. This is, of course, a severe security issue.
    #: Secure SSL configuration HIGHLY recommended, if not operating in ``read_only`` mode.
    read_only = CBool(True)

    #: Default view that is displayed when entering the server.
    #: Can be the name of any view in views.py
    default_view = Str('system')

    #: HTTP port to listen
    http_port = Int(8080)

    #: Authentication for logging into web server. (user,password) pairs in a tuple.
    http_auth = Tuple

    #: Let websocket connection die after ``websocket_timeout`` time of no ping reply from client.
    websocket_timeout = CInt(60 * 5)

    #: Tags that are shown in user defined view
    user_tags = CSet(trait=Str, value={'user'})

    #: Django debugging mode (slower, more info shown when error occurs)
    debug = CBool(False)

    #: User-defined custom pages as a dictionary of form ``{name: template_content}``
    custom_pages = Dict(key_trait=Unicode, value_trait=Unicode)

    #: set to True, if you want to launch multiple servers with same system. Authentication and
    #: other settings are then taken from master service. Only web server settings (http host/port)
    #: are used from slave.
    slave = CBool(False)

    #: In this dictionary you can define your custom Django settings which will override the default ones
    django_settings = Dict()

    #: From /set/object/value and /toggle/object, redirect to /set_ready/object/value after after executing action
    redirect_from_setters = CBool(True)

    #: Show hidden objects in web UI (those prefixed with _)
    show_hidden = CBool(False)

    #: Full exposed url root
    server_url = Unicode()

    _sockets = List(transient=True)

    def get_filehandler_class(service):
        class MyFileHandler(tornado.web.StaticFileHandler):

            def validate_absolute_path(self, *args, **kwargs):
                session_id = getattr(self.request.cookies.get('sessionid', None), 'value', None)
                session_data = SessionStore(session_key=session_id)
                if not session_data.get('logged_in', False):
                    raise tornado.web.HTTPError(403, 'not logged in')

                return super().validate_absolute_path(*args, **kwargs)

            def check_etag_header(self):
                """ Disable etag_header checking (checks only modified time). Due to etag caching
                    file changes were not detected at all. """
                return False
        return MyFileHandler

    def get_tornado_handlers(self):
        if self.slave:
            return self.system.request_service('WebService').get_tornado_handlers()
        super_handlers = super().get_tornado_handlers()
        path = os.path.join(os.path.dirname(__file__), 'static')
        static = [('/static/(.*)', tornado.web.StaticFileHandler, {'path': path})]
        return static + super_handlers

    def setup(self):
        if not self.slave:
            os.environ['DJANGO_SETTINGS_MODULE'] = 'automate.extensions.webui.settings'
            from django.conf import settings
            settings.DEBUG = self.debug
            if not 'SECRET_KEY' in self.django_settings:
                self.logger.warning('Insecure settings! Please set proper SECRET_KEY in '
                                    'WebService.django_settings!')
            if not 'TIME_ZONE' in self.django_settings:
                os.environ.pop('TZ')  # Django uses America/Chicago as default timezone. Let's clean this up.
                time.tzset()
            if self.server_url:
                self.django_settings['SERVER_URL'] = self.server_url
            if self.system.raven_dsn:
                settings.INSTALLED_APPS.append('raven.contrib.django.raven_compat')
                settings.RAVEN_CONFIG = {'dsn': self.system.raven_dsn, 'release': __version__}
            installed_apps = self.django_settings.pop('INSTALLED_APPS', None)
            if installed_apps:
                settings.INSTALLED_APPS.extend(list(installed_apps))

            for key, value in self.django_settings.items():
                setattr(settings, key, value)

            from automate.extensions.webui.djangoapp.views import set_globals
            set_globals(self, self.system)

        super().setup()
        if not self.slave:
            self.system.request_service('LogStoreService').on_trait_change(self.push_log, 'most_recent_line')

            self.system.on_trait_change(self.update_sockets, 'objects.status, objects.changing, objects.active, '
                                        'objects.program_status_items')

    def get_websocket(service):
        if service.slave:
            return service.system.request_service('WebService').get_websocket()

        class WebSocket(WebSocketHandler):

            def data_received(self, chunk):
                pass

            def __init__(self, application, request, **kwargs):
                self.log_requested = False
                self.subscribed_objects = set()
                self.last_message = None
                self.logged_in = False

                super().__init__(application, request, **kwargs)

            def check_origin(self, origin):
                return True

            def write_json(self, **kwargs):
                msg = json.dumps(kwargs)
                service.logger.debug('Sending to client %s', msg)
                self.write_message(msg)

            def open(self):
                self.session_id = session_id = getattr(self.request.cookies.get('sessionid', None), 'value', None)
                session_data = SessionStore(session_key=session_id)

                if session_data.get('logged_in', False) or not service.http_auth:
                    self.logged_in = True
                else:
                    service.logger.warning("Not (yet) logged in %s", session_id)

                service.logger.debug("WebSocket opened for session %s", session_id)
                service._sockets.append(self)

            def _authenticate(self, username, password):
                if (username, password) == service.http_auth:
                    self.logged_in = True
                    service.logger.debug('Websocket user %s logged in.', username)
                else:
                    service.logger.warning('Authentication failure: user %s with passwd %s != %s ',
                                           username, password, service.http_auth)
                    self.close()

            def _ping(self):
                pass

            def _set_status(self, name, status):
                if service.read_only:
                    service.logger.warning("Could not perform operation: read only mode enabled")
                    return
                obj = service.system.namespace.get(name, None)
                if obj:
                    obj.status = status

            def _subscribe(self, objects):
                self.subscribed_objects.update(objects)

            def _unsubscribe(self, objects):
                self.subscribed_objects -= set(objects)

            def _clear_subscriptions(self):
                self.subscribed_objects.clear()

            def _send_command(self, command):
                if not service.read_only:
                    service.system.cmd_exec(command)
                else:
                    service.logger.warning("Could not perform operation: read only mode enabled")

            def _fetch_objects(self):
                data = [(i.name, i.get_as_datadict()) for i in service.system.objects_sorted]
                self.write_json(action='return', rv=data)

            def _request_log(self):
                self.log_requested = True

            def on_message(self, json_message):
                """
                    Message format: {'action': 'action_name', other_kwargs...)
                """

                message = json.loads(json_message)
                service.logger.debug('Message received from client: %s', message)

                action = message.pop('action', '')

                if self.logged_in:
                    action_func = getattr(self, '_' + action, None)
                    if action_func:
                        service.logger.debug('Running websocket action %s', action)
                        action_func(**message)
                    else:
                        service.logger.error('Not logged in or unknown message %s', message)
                elif action == 'authenticate':
                    return self._authenticate(**message)

                self.last_message = datetime.datetime.now()

            def on_close(self):
                service.logger.debug("WebSocket closed for session %s", self.session_id)
                service._sockets.remove(self)

        return WebSocket

    def push_log(self, new):
        for s in self._sockets:
            if s.log_requested:
                try:
                    s.write_json(action='log', data=new)
                except WebSocketClosedError:
                    pass

    def update_sockets(self, obj, attribute, old, new):
        from django.template.loader import render_to_string
        if isinstance(obj, StatusObject):
            self.logger.debug('Update_sockets %s %s %s %s', obj, attribute, old, new)
            for s in self._sockets:
                if s.last_message and (s.last_message < datetime.datetime.now()
                                       - datetime.timedelta(seconds=self.websocket_timeout)):
                    self.logger.info('Closing connection %s due to timeout', s.session_id)
                    s.on_close()
                    s.close(code=1000, reason='Timeout')
                    continue
                if obj.name in s.subscribed_objects:
                    if attribute == 'active':
                        s.write_json(action='program_active', name=obj.name, active=obj.active)
                    elif attribute in ['status', 'changing']:
                        s.write_json(action='object_status',
                                     name=obj.name,
                                     status=obj.status,
                                     time=int(1000*time.time()),
                                     display=obj.get_status_display(),
                                     changing=obj.changing)

    def get_wsgi_application(self):
        from django.core.wsgi import get_wsgi_application
        return get_wsgi_application()
