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

import re
import operator
import logging

from django import template
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe

from automate.statusobject import StatusObject
from automate.program import Program

from ..forms import QUICK_EDITS

logger = logging.getLogger('automate.webui')

register = template.Library()


@register.simple_tag
def program_status(actuator, program):
    try:
        return active_color((actuator, program), actuator.program_status[program])
    except KeyError:
        return '-'


@register.filter
def name_sort(l):
    return sorted(list(l), key=operator.attrgetter('class_name', 'name'))


def active_color(obj, value, changing=None, display=None, program=False):
    if isinstance(obj, tuple):
        id = u'program_status_for_actuator'
    else:
        id = u'object_status_' + obj.name
    if program:
        id = u'program_active_' + obj.name

    if display is None:
        display = value
    if changing:
        rv = u'<em class="status_changing %s">%s</em>' % (id, display)
    else:
        if value:
            rv = u'<em class="status_active %s">%s</em>' % (id, display)
        else:
            rv = u'<em class="status_inactive %s">%s</em>' % (id, display)

    return mark_safe(rv)


@register.simple_tag()
def program_active(obj):
    return active_color(obj, obj.active, False, program=True)


@register.simple_tag(takes_context=True)
def row_attrs(context, name, prefix=""):
    source = context['source']
    url = reverse('info_panel', args=(name,))
    return 'data-url="{url}?source={source}" data-name="{name}"'.format(
        name=name,
        url=url,
        source=source,
    )


@register.simple_tag()
def object_status(obj):
    if isinstance(obj, Program):
        return active_color(obj, obj.active, False)
    if isinstance(obj, StatusObject):
        return active_color(obj, obj.status, obj.changing, display=obj.get_status_display())
    else:
        return active_color(obj, obj.get_status_display(), False)


@register.simple_tag
def condition_string(prog, attr):
    def repl(matchobj):
        if matchobj.group(1) == '__ACT__':
            return u'<em class="condition_active">%s</em>' % matchobj.group(2)
        else:
            return u'<em class="condition_inactive">%s</em>' % matchobj.group(2)

    cond = getattr(prog, attr)
    cond_str = cond.give_str_indented(tags=True)

    cond_str = re.sub(r"(__ACT__|__INACT__)('[^']*')", repl, cond_str)
    cond_str = re.sub(r"(__ACT__|__INACT__)(\"[^\"]*\")", repl, cond_str)
    cond_str = re.sub(r"(__ACT__|__INACT__)(\w*\()", repl, cond_str)
    cond_str = re.sub(r"(__ACT__|__INACT__)([\w=]*\b)", repl, cond_str)

    return mark_safe('<pre class="conditions">%s</pre>' % cond_str)


@register.assignment_tag(takes_context=True)
def sensor_form(context, sensor):
    try:
        form = QUICK_EDITS[sensor.data_type]({'status': sensor.status, 'name': sensor.name},
                                             source=context.get('source', 'main'), sensor=sensor)
    except Exception as e:
        logger.error('Error: %s', e)
        raise e
    return form
