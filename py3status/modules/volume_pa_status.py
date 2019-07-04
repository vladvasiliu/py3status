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

from pulsectl import Pulse, PulseEventMaskEnum, PulseEventTypeEnum, PulseEventFacilityEnum, PulseSinkInfo, PulseDisconnected

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
        self._sink: Optional[PulseSinkInfo] = None
        self._sink_name = sink_name
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

    def _get_default_sink(self):
        default_sink_name = self._pulse_connector.server_info().default_sink_name
        if self._sink_name != default_sink_name:
            self._sink_name = default_sink_name
            self._sink = self._pulse_connector.get_sink_by_name(self._sink_name)
            self._get_volume()

    def _get_volume(self):
        pulse_volume = self._pulse_connector.volume_get_all_chans(self._sink)
        if self._volume != pulse_volume:
            self._volume = pulse_volume
            self._event.set()

    def _callback(self, ev):
        if not ev.t == PulseEventTypeEnum.change:
            return

        if ev.facility == PulseEventFacilityEnum.server:
            self._command_queue.put(partial(self._get_default_sink))
        elif ev.facility == PulseEventFacilityEnum.sink and ev.index == self._sink.index:
            self._command_queue.put(partial(self._get_volume))

    def _stop_writer(self):
        raise StopController

    def _pulse_writer(self):
        while True:
            logger.debug("waiting for commands...")
            command = self._command_queue.get()

            logger.debug(f"Got command {command}")

            logger.debug(f"Stopping pulse event loop...")
            self._pulse_connector.event_listen_stop()
            try:
                command()
            except StopController:
                logger.debug("Stopping writer.")
                break
            else:
                self._pulse_connector_lock.release()

    def _pulse_reader(self):
        while True:
            self._pulse_connector_lock.acquire()
            logger.debug("starting reader")
            try:
                self._pulse_connector.event_listen()
            except PulseDisconnected:
                logger.debug("Pulse disconnected. Stopping reader.")
                self._command_queue.put(partial(self._stop_writer))
                break

    def post_config_hook(self):
        self._pulse_connector.connect()
        self._get_default_sink()
        self._get_volume()
        self._pulse_connector.event_mask_set(PulseEventMaskEnum.server, PulseEventMaskEnum.sink)
        self._pulse_connector.event_callback_set(self._callback)
        self._reader_thread = threading.Thread(name="pulse_reader", target=self._pulse_reader)
        self._writer_thread = threading.Thread(name="pulse_writer", target=self._pulse_writer)
        self._reader_thread.start()
        self._writer_thread.start()

    def kill(self):
        logger.info("Shutting down")
        self._pulse_connector.event_listen_stop()
        self._pulse_connector.disconnect()

    def volume_status(self):
        response = {
            "cached_until": self.py3.CACHE_FOREVER,
            "color": "blue",
            "full_text": f"Vol: 100%",
        }
        return response



# class Py3status:
#     """
#     """
#
#     # available configuration parameters
#     py3: Py3
#     button_down = 5
#     button_mute = 1
#     button_up = 4
#     volume_delta = 5
#     max_volume = 100
#
#     def __init__(self):
#         self._volume = None
#         self._mute = None
#         self._pulse_reader = Pulse('volume-reader')
#         self._pulse_event_handler = None
#         self._default_sink = None
#
#     def _pulse_callback(self, ev):
#         raise PulseLoopStop
#
#
#
#     def _formatted_volume(self):
#         return round(self._volume * 100)
#
#     # return the format string formatted with available variables
#     def _format_output(self, format, icon, percentage):
#         text = self.py3.safe_format(format, {"icon": icon, "percentage": percentage})
#         return text
#
#     def volume_status(self):
#
#         # create response dict
#         response = {
#             "cached_until": self.py3.CACHE_FOREVER,
#             "color": "blue",
#             "full_text": f"Vol: {self._formatted_volume()}",
#         }
#         return response
#
#     # def on_click(self, event):
#     #     """
#     #     Volume up/down and toggle mute.
#     #     """
#     #     button = event["button"]
#     #     # volume up
#     #     if button == self.button_up:
#     #         try:
#     #             self.backend.volume_up(self.volume_delta)
#     #         except TypeError:
#     #             pass
#     #     # volume down
#     #     elif button == self.button_down:
#     #         self.backend.volume_down(self.volume_delta)
#     #     # toggle mute
#     #     elif button == self.button_mute:
#     #         self.backend.toggle_mute()


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
