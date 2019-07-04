# -*- coding: utf-8 -*-
"""
Pulse Audio Volume control.

@author <Vlad Vasiliu> <vladvasiliu@yahoo.fr>
@license BSD
"""

from functools import partial
import logging
from queue import Queue
import threading
from typing import Optional

from pulsectl import Pulse, PulseEventMaskEnum, PulseEventTypeEnum, PulseEventFacilityEnum, PulseSinkInfo, \
    PulseDisconnected, PulseLoopStop

from py3status.py3 import Py3


logger = logging.getLogger("main")
logging.basicConfig(level=logging.DEBUG)


class StopController(Exception):
    pass


class Py3status:
    _py3: Py3

    def __init__(self, sink_name: Optional[str] = None, volume_boost: bool = False):
        """

        :param sink_name:  Sink name to use. Empty uses default sink
        :param volume_boost: Whether to allow setting volume above 1.0 - uses software boost
        """
        self._sink: Optional[PulseSinkInfo]
        self._volume_boost = volume_boost
        self._pulse_connector = Pulse('py3status-pulse-connector', threading_lock=True)
        self._command_queue = Queue()
        self._event = threading.Event()     # Something has changed in the backend
        self._pulse_connector_lock = threading.Lock()
        self._volume: Optional[float] = None
        self._reader_thread = threading.Thread
        self._writer_thread = threading.Thread

    # @property
    # def volume(self) -> int:
    #     return self._pulse_connector.volume_get_all_chans(self._sink)
    #
    # @volume.setter
    # def volume(self, value):
    #     if not self._volume_boost:
    #         value = max(1.0, value)
    #     self._pulse_connector.volume_set_all_chans(self._sink, value)

    def _get_volume(self):
        sink_name = self._pulse_connector.server_info().default_sink_name
        self._sink = self._pulse_connector.get_sink_by_name(sink_name)
        pulse_volume = self._pulse_connector.volume_get_all_chans(self._sink)
        if self._volume != pulse_volume:
            self._volume = pulse_volume
            self._event.set()

    def _callback(self, ev):
        print(ev)
        if ev.t == PulseEventTypeEnum.change and \
                (ev.facility == PulseEventFacilityEnum.server or
                 ev.facility == PulseEventFacilityEnum.sink and ev.index == self._sink.index):
            raise PulseLoopStop

    def _pulse_reader(self):
        while True:
            try:
                self._pulse_connector.event_listen()
                self._get_volume()
            except PulseDisconnected:
                logger.debug("Pulse disconnected. Stopping reader.")
                break

    def post_config_hook(self):
        self._pulse_connector.connect()
        self._get_volume()
        self._pulse_connector.event_mask_set(PulseEventMaskEnum.server, PulseEventMaskEnum.sink)
        self._pulse_connector.event_callback_set(self._callback)
        self._reader_thread = threading.Thread(name="pulse_reader", target=self._pulse_reader).start()

    def kill(self):
        logger.info("Shutting down")
        self._pulse_connector.disconnect()

    def volume_status(self):
        response = {
            "cached_until": self.py3.CACHE_FOREVER,
            "color": "blue",
            "full_text": f"Vol: {self._volume}%",
        }
        return response


if __name__ == "__main__":
    """
    Run module in test mode.
    """
    # with PulseController() as pc:
    #     pc.run()
    #
    #     while True:
    #         sleep(10)
    from py3status.module_test import module_test

    module_test(Py3status)
