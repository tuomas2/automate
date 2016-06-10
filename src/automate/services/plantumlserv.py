from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
# -*- coding: utf-8 -*-
# (c) 2015 Tuomas Airaksinen
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
#
# ------------------------------------------------------------------
#
# If you like Automate, please take a look at this page:
# http://evankelista.net/automate/

import io

from traits.api import Str, Dict

from automate.service import AbstractUserService
from automate.program import DefaultProgram, ProgrammableSystemObject
from automate.statusobject import AbstractActuator, AbstractSensor


class PlantUMLService(AbstractUserService):

    """
        Provides UML diagrams of the system as SVG images. Used by WebService.

        PLantUMLService requires either PlantUML software (which is opensource software written in Java) to be
        installed locally (see http://plantuml.sourceforge.net/) or it is possible to use online service of plantuml.com
        In addition you need python package :mod:`plantuml` (available via PYPI).
    """

    #: URL of PlantUML Java Service. To use PlantUML online service, set this to 'http://www.plantuml.com/plantuml/svg/'
    url = Str()

    #: Arrow colors as HTML codes stored as a dictionary with keys:
    #: controlled_target, active_target, inactive_target, trigger
    arrow_colors = Dict(
        dict(controlled_target='#FF0000', active_target='#0000FF', inactive_target='#4C4C4C', trigger='#009933'))

    #: Background colors as HTML codes, stored as a dictionary with keys: program, actuator, sensor
    background_colors = Dict(dict(program='#FFFFCC', actuator='#FFCCFF', sensor='#CCFFCC'))

    def write_puml(self, filename=''):
        """
            Writes PUML from the system. If filename is given, stores result in the file.
            Otherwise returns result as a string.
        """
        def get_type(o):
            type = 'program'
            if isinstance(o, AbstractSensor):
                type = 'sensor'
            elif isinstance(o, AbstractActuator):
                type = 'actuator'
            return type

        if filename:
            s = open(filename, 'w')
        else:
            s = io.StringIO()
        s.write('@startuml\n')
        s.write('skinparam state {\n')
        for k, v in list(self.background_colors.items()):
            s.write('BackGroundColor<<%s>> %s\n' % (k, v))
        s.write('}\n')

        for o in self.system.objects:
            if isinstance(o, DefaultProgram) or o.hide_in_uml:
                continue

            if isinstance(o, ProgrammableSystemObject):
                s.write('state "%s" as %s <<%s>>\n' % (o, o, get_type(o)))

                s.write('%s: %s\n' % (o, o.class_name))
                if isinstance(o, AbstractActuator):
                    for p in reversed(o.program_stack):
                        s.write('%s: %s :: %s\n' % (o, p, o.program_status.get(p, '-')))
                elif hasattr(o, 'status'):
                    s.write('%s: Status: %s\n' % (o, o.status))
                if getattr(o, 'is_program', False):
                    s.write('%s: Priority: %s\n' % (o, o.priority))

                for t in o.actual_triggers:
                    if isinstance(t, DefaultProgram) or t.hide_in_uml:
                        continue
                    s.write('%s -[%s]-> %s\n' % (t, self.arrow_colors['trigger'], o))
                for t in o.actual_targets:
                    if t.hide_in_uml:
                        continue
                    if o.active:
                        color = 'active_target'
                    else:
                        color = 'inactive_target'
                    if getattr(t, 'program', None) == o:
                        color = 'controlled_target'

                    s.write('%s -[%s]-> %s\n' % (o, self.arrow_colors[color], t))
        s.write('@enduml\n')
        if filename:
            s.close()
        else:
            return s.getvalue()

    def write_svg(self):
        """
            Returns PUML from the system as a SVG image. Requires plantuml library.
        """
        import plantuml
        puml = self.write_puml()
        server = plantuml.PlantUML(url=self.url)
        svg = server.processes(puml)
        return svg
