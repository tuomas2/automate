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

    Module to allow using Django like a microframework.

"""
from __future__ import unicode_literals
from builtins import object

import sys
import os
from django.conf import settings
from django.conf.urls import url


def add_urls(*args):
    """Dynamically add new urls to django config"""
    import microdjango_urlconf
    microdjango_urlconf.urlpatterns += args


def route(urlstr, *args, **kwargs):
    """Decorator for adding new views to django config urls"""
    def add_route(view):
        import microdjango_urlconf
        kwargs.setdefault('name', view.__name__)
        microdjango_urlconf.urlpatterns.append(url(urlstr, view, *args, **kwargs))
        return view
    return add_route


def setup_django(**kwargs):
    if not settings.configured:
        class DummyModule(object):
            pass
        mymod = DummyModule()
        mymod.urlpatterns = []
        sys.modules['microdjango_urlconf'] = mymod
        mysettings = dict(
            ALLOWED_HOSTS=['*'],
            ROOT_URLCONF='microdjango_urlconf',
            TEMPLATE_DIRS=[os.path.join(os.path.dirname(__file__), 'templates')],
            TEMPLATE_LOADERS=(
                ('django.template.loaders.cached.Loader', (
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                )),
            ) if not kwargs['DEBUG'] else
            (
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ),

            INSTALLED_APPS=['crispy_forms',
                            'django.contrib.staticfiles',
                            'django.contrib.messages',
                            'automate.extensions.webui',
                            ],

            STATIC_URL='/static/',
            MESSAGE_STORAGE='django.contrib.messages.storage.session.SessionStorage',
            STATICFILES_DIRS = [os.path.join(os.path.dirname(__file__), 'static')],
            MIDDLEWARE_CLASSES=['django.middleware.csrf.CsrfViewMiddleware',
                                'django.contrib.sessions.middleware.SessionMiddleware',
                                'django.contrib.messages.middleware.MessageMiddleware',
                                ],
            SESSION_ENGINE="django.contrib.sessions.backends.file",
            CRISPY_TEMPLATE_PACK='bootstrap3',
            LOGGING = {  # set up logging such that log entries go to Automate logging
                'version': 1,
                'disable_existing_loggers': False,
                'handlers': {
                    'null': {
                        'level': 'DEBUG',
                        'class': 'logging.NullHandler',
                    }
                },
                'loggers': {
                    'django': {
                        'level': 'DEBUG',
                        'handlers': ['null'],
                    }
                }
            }
        )
        mysettings.update(kwargs)
        settings.configure(**mysettings)
