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

from __future__ import unicode_literals
import platform
from threading import Thread

from traits.api import CUnicode, Unicode, CInt
import requests

from automate.common import threaded
from automate.systemobject import SystemObject


class PushOver(SystemObject):
    """
        Send push notifications to android/IOS phones (see http://pushover.net).

        Use this as you would use a Callable.
    """

    #: Pushover.net application/API token
    api_key = CUnicode
    #: Pushover.net user key
    user_key = CUnicode
    #: Pushover.net priority
    priority = CInt(0)
    #: Device name (empty to send to all devices)
    device = CUnicode
    #: Sound name in device
    sound = CUnicode

    def send(self, caller):
        try:
            url = self.system.services_by_name['WebService'][0].server_url
        except KeyError:
            url = ''

        data=dict(
            token=self.api_key,
            user=self.user_key,
            message='Automate event triggered on %s' % platform.node(),
            title=caller.name,
            url=url,
            url_title=self.system.name + ' web interface')

        if self.device:
            data['device'] = self.device
        if self.sound:
            data['sound'] = self.sound

        requests.post('https://api.pushover.net/1/messages.json', data=data)

    def call(self, caller, **kwargs):
        t = Thread(target=threaded(self.send, caller), name='Notification sender thread')
        t.start()


class EmailSender(SystemObject):

    """ Send email notification of the current status of the system """

    # Email address where mail is sent
    to_email = CUnicode
    smtp_hostname = Unicode
    smtp_username = Unicode
    smtp_password = Unicode
    smtp_fromname = Unicode
    smtp_fromemail = Unicode

    def get_status_display(self):
        return self.to_email

    def call(self, caller, **kwargs):
        t = Thread(target=threaded(self.send, caller), name='Email sender thread')
        t.start()

    def send(self, caller):
        self.logger.info("Sending email now")

        progname = self.system.name

        hostname = platform.node()
        subject = u'Program {progname} at {host} encountered event of "{evname}"! '.format(
            host=hostname, progname=progname, evname=caller.name)

        headers = (u"Subject: {subject}\n"
                   "From: {fromaddr}\n"
                   "To: {to}\n"
                   "Content-type: text/plain; charset=UTF-8\n").format(subject=subject,
                                                                       fromaddr=self.smtp_fromemail,
                                                                       to=self.to_email)

        sensorstatuses = '\n'.join('%s: %s' % (i.name, i.status) for i in self.system.sensors)
        actuatorstatuses = '\n'.join('%s: %s' % (i.name, i.status) for i in self.system.actuators)

        logserv = self.system.request_service('LogStoreService')
        message = (u'{headers}\n'
                   'Program {progname} encountered event of "{evname}"!\n\n'
                   'Sensors\n\n'
                   '{sensorstatuses}\n\n'
                   'Actuators\n\n'
                   '{actuatorstatuses}\n\n'
                   'Log\n\n{log}').format(progname=progname,
                                          evname=caller.name,
                                          headers=headers,
                                          sensorstatuses=sensorstatuses,
                                          actuatorstatuses=actuatorstatuses,
                                          log=logserv.lastlog(html=False))
        message = message

        import smtplib

        smtp = smtplib.SMTP_SSL(self.smtp_hostname)
        smtp.login(self.smtp_username, self.smtp_password)
        smtp.sendmail(self.smtp_fromemail, self.to_email, message)


class PlantUMLGenerator(SystemObject):

    def call(self, caller=None):
        s = self.system.request_service('PlantUMLService')
        return s.write_puml()
