# (c) 2015-2017 Tuomas Airaksinen
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
import os
SECRET_KEY = 'insecure-default'
ALLOWED_HOSTS = ['*']
ROOT_URLCONF = 'automate.extensions.webui.djangoapp.urls'
USE_TZ=False

TEMPLATES = [
                {
                    'BACKEND': 'django.template.backends.django.DjangoTemplates',
                    'DIRS': [
                        # insert your TEMPLATE_DIRS here
                    ],
                    'APP_DIRS': True,
                    'OPTIONS': {
                        'context_processors': [
                            'django.template.context_processors.debug',
                            'django.template.context_processors.i18n',
                            'django.template.context_processors.media',
                            'django.template.context_processors.static',
                            'django.template.context_processors.tz',
                            'django.contrib.messages.context_processors.messages',
                            'automate.extensions.webui.djangoapp.views.common_context',
                        ],
                    },
                },
            ]

INSTALLED_APPS = ['crispy_forms',
                  'django.contrib.staticfiles',
                  'django.contrib.messages',
                  'automate.extensions.webui.djangoapp',
                  ]

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(os.path.dirname(__file__), 'static')
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
MIDDLEWARE_CLASSES = [
#    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]
#STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

SESSION_ENGINE = "django.contrib.sessions.backends.file"
CRISPY_TEMPLATE_PACK = 'bootstrap3'

LOGGING_CONFIG = None

#LOGGING = {  # set up logging such that log entries go to Automate logging
#    'version': 1,
#    'disable_existing_loggers': False,
#    'handlers': {
#        'null': {
#            'level': 'DEBUG',
#            'class': 'logging.NullHandler',
#        }
#    },
#    'loggers': {
#        'django': {
#            'level': 'DEBUG',
#            'handlers': ['null'],
#        }
#    }
#}