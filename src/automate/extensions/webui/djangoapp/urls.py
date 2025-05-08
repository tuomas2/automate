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

"""
The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path, re_path

from . import views

urlpatterns = [
    path('login', views.login, name='login'),
    path('', views.main, name='main'),
    path('logout', views.logout, name='logout'),
    re_path(r'^custom/(\w*)$', views.custom, name='custom'),
    path('uml/system.svg', views.puml_svg, name='puml_svg'),
    re_path(r'^history.json/object/(\w*)$', views.history_json, name='history_json'),
    path('uml/system.puml', views.puml_raw, name='puml_raw'),
    path('uml', views.plantuml, name='plantuml'),

    path('system', views.system_view, name='system'),
    path('threads', views.threads, name='threads'),

    re_path(r'^tag/([\w:]*)$', views.single_tag, name='single_tag'),

    path('tag', views.tags_view, name='tags_view'),
    path('user_editable_view', views.user_defined_view, name='user_editable_view'),
    path('user_defined_view', views.tags_view, name='user_defined_view'),
    path('only_groups', views.tag_view_only_groups, name='tag_view_only_groups'),
    re_path(r'^info_panel/(\w*)$', views.info_panel, name='info_panel'),
    re_path(r'^toggle_sensor/(\w*)$', views.toggle_sensor, name='toggle_sensor'),
    re_path(r'^toggle/(\w*)$', views.toggle_value, name='toggle_value'),
    re_path(r'^set/(\w*)/(\w*)$', views.set_value, name='set_value'),
    re_path(r'^set_ready/(\w*)/(\w*)$', views.set_ready, name='set_ready'),
    re_path(r'^reload_service/(\d*)$', views.reload_service, name='reload_service'),
    re_path(r'^cancel_thread/(\d*)$', views.cancel_thread, name='cancel_thread'),
    re_path(r'^edit/(\w*)$', views.edit, name='edit'),
    re_path(r'^continue_edit/(\w*)/(\w*)$', views.continue_edit, name='continue_edit'),
    re_path(r'^new/(\w*)$', views.new, name='new'),
    path('console', views.console, name='console'),

    path('set_status', views.set_status, name='set_status'),
    re_path(r'^.*', views.notfound, name='notfound'),
]