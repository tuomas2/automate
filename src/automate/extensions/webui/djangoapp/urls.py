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
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""

from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^login$', views.login, name='login'),
    url(r'^$', views.main, name='main'),
    url(r'^logout$', views.logout, name='logout'),
    url('^custom/(\w*)$', views.custom, name='custom'),
    url('^uml/system.svg$', views.puml_svg, name='puml_svg'),
    url('^uml/system.puml$', views.puml_raw, name='puml_raw'),
    url('^uml$', views.plantuml, name='plantuml'),

    url('^system$', views.system_view, name='system'),
    url("^threads$", views.threads, name='threads'),

    url('^tag/([\w:]*)', views.single_tag, name='single_tag'),

    url('^tag$', views.tags_view, name='tags_view'),
    url('^user_editable_view$', views.user_defined_view, name='user_editable_view'),
    url('^user_defined_view$', views.tags_view, name='user_defined_view'),
    url('^only_groups$', views.tag_view_only_groups, name='tag_view_only_groups'),
    url('^info_panel/(\w*)', views.info_panel, name='info_panel'),
    url('^toggle_sensor/(\w*)$', views.toggle_sensor, name='toggle_sensor'),
    url(r'^toggle/(\w*)$', views.toggle_value, name='toggle_value'),
    url(r'^set/(\w*)/(\w*)$', views.set_value, name='set_value'),
    url(r'^set_ready/(\w*)/(\w*)', views.set_ready, name='set_ready'),
    url(r'^reload_service/(\d*)$', views.reload_service, name='reload_service'),
    url(r'^cancel_thread/(\d*)$', views.cancel_thread, name='cancel_thread'),
    url(r'^edit/(\w*)$', views.edit, name='edit'),
    url(r'^continue_edit/(\w*)/(\w*)$', views.continue_edit, name='continue_edit'),
    url(r'^new/(\w*)$', views.new, name='new'),
    url('^console$', views.console, name='console'),

    url('^set_status$', views.set_status, name='set_status'),
    url('^.*', views.notfound, name='notfound'),
]