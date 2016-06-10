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

"""
Apply two fixeds to traits 4.5.0 that are necessary in order to Automate to function.
Most likely these are not necessary (neither harmful) any more with 4.6.0.
"""
from __future__ import unicode_literals

import traits.traits_listener as tlistener
original_register = tlistener.ListenerItem.register


def ListenerItem_register(self, new):
    import traits.has_traits as has_traits
    if not isinstance(new, has_traits.HasTraits):
        return tlistener.INVALID_DESTINATION

    return original_register(self, new)
tlistener.ListenerItem.register = ListenerItem_register
import traits.trait_types as ttypes


def CSet_validate(self, object, name, value):
    if not isinstance(value, set):
        try:
            value = set(value)
        except (ValueError, TypeError):
            value = {value}

    return super(ttypes.CSet, self).validate(object, name, value)

ttypes.CSet.validate = CSet_validate

# This hack is necessary in order to silence undesired error messages from Traits notification handler

import traits.trait_notifiers as tnotifier


def _dispatch_change_event(self, object, trait_name, old, new, handler):
    """ Prepare and dispatch a trait change event to a listener. """

    # Extract the arguments needed from the handler.
    args = self.argument_transform(object, trait_name, old, new)

    # Send a description of the event to the change event tracer.
    if tnotifier._pre_change_event_tracer is not None:
        tnotifier._pre_change_event_tracer(object, trait_name, old, new, handler)

    # Dispatch the event to the listener.
    from automate.common import SystemNotReady
    try:
        self.dispatch(handler, *args)
    except SystemNotReady:
        pass
    except Exception as e:
        if tnotifier._post_change_event_tracer is not None:
            tnotifier._post_change_event_tracer(object, trait_name, old, new,
                                                handler, exception=e)
        # This call needs to be made inside the `except` block in case
        # the handler wants to re-raise the exception.
        tnotifier.handle_exception(object, trait_name, old, new)
    else:
        if tnotifier._post_change_event_tracer is not None:
            tnotifier._post_change_event_tracer(object, trait_name, old, new,
                                                handler, exception=None)

tnotifier.TraitChangeNotifyWrapper._dispatch_change_event = _dispatch_change_event
