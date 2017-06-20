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

from __future__ import division
from __future__ import unicode_literals
import re
import keyword

import django.forms as forms
from django.core.urlresolvers import reverse
from django.contrib import messages

from traits.api import TraitError

from automate.callable import AbstractCallable
from automate.program import Program

fieldtypes = {int: forms.IntegerField, float: forms.FloatField, bool: forms.BooleanField}


class TextForm(forms.Form):

    """
    Larger text edit form shown in info panel for user_editable text objects
    """
    name = forms.CharField(widget=forms.HiddenInput())
    status = forms.CharField(widget=forms.Textarea(attrs={'rows': 2, 'class': 'mytextbox'}), required=False)

    def __init__(self, data=None, source='', **kwargs):
        super(TextForm, self).__init__(data, **kwargs)
        from crispy_forms.helper import FormHelper
        from crispy_forms.layout import Layout, Submit
        self.helper = FormHelper()
        self.helper.layout = Layout('name', 'status', Submit('set_status', 'Set', css_class='textform_submit'))
        self.helper.form_class = "form-horizontal"
        self.helper.form_action = reverse('set_status') + '?source=%s' % source


class QuickEdit(forms.Form):

    """
    Small quick edit forms that are used in main views to edit object statuses
    """
    name = forms.CharField(widget=forms.HiddenInput())
    status = forms.BooleanField()

    def __init__(self, data=None, source='', sensor=None, **kwargs):
        super(QuickEdit, self).__init__(data, **kwargs)
        self.fields['status'].label = ''
        from crispy_forms.helper import FormHelper
        from crispy_forms.bootstrap import FieldWithButtons
        from crispy_forms.layout import Layout, Submit
        self.helper = FormHelper()
        self.helper.layout = Layout('name', FieldWithButtons('status', Submit('set_status', '>')))
        self.helper.form_class = "form-inline quickedit"
        self.helper.form_action = reverse('set_status') + '?source=%s' % source


class NumericQuickEdit(QuickEdit):
    status = forms.Field()

    def __init__(self, data=None, source='', sensor=None, **kwargs):
        from crispy_forms.bootstrap import FieldWithButtons
        from crispy_forms.layout import Layout, Submit, Field
        super(NumericQuickEdit, self).__init__(data, source, sensor, **kwargs)
        if sensor.is_finite_range:
            field = self.fields['status']
            field.sensor_name = sensor.name
            field.min_value = self.num_type(sensor.value_min)
            field.max_value = self.num_type(sensor.value_max)
            if self.num_type is int:
                field.step = 1
            else:
                field.step = (sensor.value_max - sensor.value_min)/10000.

            self.helper.layout = Layout('name', Field('status', template='slider.html'))
        else:
            self.helper.layout = Layout('name', FieldWithButtons('status', Submit('set_status', '>')))


class IntQuickEdit(NumericQuickEdit):
    num_type = int
    status = forms.IntegerField()


class FloatQuickEdit(NumericQuickEdit):
    num_type = float
    status = forms.FloatField()


class StrQuickEdit(QuickEdit):
    status = forms.CharField(required=False)


class BoolQuickEdit(QuickEdit):
    status = forms.BooleanField()

QUICK_EDITS = dict(str=StrQuickEdit, unicode=StrQuickEdit, int=IntQuickEdit, float=FloatQuickEdit, bool=BoolQuickEdit)


class BaseForm(forms.Form):

    """
    Base crispy form for full-page forms such as LoginForm and SystemObjectForms
    """

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(BaseForm, self).__init__(*args, **kwargs)
        from crispy_forms.helper import FormHelper
        from crispy_forms.layout import Submit
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Submit'))
        self.helper.add_input(Submit('cancel', 'Cancel'))
        self.helper.form_class = 'form-horizontal'


class LoginForm(BaseForm):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput())

    def clean(self):
        cleaned_data = super(LoginForm, self).clean()
        if (cleaned_data.get('username') != self.auth[0]
                or cleaned_data.get('password') != self.auth[1]):
            raise forms.ValidationError('Username or password is not correct', code='invalid')
        return cleaned_data


class CmdForm(forms.Form):
    cmd = forms.CharField(label='Command', widget=forms.TextInput(attrs={'autocomplete': 'off'}))

    def __init__(self, *args, **kwargs):
        textarea = kwargs.pop('textarea', False)
        super(CmdForm, self).__init__(*args, **kwargs)
        from crispy_forms.helper import FormHelper
        self.helper = FormHelper()
        from crispy_forms.bootstrap import FieldWithButtons
        from crispy_forms.layout import Layout, Submit
        if textarea:
            self.fields['cmd'].widget = forms.Textarea(attrs=dict(cols=30, rows=3))
            self.helper.layout = Layout('cmd', Submit('run_cmd', 'Run'))
        else:
            self.helper.layout = Layout(FieldWithButtons('cmd', Submit('run_cmd', 'Run')))
        self.helper.form_class = "form-horizontal"


class SystemObjectForm(BaseForm):
    name = forms.CharField()
    description = forms.CharField(widget=forms.Textarea(attrs=dict(rows=3)), required=False)
    tags = forms.MultipleChoiceField(required=False)
    new_tags = forms.CharField(required=False, initial='')

    def get_object(self, name):
        obj = self.system.namespace.get(name, None)
        self.instance = obj or self.new(self.cleaned_data['name'])
        return self.instance

    def save(self, objname):
        obj = self.get_object(objname)
        for key, value in self.cleaned_data.items():
            if key in self.changed_data:
                if key == 'new_tags':
                    for tag in value.split(','):
                        obj.tags.add(tag)
                    continue
                try:
                    setattr(obj, key, value)
                except Exception as e:
                    messages.error(self.request, 'Error was caught when trying to set %s: %s' % (key, e))

    def clean_name(self):
        name = self.cleaned_data['name']
        if 'name' in self.changed_data and name in self.system.namespace:
            raise forms.ValidationError('Name already in %s namespace' % self.system.name)
        if not re.match("^[_A-Za-z][_a-zA-Z0-9]*$", name):
            raise forms.ValidationError('Illegal characters')
        if keyword.iskeyword(name):
            raise forms.ValidationError('Name is python keyword')
        return name

    def setup_system(self, system):
        self.system = system
        self.load_from_system()

    def load_from_system(self):
        all_tags = list(self.system.all_tags)
        self.fields['tags'].choices = [(i, i) for i in all_tags if i]

    @property
    def class_name(self):
        if hasattr(self, 'instance'):
            return self.instance.class_name
        else:
            return 'New ' + self.__class__.__name__.replace('Form', '')

    def load(self, objname):
        if objname:
            # fill those defined fields that are without initial value
            self.obj = obj = self.system.namespace[objname]
            self.instance = obj
            self.fields['tags'].initial = list(obj.tags)
            for key, value in self.fields.items():
                if value.initial is None:
                    value.initial = getattr(obj, key)


class ProgramForm(SystemObjectForm):
    priority = forms.FloatField()

    def load(self, programname):
        if programname:
            prog = self.system.namespace[programname]

            for key in prog.callables + ['triggers', 'exclude_triggers']:
                cll = getattr(prog, key)
                if isinstance(cll, AbstractCallable):
                    val = cll.give_str_indented()
                elif isinstance(cll, set):
                    val = repr(set(cll))

                self.fields[key] = forms.CharField(initial=val, required=False,
                                                   widget=forms.Textarea(attrs=dict(rows=val.count('\n') + 1)))
        super(ProgramForm, self).load(programname)

    def clean(self):
        from automate.common import LogicStr

        obj = getattr(self, 'obj', None)
        if obj:
            for key in obj.callables + ['triggers', 'exclude_triggers']:
                if key in self.changed_data:
                    try:
                        LogicStr().validate(list(self.system.programs)[0], None, self.cleaned_data[key])
                    except TraitError:
                        self.add_error(key, 'Invalid value')

        return super(ProgramForm, self).clean()

    def new(self, progname):
        prog = Program(self.cleaned_data.pop('name'))
        prog.setup_system(self.system)
        return prog

    def save(self, progname=None):
        prog = self.get_object(progname)

        for key in prog.callables + ['triggers', 'exlude_triggers']:
            if key in self.changed_data:
                setattr(prog, key + '_str', self.cleaned_data.pop(key))

        super(ProgramForm, self).save(prog.name)


class StatusObjectForm(ProgramForm):
    safety_delay = forms.FloatField()
    safety_mode = forms.ChoiceField(choices=[(i, i) for i in ['rising', 'falling', 'both']])
    change_delay = forms.FloatField()
    change_mode = forms.ChoiceField(choices=[(i, i) for i in ['rising', 'falling', 'both']])

    def load(self, objname=None):
        if objname is None:
            # Object type field for new objects
            self.fields['object_type'] = forms.ChoiceField(choices=[(i, i) for i in self.types])
        else:
            obj = self.get_object(objname)
            for attr_name in obj.view:
                if attr_name not in self.fields:
                    init_value = getattr(obj, attr_name)
                    value_type = type(init_value)
                    self.fields[attr_name] = fieldtypes.get(
                        value_type, forms.CharField)(initial=init_value, required=False)
        super(StatusObjectForm, self).load(objname)

    def new(self, name):
        type = self.cleaned_data.pop('object_type')
        Type = getattr(self.module, type)
        obj = Type(self.cleaned_data.pop('name'))
        obj.setup_system(self.system)
        return obj

    @property
    def abstract_class(self):
        raise NotImplementedError

    @property
    def module(self):
        raise NotImplementedError

    @property
    def types(self):
        return sorted([key for key, value in self.module.__dict__.items()
                       if isinstance(value, type) and issubclass(value, self.abstract_class) and not key.startswith('Abstract')])


class SensorForm(StatusObjectForm):

    @property
    def abstract_class(self):
        from automate.statusobject import AbstractSensor
        return AbstractSensor

    @property
    def module(self):
        import automate.sensors
        return automate.sensors


class ActuatorForm(StatusObjectForm):

    @property
    def abstract_class(self):
        from automate.statusobject import AbstractActuator
        return AbstractActuator

    @property
    def module(self):
        import automate.actuators
        return automate.actuators

FORMTYPES = dict(program=ProgramForm, sensor=SensorForm, actuator=ActuatorForm)
