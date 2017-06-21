# (c) 2017 Tuomas Airaksinen
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

import pytest
from django.core.urlresolvers import reverse
from django.test import Client
from future.backports.urllib.parse import urlparse

from automate import *
from automate.extensions.webui import WebService


@pytest.fixture()
def sys_with_web():
    web = WebService(
        http_port=80811,
        http_auth=(
            ('test', 'test')
        ),
        debug=False,
        user_tags={'web'},
        read_only=False,
        default_view='tags_view',
        show_actuator_details=False,
        #static_dirs={'/webcam/(.*)': '/home/tuma/public_html/webcam/'},
        #custom_pages={'Webcam': webcam_page},
        #django_settings={
        #    'SESSION_FILE_PATH': '/var/cache/automatesession' if is_raspi() else '/tmp',
        #    'SESSION_COOKIE_AGE': 52560000},
    )
    class sys(System):
        s1 = UserBoolSensor()
        s2 = UserBoolSensor()
        a1 = BoolActuator(default=False)
        a2 = BoolActuator()

    s = sys(exclude_services=['TextUIService'], services=[web])
    s.flush()
    yield s
    s.cleanup()

class Http:
    OK = 200
    REDIR = 302
    FORBIDDEN = 304


def r(view_name, *args, **kwargs):
    return reverse(view_name, args=args, kwargs=kwargs)

@pytest.fixture
def constants(sys_with_web):
    class Pages:
        ROOT = '/'
        LOGIN = r('login')

        MAIN = r('main')
        TAGS = r('tags_view')
        USER1 = r('user_editable_view')
        USER2 = r('user_defined_view')
        GROUPS = r('tag_view_only_groups')
        CONSOLE = r('console')
        NEW_ACTUATOR = r('new', 'actuator')
        NEW_SENSOR = r('new', 'sensor')
        NEW_PROGRAM = r('new', 'program')

        BASIC_VIEWS = [TAGS, USER1, USER2, GROUPS, CONSOLE, NEW_ACTUATOR, NEW_PROGRAM, NEW_SENSOR]

        LOGOUT = r('logout')

    return Pages


@pytest.fixture()
def logged_client(sys_with_web, constants):
    client = Client()
    res = client.get('/')
    assert res.status_code == Http.REDIR
    assert u(res.url).startswith('/login')
    # let's login
    res = client.post(u(res.url), {'username': 'test', 'password': 'test'})
    assert res.status_code == Http.REDIR
    assert u(res.url) == constants.ROOT
    res = client.get(constants.ROOT)
    assert res.status_code == Http.REDIR
    assert u(res.url) == constants.TAGS

    yield client

    res = client.get(constants.LOGOUT)
    for p in constants.BASIC_VIEWS:
        res = client.get(p)
        assert res.status_code == Http.REDIR
        assert u(res.url).startswith(constants.LOGIN)


def u(url):
    return urlparse(url).path

def test_web(sys_with_web, logged_client, constants):
    for p in constants.BASIC_VIEWS:
        res = logged_client.get(p)
        assert res.status_code == Http.OK


# TODO:
# - test creating new objects
# - test editing objects via web
# - test changing status via web, via REST AND via websockets
# - test that console gets input
# - test making change via console

