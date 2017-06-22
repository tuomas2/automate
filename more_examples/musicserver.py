# encoding:utf-8
from __future__ import unicode_literals
from automate import *
from automate.extensions.arduino import ArduinoPWMActuator
from automate.extensions.rpc import RpcService
from automate.extensions.rpio import RpioActuator
from automate.extensions.webui import WebService
from automate.program import Program
#import alsaseq
from traits.api import Bool
import time
import os
import signal
import psutil

import socket
socket.setdefaulttimeout(30) # Do not keep waiting forever for RemoteFuncs

def meminfo():
    return psutil.virtual_memory().percent

#class MidiSensor(AbstractSensor):
#    _status = Bool(False)
#
#    def setup(self):
#        alsaseq.client('Recorder', 1, 0, True)
#        alsaseq.connectfrom(0, 20, 0)
#        alsaseq.start()
#        thread_start(self.midiloop)
#
#    def midiloop(self):
#        lastchange = 0
#        while 1:
#            time.sleep(1)
#            if alsaseq.inputpending():
#                event = alsaseq.input()
#                if event[0] in [36, 42]:
#                    if time.time() - lastchange > 10:
#                        self.status = False
#                    continue
#                if event[0] == 67:
#                    self.status = False
#                    return
#                self.status = True
#                lastchange = time.time()


# TODO: puhesyntetisaattori
def is_raspi():
    """Only in my raspi1,2 computers enable GPIO"""
    import platform
    return platform.node() in ["raspi1", "raspi2"]

def lirc_filter(line):
    code, num, key, remote = line.split(' ')
    return key

class IsRaspi(SystemObject):

    def call(self, caller, **kwargs):
        return is_raspi()

raspi1host = 'http://raspi1:3030/' if is_raspi() else 'http://localhost:3030/'
basetime = 5 if is_raspi() else 100


class MusicServer(System):
    #    class Test(Group):
    #        tstint = UserIntSensor()
    #        tstfloat = UserFloatSensor()
    #        tststr = UserStrSensor()
    #        tstbool = UserBoolSensor()

    normal_volume = UserIntSensor(
        default=0,
        value_min=-50,
        value_max=0
    )
    piano_volume = UserIntSensor(
        default=0,
        value_min=-50,
        value_max=0,
    )

    israspi = IsRaspi()
    email_sender = EmailSender(to_email=os.getenv('AUTOMATE_EMAIL', 'test@test.com'),
                               smtp_hostname=os.getenv('AUTOMATE_SMTP_HOSTNAME'),
                               smtp_username=os.getenv('AUTOMATE_EMAIL'),
                               smtp_password=os.getenv('AUTOMATE_SMTP_PASSWORD'),
                               smtp_fromemail=os.getenv('AUTOMATE_EMAIL'),
                               smtp_fromname="Automate",
                               )

    raspi1_alive = PollingSensor(
        interval=10 * basetime,
        status_updater=RemoteFunc(raspi1host, 'is_alive'),
        active_condition=Value('raspi1_alive'),
        on_deactivate=If(israspi, email_sender),
    )

    class UrlPlay(Group):
        reset_mplayer = Run(
                            If(Not('out_actual'),
                               SetStatus('launchtime', 1),
                               WaitUntil('soundcard_ready',
                                   Shell('mplayer click.mp3'),  # initialize sound (soft mixer does not work untill this is done)
                                   SetStatus('volume', IfElse('piano_on', 'piano_volume', 'normal_volume'), force=True),
                                   SetStatus('launchtime', 0),
                               ),
                            ),
                            Shell('mpc pause'),
                            If('mplayer_pid',
                                Func(os.kill, 'mplayer_pid', signal.SIGTERM),
                                SetStatus('mplayer_pid', 0)
                               )
                            )

        mplayer_pid = UserIntSensor(user_editable=False)

        mplayer_alive = PollingSensor(
            interval=basetime,
            #status_updater=Value(IfElse(mplayer_pid, Not(Shell(ToStr('ps {}', mplayer_pid))), 0)),
            status_updater=Value(IfElse(mplayer_pid, Func(os.path.isdir, ToStr('/proc/{}', mplayer_pid)), 0)),
            active_condition=Value('mplayer_alive'),
            on_deactivate=Run('clear'),
        )

        mplayer = UserStrSensor(
            active_condition=Value('mplayer'),
            on_update=If(TriggeredBy('mplayer'),
                         Run(reset_mplayer),
                         WaitUntil(And('soundcard_ready', Not('launchtime')),
                            SetStatus(mplayer_pid,
                                       Shell(ToStr('nohup mplayer -cache 1024 {}', Value('mplayer')), no_wait=True))),
                         )
        )

        youtube = UserStrSensor(
            active_condition=Value('youtube'),
            on_activate=If(TriggeredBy('youtube'),
                            Run(reset_mplayer),
                            WaitUntil(And('soundcard_ready', Not('launchtime')),
                                SetStatus( mplayer_pid, Shell(ToStr('mpsyt playurl "{}"', Value('youtube')), no_wait=True))),
            )
        )

        livestreamer = UserStrSensor(
            active_condition=Value('livestreamer'),
            on_activate=If(TriggeredBy('livestreamer'),
                            reset_mplayer,
                            WaitUntil(And('soundcard_ready', Not('launchtime')),
                                SetStatus(mplayer_pid,
                                      Shell(
                                            ToStr('livestreamer --yes-run-as-root --player mplayer "{}" worst',
                                                  Value('livestreamer')),
                                            no_wait=True))),
                            )
        )

        pause_mplayer = UserBoolSensor(
            active_condition=Value('pause_mplayer'),
            update_condition=Value(mplayer_pid),
            on_activate=If(mplayer_pid,
                           Func(os.kill, 'mplayer_pid', signal.SIGSTOP)),
            on_deactivate=If(mplayer_pid,
                             Func(os.kill, 'mplayer_pid', signal.SIGCONT)),
        )

        # clear = UserEventSensor(
        #    on_activate=
        clear = SetStatus([mplayer, youtube, livestreamer], [''] * 3)
        #)

    class Commands(Group):
        tags = 'web'
        reload_arduino = UserEventSensor(
            on_activate=ReloadService('ArduinoService'),
        )
        reload_web = UserEventSensor(
            on_activate=ReloadService('WebService'),
        )

        radiodei = UserEventSensor(tags={'quick_music'},
            on_activate=SetStatus('mplayer', 'mms://mms.radiodei.fi/RadioDeiR2HF')
        )

        radiopatmos = UserEventSensor(tags={'quick_music'},
            on_activate=SetStatus('mplayer', 'http://46.163.245.15:8000/radio')
        )

        start = UserBoolSensor(tags={'quick_music'},
            active_condition=Value('start'),
            on_activate=Run('reset_mplayer',
                            WaitUntil(And('soundcard_ready', Not('launchtime')),
                                      Shell('mpc play'),
                                      SetStatus('start', 0))
                           )
        )

        stop = UserEventSensor(tags={'quick_music'},
            on_activate=Run('reset_mplayer', 'clear'),
        )

        restart_mpd = UserEventSensor(
            on_activate=Shell('service mpd restart'),
        )

        prev = UserEventSensor(
            on_activate=Shell('mpc prev'),
        )

        next = UserEventSensor(
            on_activate=Shell('mpc next'),
        )

        #volumesensor = PollingSensor(
        #    interval=basetime,
        #    status_updater=RegexSearch(r'Front Left: (\d*)', Shell('amixer sget Master 2>/dev/null', output=True)),
        #    #on_update=SetStatus('volume', 'volumesensor'),
        #)

        read_volume = UserEventSensor(
            on_activate=Run(
                SetStatus('volume', Func(float, RegexSearch(r'\[([-\.\d]+)dB\]', Shell('amixer sget Master 2>/dev/null', output=True)))),
                SetStatus('volume_piano_only', Func(float, RegexSearch(r'\[([-\.\d]+)dB\]', Shell('amixer sget "Matrix 03 Mix A" 2>/dev/null', output=True)))),
                SetStatus('volume_pcm_only', Func(float, RegexSearch(r'\[([-\.\d]+)dB\]', Shell('amixer sget "Matrix 01 Mix A" 2>/dev/null', output=True)))),
                ),
            tags = 'quick_music',
        )

        volume = UserIntSensor(tags={'quick_music'},
            default=0,
            value_min=-50,
            value_max=0,
            on_update=Shell(ToStr('amixer -- sset "Master" {}dB', Value('volume')))
        )

        volume_piano_only = UserIntSensor(tags={'quick_music'},
            default=0,
            value_min=-50,
            value_max=0,
            on_update=Run(
                    Shell(ToStr('amixer -- sset "Matrix 03 Mix A" {}dB', Value('volume_piano_only'))),
                    Shell(ToStr('amixer -- sset "Matrix 04 Mix B" {}dB', Value('volume_piano_only'))),
            )
        )

        volume_pcm_only = UserIntSensor(tags={'quick_music'},
            default=-12,
            value_min=-50,
            value_max=0,
            on_update=Run(
                    Shell(ToStr('amixer -- sset "Matrix 01 Mix A" {}dB', Value('volume_pcm_only'))),
                    Shell(ToStr('amixer -- sset "Matrix 02 Mix B" {}dB', Value('volume_pcm_only'))),
            )
        )

        current = PollingSensor(
            interval=basetime,
            status_updater=Shell('mpc current', output=True),
        )

        reset = UserBoolSensor(
            priority=50.,
            active_condition=Value('reset'),
            on_activate=Threaded(Shell('mpc pause'),
                                 SetStatus('out_actual', 0),
                                 WaitUntil(Not('out_hardware'),
                                     SetStatus('reset', 0),
                                     SetStatus('start', 1),
                                    )
                                 )
        )

        manual_mode = UserBoolSensor(tags={'quick_music'},
            default=True,
            #active_condition=Value('manual_mode'),
            #on_activate=SetStatus('out_buffer', 1),
        )

    moc_alive = UserBoolSensor(default=False)
    #class Moc(Group):
    #    moc_alive = PollingSensor(
    #        type=bool,
    #        interval=basetime,
    #        status_updater=RegexMatch(r'^State: PLAY$', Shell('mocp -i', output=True)),
    #        active_condition=Value('moc_alive'),
    #        on_deactivate=SetStatus('moc_play', ''),
    #    )

    #    moc_toggle_pause = UserEventSensor(
    #        on_activate=Shell('mocp --toggle-pause')
    #    )

    #    moc_play = UserStrSensor(
    #        active_condition=Value('moc_play'),
    #        on_update=Shell(ToStr('mocp --playit {}', 'moc_play'))
    #    )

    class In(Group):
        lirc_sensor = ShellSensor(cmd='irw', filter=lirc_filter, default='', reset_delay=0.3,
            active_condition=Value('lirc_sensor'),
            on_update=Switch('lirc_sensor',
                    {'KEY_GREEN': SetStatus('start', 1),
                     'KEY_YELLOW': SetStatus('radiodei', 1),
                     'KEY_BLUE': SetStatus('radiopatmos', 1),
                     'KEY_RED': SetStatus('stop', 1),
                     'KEY_7': SetStatus('preset1', 1),
                     'KEY_8': SetStatus('preset2', 1),
                     'KEY_9': SetStatus('preset3', 1),
                     'KEY_VOLUMEUP': SetStatus('volume', Value('volume')+1),
                     'KEY_VOLUMEDOWN': SetStatus('volume', Value('volume')-1),
                     'KEY_0': SetStatus('switch_off', 1),
                     'KEY_SHUFFLE': SetStatus('fade_out', 1),
                     'F_POWER': Shell('reboot'),
                    }
                ),
        )

        soundcard_ready = PollingSensor(
            interval=basetime,
            status_updater=Shell('aplay -l 2>/dev/null | grep "18i6"', output=True),
            active_condition=Value('soundcard_ready'),
            on_activate=Run(
                SetStatus('volume', 'volume', force=True),
                SetStatus('volume_piano_only', 'volume_piano_only', force=True),
                SetStatus('volume_pcm_only', 'volume_pcm_only', force=True),
            )
        )
#        def filter(line):
#            start_str = 'Product: Scarlett 18i6 USB'
#            stop_str = '
#            pass
#
#        soundcard_ready = ShellSensor(cmd='tail -f /var/log/syslog', filter=filter, simple=True)

        playback_active = PollingSensor(
            interval=basetime,
            status_updater=Or('mplayer_alive', 'moc_alive', Not(Shell('mpc | grep playing'))),
        )

        #set_piano_volume = Program(
        #    active_condition=And('piano_on', 'soundcard_ready'),
        #    on_activate=SetStatus('volume', 'piano_volume'),
        #    on_deactivate=SetStatus('volume', 'normal_volume')
        #)

        piano_on = PollingSensor(
            #active_condition = Value('piano_on'),
            #on_activate=SetStatus('out_buffer', 1),
            interval = basetime,
            status_updater=Not(Shell('aplaymidi -l | grep RD')),
        )
        #midi = MidiSensor()
        #fsc = FileChangeSensor(filename='/home/tuma/nauhoituksia/', silent=True)
        # playback_active = SocketSensor(
        #    port=9192,
        #)

    class Lamps(Group):
        warm_lamp_out = ArduinoPWMActuator(dev=0, pin=9, default=0.)
        cold_lamp_out = ArduinoPWMActuator(dev=0, pin=10, default=0.)

        warm_preset1 = UserFloatSensor(value_min=0., value_max=1., default=0.5)
        cold_preset1 = UserFloatSensor(value_min=0., value_max=1., default=1.)

        warm_preset2 = UserFloatSensor(value_min=0., value_max=1., default=1.)
        cold_preset2 = UserFloatSensor(value_min=0., value_max=1., default=0.)

        warm_preset3 = UserFloatSensor(value_min=0., value_max=1., default=.1)
        cold_preset3 = UserFloatSensor(value_min=0., value_max=1., default=0.)

        preset1 = UserBoolSensor(tags={'quick_lamps'},
                                 priority=2.,
                                 active_condition=Value('preset1'),
                                 on_update=Run(SetStatus('warm_lamp_out', 'warm_preset1'),
                                               SetStatus('cold_lamp_out', 'cold_preset1'),
                                               SetStatus('preset2', 0),
                                               SetStatus('preset3', 0),
                                               ))

        preset2 = UserBoolSensor(tags={'quick_lamps'}, priority=2.,
                                 active_condition=Value('preset2'),
                                 on_update=Run(SetStatus('warm_lamp_out', 'warm_preset2'),
                                               SetStatus('cold_lamp_out', 'cold_preset2'),
                                               SetStatus('preset1', 0),
                                               SetStatus('preset3', 0),
                                               ))

        preset3 = UserBoolSensor(tags={'quick_lamps'}, priority=2.,
                                 active_condition=Value('preset3'),
                                 on_update=Run(SetStatus('warm_lamp_out', 'warm_preset3'),
                                               SetStatus('cold_lamp_out', 'cold_preset3'),
                                               SetStatus('preset1', 0),
                                               SetStatus('preset2', 0),
                                                ))

        switch_off = UserEventSensor(tags={'quick_lamps'}, on_activate=SetStatus(['fade_out', 'preset1', 'preset2', 'preset3'], [0]*4))

        fd_mpl = UserFloatSensor(description='multiplier', default=0.999, value_min=0.9, value_max=1.0)
        fd_thr = UserFloatSensor(description='threshold', default=0.001, value_min=0.0001, value_max=0.01)
        fd_slp = UserFloatSensor(description='sleep time', default=0.1, value_min=0.00, value_max=1.)

        dimmer = While(
                        Or(
                            Value('cold_lamp_out'),
                            Value('warm_lamp_out'),
                        ),
                        SetStatus('cold_lamp_out', IfElse(Value('cold_lamp_out') > Value(fd_thr),
                                                          Value('cold_lamp_out')*Value(fd_mpl), 0)),
                        SetStatus('warm_lamp_out', IfElse(Value('warm_lamp_out') > Value(fd_thr),
                                                          Value('warm_lamp_out')*Value(fd_mpl), 0)),
                        Func(time.sleep, 'fd_slp'),
                        do_after=Run(SetStatus(['preset1', 'preset2', 'preset3', 'fade_out', 'akvadimmer'], [0]*5))
                      )

        fade_out = UserBoolSensor(tags={'quick_lamps'}, priority=3,
                                     active_condition=Value('fade_out'),
                                     on_activate=Run('dimmer')
                                 )

        warm_preset_akva = UserFloatSensor(value_min=0., value_max=1., default=1, user_editable=False)
        cold_preset_akva = UserFloatSensor(value_min=0., value_max=1., default=0.5, user_editable=False)

        akvadimmer = UserBoolSensor(priority=1., # lower priority light for aquarium (raspi1) remote use only
                                 active_condition=Value('akvadimmer'),
                                 on_activate=IfElse(
                                                # if lamp already on, do not activate this function at all
                                                Or('warm_lamp_out', 'cold_lamp_out'),
                                                SetStatus('akvadimmer', 0),
                                                Run(SetStatus('warm_lamp_out', 'warm_preset_akva'),
                                                    SetStatus('cold_lamp_out', 'cold_preset_akva'),
                                                    Run('dimmer'),
                                                    )
                                                ))

    class SystemInfo(Group):
        load_average = PollingSensor(interval=10, status_updater=ToStr('{}', Func(os.getloadavg)))
        memory = PollingSensor(interval=10, status_updater=ToStr(Func(meminfo)))

    class Out(Group):
        launchtime = UserBoolSensor() #at launchtime, this is used to set out_buffer to 1, before playback can start
        gmediarender_pid = UserIntSensor(default=0, user_editable=False)

        out_hardware = RpioActuator(port=17, slave=True)
        out_actual = BoolActuator(active_condition=Value('out_actual'),
                                  on_activate=Run(SetStatus(out_hardware, 1),
                                                  SetStatus('gmediarender_pid', Shell('gmediarender -f raspi2', no_wait=True))),
                                  on_deactivate=Run(
                                                   If('gmediarender_pid',
                                                     Run(Func(os.kill, gmediarender_pid, signal.SIGTERM),
                                                       SetStatus('gmediarender_pid', 0))),
                                                   Shell('amixer sset Master mute'),
                                                   SetStatus('out_hardware', 0))
        )

        out_buf_prog = Program(
            on_update=SetStatus('out_buffer', Or('launchtime', 'playback_active', 'piano_on', 'manual_mode'))
        )

        out_buffer = BoolActuator(
            safety_mode='both',
            change_delay=900.0,
            change_mode='falling',
            on_update=SetStatus(out_actual, 'out_buffer'),
        )

        #after_reset = Program(
        #    update_condition=Value('out_buffer'),
        #    on_update=If(Not(Or('manual_mode', 'piano_on')), Delay(5, Shell('mpc play'))),
        #    exclude_triggers=['manual_mode', 'piano_on']
        #)

import tornado.log
tornado.log.access_log.setLevel(logging.WARNING)

if __name__ == '__main__':
    s = MusicServer.load_or_create('musicserver.dmp',
                                   services=[
                                       WebService(
                                           http_port=8080 if is_raspi() else 8082,
                                           http_auth=(
                                               (os.getenv('AUTOMATE_USERNAME', 'test'), os.getenv('AUTOMATE_PASSWORD', 'test')),
                                           ),
                                           debug=False if is_raspi() else True,
                                           user_tags={'web'}, default_view='user_editable_view',
                                           read_only=False,
                                           show_actuator_details=False,
                                           django_settings = {'SESSION_FILE_PATH': 'sessions' if is_raspi() else '/tmp',
                                                              'SESSION_COOKIE_AGE': 52560000,
                                                              'SECRET_KEY': os.getenv('AUTOMATE_SECRET_KEY', 'unsecure-default')},
                                           #read_only = True,
                                       ),
                                       StatusSaverService(),
                                       RpcService(http_port=3031, view_tags={'web'}),
                                   ],
                                   logfile='music_server.log' if is_raspi() else '',
                                   print_level=logging.INFO,
                                   log_level=logging.WARNING,
                                   )
