# -*- coding: utf-8 -*-
"""
Pulse Audio Volume control.

@author <Vlad Vasiliu> <vladvasiliu@yahoo.fr>
@license BSD
"""

from datetime import datetime

import threading

from pulsectl import Pulse, PulseLoopStop, PulseEventTypeEnum

from py3status.py3 import Py3


class Py3status:
    """
    """

    # available configuration parameters
    py3: Py3

    def __init__(self):
        self._volume = None
        self._mute = None
        self._pulse_reader = Pulse('volume-reader')

    def _pulse_callback(self, ev):
        raise PulseLoopStop

    def _set_volume_from_pulse(self):
        # We're getting the first sink each time to make sure we're getting the default one
        sink = self._pulse_reader.sink_list()[0]
        self._volume = sink.volume.value_flat

    def _volume_follower(self):
        self._pulse_reader.event_mask_set('all')
        self._pulse_reader.event_callback_set(self._pulse_callback)
        while True:
            self._pulse_reader.event_listen()
            self._set_volume_from_pulse()
            self.py3.update()

    def post_config_hook(self):
        self._pulse_reader.connect()
        self._set_volume_from_pulse()
        threading.Thread(target=self._volume_follower, daemon=True).start()

    def _formatted_volume(self):
        return round(self._volume * 100)

    # return the format string formatted with available variables
    def _format_output(self, format, icon, percentage):
        text = self.py3.safe_format(format, {"icon": icon, "percentage": percentage})
        return text

    def volume_status(self):

        # create response dict
        response = {
            "cached_until": self.py3.CACHE_FOREVER,
            "color": "blue",
            "full_text": f"Vol: {self._formatted_volume()}",
        }
        return response


if __name__ == "__main__":
    """
    Run module in test mode.
    """
    from py3status.module_test import module_test

    module_test(Py3status)
