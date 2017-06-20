from __future__ import unicode_literals
from builtins import input
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

from automate.common import ExitException
from automate.service import AbstractUserService

helpstr = """
 Automate interactive Python shell
 ==================================

 This interactive shell is intended for making small changes to
 working model.

 Any Python commands are accepted. You may refer to all your
 automate objects by their name attribute. You may do anything to
 modify the state on fly by this field, for example, create new programs,
 actuators, sensors, etc. Some practical commands:

  help -- show this help message (or with parameter, normal pydoc)
  lsa, lsp, lss -- list actuators, programs, sensors
  get_statusmsg -- print current system status
  gui -- show GUI
  quit -- quit cleanly

  python_str(filename) -- print all objects in a python file
  obj.set_value(value) -- set object value for obj
  obj.print_traits() -- print all traits attributes for obj

"""

prompt = "> "


class TextUIService(AbstractUserService):

    """
        Provides interactive Python shell frontend to the System.
        Uses IPython if it is installed.
        Provides couple of functions to the System namespace.
    """
    autoload = True

    def setup(self):
        self.system.register_service_functions(
            self.ls, self.lsa, self.lsp, self.lss, self.help, self.text_ui, self.quit)
        self.system.on_trait_change(self.text_ui, 'post_init_trigger')

    def ls(self, what):
        """List actuators, programs or sensors (what is string)"""
        for i in getattr(self.system, what):
            self.logger.info('%s: %s: %s', i.__class__.__name__, i, i.status)
        return True

    def lsa(self):
        """List actuators"""
        return self.ls("actuators")

    def lsp(self):
        """List programs"""
        return self.ls("programs")

    def lss(self):
        """List sensors"""
        return self.ls("sensors")

    def help(self, *args, **kwargs):
        """Print Automate help if no parameter is given. Otherwise,
           act as pydoc.help()"""
        if len(args) > 0 or len(kwargs) > 0:
            import pydoc

            pydoc.help(*args, **kwargs)
        else:
            hstr = helpstr
            for i in hstr.split("\n"):
                self.logger.info(i)
        return True

    def text_ui(self):
        """
            Start Text UI main loop
        """
        self.logger.info("Starting command line interface")
        self.help()
        try:
            self.ipython_ui()
        except ImportError:
            self.fallback_ui()
        self.system.cleanup()

    def ipython_ui(self):
        from IPython.terminal.ipapp import TerminalIPythonApp
        import automate
        self.system.namespace.allow_overwrite.extend(['_', '__', '___', '_i', '_ii', '_iii', 'quit'])
        self.system.namespace.update({k: v for k, v in list(automate.__dict__.items()) if k not in self.system.namespace})
        term = TerminalIPythonApp(user_ns=self.system.namespace)
        self.system.namespace['term'] = term
        term.initialize()
        term.start()

    def fallback_ui(self):
        # If IPython is not installed, this fallback is used
        try:
            while True:
                try:
                    import readline
                    import rlcompleter

                    rlcompleter.Completer._callable_postfix = lambda self, val, word: word
                    readline.set_completer(rlcompleter.Completer(self.system.cmd_namespace).complete)
                    readline.parse_and_bind("tab: complete")
                except ImportError:
                    self.logger.warning(
                        "Readline support disabled. Please install readline and rlcompleter if you want to use.")
                try:
                    c = eval(input(prompt))
                except EOFError:
                    return
                if c[:1] == "%":
                    c = c[1:]
                else:
                    cmd = c.strip()
                    self.system.cmd_exec(cmd)

        except (KeyboardInterrupt, ExitException):
            return

    def quit(self):
        raise ExitException
