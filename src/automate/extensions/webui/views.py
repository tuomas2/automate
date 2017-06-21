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

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
import threading
from django.contrib import messages

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import render
from django.template import Template, RequestContext
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from .microdjango import route
from .forms import LoginForm, CmdForm, FORMTYPES, QUICK_EDITS, TextForm
from functools import wraps
from automate.statusobject import AbstractActuator
from automate.statusobject import AbstractSensor


def set_globals(_service, _system):
    global system, service
    system = _system
    service = _service


def common_context(request):
    global system, service
    views = [
        ('By types', 'system'),
        ('By groups', 'tag_view_only_groups'),
        ('By tags', 'tags_view'),
        ('User editable', 'user_editable_view'),
        ('User defined', 'user_defined_view'),
    ]
    import automate
    from automate.extensions import webui
    return {'views': views, 'system': system, 'service': service,
            'automate_version': automate.__version__}


def get_views(service):
    def require_login(func):
        @wraps(func)
        def wrapped(request, *args, **kwargs):
            if not request.session.get('logged_in', False):
                service.system.logger.debug('Require login')
                return HttpResponseRedirect(reverse('login') + '?%s' % urlencode({'url': request.META['PATH_INFO']}))
            service.system.flush()
            return func(request, *args, **kwargs)
        return wrapped

    @route('^login$')
    def login(request):
        url = request.GET.get('url', reverse('main'))
        if not service.http_auth or request.session.get('logged_in', False):
            request.session['logged_in'] = True
            return HttpResponseRedirect(url)
        if request.method == 'POST':
            form = LoginForm(request.POST, request=request)
            form.auth = service.http_auth
            if form.is_valid():
                request.session['logged_in'] = True
                return HttpResponseRedirect(url)
        else:
            form = LoginForm(request=request)
        form.helper.form_class = 'form-signin'
        form.helper.form_action += '?url=%s' % url
        return render(request, 'login.html', {'form': form, 'source': 'login'})

    @route('^$')
    @require_login
    def main(request):
        return HttpResponseRedirect(reverse(service.default_view))

    @route('^logout$')
    def logout(request):
        request.session['logged_in'] = False
        return HttpResponseRedirect('login')

    @route('^custom/(\w*)$')
    @require_login
    def custom(request, name):
        context = RequestContext(request, {'source': 'main'})
        try:
            return HttpResponse(content=Template(service.custom_pages[name]).render(context))
        except KeyError:
            raise Http404

    @route('^uml/system.svg$')
    @require_login
    def puml_svg(request):
        svg = service.system.request_service('PlantUMLService').write_svg()
        return HttpResponse(content=svg, content_type='image/svg+xml')

    @route('^uml/system.puml$')
    @require_login
    def puml_raw(request):
        puml = service.system.request_service('PlantUMLService').write_puml()
        return HttpResponse(content=puml, content_type='text/plain')

    @route('^uml$')
    @require_login
    def plantuml(request):
        puml_service = service.system.request_service('PlantUMLService')
        return render(request, 'views/plantuml.html', {'source': 'system',
                                                       'puml_service': puml_service,
                                                       })

    @route('^system$')
    @require_login
    def system(request):
        return render(request, 'views/system.html', {'source': 'system'})

    @route("^threads$")
    @require_login
    def threads(request):
        threads = [t.name for t in threading.enumerate()]
        threads.sort()
        return render(request, 'views/threads.html', {'threads': threads})

    @route('^tag/([\w:]*)')
    @require_login
    def single_tag(request, tag):
        objs = sorted([obj for obj in service.system.objects_sorted if tag in obj.tags])
        if not objs:
            raise Http404
        return render(request, 'views/single_tag_view.html',
                      {'source': 'tags_view', 'objs': objs, 'tag': tag})

    @route('^tag$')
    @require_login
    def tags_view(request, template='', only_user_editable=False, only_user_defined=False, only_groups=False):
        groups = {}
        if only_user_editable:
            objs = (i for i in service.system.objects_sorted if getattr(i, 'user_editable', False))
        elif only_user_defined:
            objs = (i for i in service.system.objects_sorted if service.user_tags & i.tags)
        else:
            objs = service.system.objects_sorted
        for obj in objs:
            for tag in obj.tags:
                if only_groups:
                    if not tag.startswith('group:'):
                        continue
                if tag in groups:
                    groups[tag].append(obj)
                else:
                    groups[tag] = [obj]

        gitems = sorted(groups.items())
        l = len(gitems)
        g1 = gitems[:int(l/3) + 1]
        g2 = gitems[int(l/3) + 1:2 * int(l/3) + 1]
        g3 = gitems[2 * int(l/3) + 1:]
        return render(request, 'views/tag_view.html' if not template else template,
                      {'source': 'user_editable_view' if only_user_editable else 'tags_view', 'groups': [g1, g2, g3]})

    @route('^user_editable_view$')
    @require_login
    def user_editable_view(request):
        return tags_view(request, template='views/user_editable_view.html', only_user_editable=True)

    @route('^user_defined_view$')
    @require_login
    def user_defined_view(request):
        return tags_view(request, template='views/user_defined_view.html', only_groups=True, only_user_defined=True)

    @route('^only_groups$')
    @require_login
    def tag_view_only_groups(request):
        return tags_view(request, template='views/only_groups.html', only_groups=True)

    @route('^info_panel/(\w*)')
    @require_login
    def info_panel(request, name):
        source = request.GET.get('source', 'main')
        if request.is_ajax():
            obj = service.system.namespace[name]
            view_items = obj.view[:] + ['class_name', 'data_type', 'next_scheduled_action']
            if 'change_delay' in view_items and not obj.change_delay:
                view_items.remove('change_delay')
                view_items.remove('change_mode')
            if 'safety_delay' in view_items and not obj.safety_delay:
                view_items.remove('safety_delay')
                view_items.remove('safety_mode')
            if 'reset_delay' in view_items and not obj.reset_delay:
                view_items.remove('reset_delay')
            info_items = [(i.capitalize().replace('_', ' '),
                           getattr(obj, i)) for i in view_items
                          if (not i.endswith('_str')
                              and i not in ['tags', 'name', 'priority', 'status']
                              and (getattr(obj, i, None) or type(getattr(obj, i, None)) in (int, float)))]

            callables = ((i.capitalize().replace('_', ' '), i) for i in obj.callables)

            textform = TextForm({'status': obj.status, 'name': obj.name},
                                source=source) if obj.data_type in ['str', 'unicode'] else None

            return render(request, 'info_panel.html', {'i': obj, 'source': source, 'info_items': info_items,
                                                       'callables': callables, 'textform': textform})
        else:
            raise Http404

    @route('^toggle_sensor/(\w*)$')
    @require_login
    def toggle_sensor(request, sensorname):
        """
        This is used only if websocket fails
        """
        if service.read_only:
            service.logger.warning("Could not perform operation: read only mode enabled")
            raise Http404
        source = request.GET.get('source', 'main')
        sensor = service.system.namespace[sensorname]
        sensor.status = not sensor.status
        service.system.flush()
        return HttpResponseRedirect(reverse(source))

    @route(r'^toggle/(\w*)$')
    @require_login
    def toggle_value(request, name):
        """
        For manual shortcut links to perform toggle actions
        """
        obj = service.system.namespace.get(name, None)
        if not obj or service.read_only:
            raise Http404
        new_status = obj.status = not obj.status
        if service.redirect_from_setters:
            return HttpResponseRedirect(reverse('set_ready', args=(name, new_status)))
        else:
            return set_ready(request, name, new_status)

    @route(r'^set/(\w*)/(\w*)$')
    @require_login
    def set_value(request, name, value):
        """
        For manual shortcut links to perform set value actions
        """
        obj = service.system.namespace.get(name, None)
        if not obj or service.read_only:
            raise Http404
        obj.status = value
        if service.redirect_from_setters:
            return HttpResponseRedirect(reverse('set_ready', args=(name, value)))
        else:
            return set_ready(request, name, value)

    @route(r'^set_ready/(\w*)/(\w*)')
    @require_login
    def set_ready(request, name, value):
        return render(request, 'views/toggle.html', {'name': name, 'status': value})

    @route(r'^edit/(\w*)$')
    @require_login
    def edit(request, name=None, type=None, cont=False):
        if service.read_only:
            service.logger.warning("Could not perform operation: read only mode enabled")
            raise Http404

        source = request.GET.get('source', 'main')
        if name:
            obj = service.system.namespace.get(name, None)
            if not obj:
                raise Http404
            if isinstance(obj, AbstractActuator):
                type = 'actuator'
            elif isinstance(obj, AbstractSensor):
                type = 'sensor'
            else:
                type = 'program'

        if not type:
            raise Http404

        FormType = FORMTYPES[type]

        if request.method == 'POST':
            if 'cancel' in request.POST:
                return HttpResponseRedirect(reverse(source))

            form = FormType(request.POST, request=request)
            form.setup_system(service.system)
            form.load(name)
            if form.is_valid():
                if form.has_changed():
                    form.save(name)
                if name:
                    return HttpResponseRedirect(reverse(source))
                else:
                    return HttpResponseRedirect(reverse('continue_edit', args=(type, form.instance.name,))
                                                + '?source=%s' % source)
        else:
            form = FormType(request=request)
            form.setup_system(service.system)
            form.load(name)
        return render(request, 'edit_object.html', {'type': type, 'editform': form,
                                                    "continue_edit": cont, 'source': source})

    @route(r'^continue_edit/(\w*)/(\w*)$')
    @require_login
    def continue_edit(request, type, name):
        if service.read_only:
            service.logger.warning("Could not perform operation: read only mode enabled")
            raise Http404
        return edit(request, type=type, name=name, cont=True)

    @route(r'^new/(\w*)$')
    @require_login
    def new(request, type):
        if service.read_only:
            service.logger.warning("Could not perform operation: read only mode enabled")
            raise Http404
        return edit(request, type=type, name=None)

    @route('^console$')
    @require_login
    def console(request):
        textarea = False
        if request.method == 'POST':
            cmdform = CmdForm(request.POST, textarea=True)
            if cmdform.is_valid():
                if not service.read_only:
                    service.system.cmd_exec(cmdform.cleaned_data['cmd'])
                else:
                    service.logger.warning("Could not perform operation: read only mode enabled")
                return HttpResponseRedirect('')
        else:
            textarea = request.GET.get('textarea', False)
            cmdform = CmdForm(textarea=textarea)

        log = mark_safe(service.system.request_service('LogStoreService').lastlog(lines=100))
        return render(request, 'views/console.html', dict(log=log, cmdform=cmdform, textarea=textarea))

    @route('^set_status$')
    @require_login
    def set_status(request):
        if service.read_only:
            service.logger.warning("Could not perform operation: read only mode enabled")
            raise Http404
        if request.method == 'POST':
            name = request.POST.get('name', None)
            status = request.POST.get('status', None)
            obj = service.system.namespace.get(name, None)
            if obj:
                service.logger.debug('POST: %s', request.POST)
                form = QUICK_EDITS[obj.data_type](request.POST, sensor=obj)
                if form.is_valid():
                    obj.status = form.cleaned_data['status']
                    service.system.flush()
                else:
                    messages.error(request, 'Error setting status %s to %s' % (name, status))
            else:
                messages.error(request, 'Error setting status of %s (no such object)' % name)

            return HttpResponseRedirect(reverse(request.GET.get('source', 'main')))
        else:
            raise Http404

    @route('^.*')
    def notfound(self):
        raise Http404
