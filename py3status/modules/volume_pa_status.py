# -*- coding: utf-8 -*-
"""
Pulse Audio Volume control.

@author <Vlad Vasiliu> <vladvasiliu@yahoo.fr>
@license BSD
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
import threading
from typing import Callable, Iterable, Optional, Union

from pulsectl import Pulse, PulseEventMaskEnum, PulseEventTypeEnum, PulseEventFacilityEnum, PulseSinkInfo, \
    PulseDisconnected, PulseLoopStop

from py3status.composite import Composite
from py3status.py3 import Py3


logger = logging.getLogger("main")
logging.basicConfig(level=logging.DEBUG)


@dataclass(frozen=True)
class Volume:
    """Holds normalized (integer) volume and mute status

    The volume will be displayed as an integer. The output will only be updated if the value changes.
    Therefore we do the conversion here so as to avoid "false positives" due to float comparisons.

    As the sink returns a volume level per channel, which is basically a list of values,
    those values must be aggregated into a single value.
    By default `max` is called, but this can be replaced with any function that takes an iterable of floats and returns
    a float.

    Volume is a positive integer:
    * 0: No sound
    * 100: 100% hardware level
    * >100: software amplification
    See PulseAudio documentation for volume levels (https://freedesktop.org/software/pulseaudio/doxygen/volume.html).
    """
    level: int
    mute: bool

    @classmethod
    def from_sink_info(cls, sink_info: PulseSinkInfo, cmp: Callable[[Iterable], float] = max) -> Volume:
        float_vol = cmp(sink_info.volume.values)
        return cls(level=round(100 * float_vol), mute=bool(sink_info.mute))


class Py3status:
    py3: Py3
    blocks = u"_▁▂▃▄▅▆▇█"
    button_down = 5
    button_mute = 1
    button_up = 4
    format = u"{icon} {percentage}%"
    format_muted = u"{icon} {percentage}%"
    is_input = False
    max_volume = 100
    thresholds = [(0, "good"), (75, "degraded"), (100, "bad")]
    volume_delta = 5

    def __init__(self, sink_name: Optional[str] = None, volume_boost: bool = False):
        """

        :param sink_name:  Sink name to use. Empty uses default sink
        :param volume_boost: Whether to allow setting volume above 1.0 - uses software boost
        """
        self._sink_name = sink_name
        self._sink_info: Optional[PulseSinkInfo]
        self._volume_boost = volume_boost
        self._pulse_connector = Pulse('py3status-pulse-connector', threading_lock=True)
        self._pulse_connector_lock = threading.Lock()
        self._volume: Optional[Volume] = None
        self._backend_thread = threading.Thread

    def _get_volume_from_backend(self):
        """Get a new sink on every call.

        The sink is not updated when the backed values change.
        Returned volume is the maximum of all available channels.
        """
        sink_name = self._pulse_connector.server_info().default_sink_name
        self._sink_info = self._pulse_connector.get_sink_by_name(sink_name)
        pulse_volume = Volume.from_sink_info(self._sink_info)
        logger.debug(pulse_volume)
        if self._volume != pulse_volume:
            self._volume = pulse_volume
            self.py3.update()

    def _callback(self, ev):
        if ev.t == PulseEventTypeEnum.change and \
                (ev.facility == PulseEventFacilityEnum.server or
                 ev.facility == PulseEventFacilityEnum.sink and ev.index == self._sink_info.index):
            raise PulseLoopStop

    def _pulse_reader(self):
        while True:
            try:
                self._pulse_connector.event_listen()
                self._get_volume_from_backend()
            except PulseDisconnected:
                logger.debug("Pulse disconnected. Stopping reader.")
                break

    def post_config_hook(self):
        self._pulse_connector.connect()
        self._get_volume_from_backend()
        self._pulse_connector.event_mask_set(PulseEventMaskEnum.server, PulseEventMaskEnum.sink)
        self._pulse_connector.event_callback_set(self._callback)
        self._backend_thread = threading.Thread(name="pulse_backend", target=self._pulse_reader).start()

    def kill(self):
        logger.info("Shutting down")
        self._pulse_connector.disconnect()

    def _color_for_output(self) -> str:
        if self._volume is None:
            return self.py3.COLOR_BAD
        if self._volume.mute:
            return self.py3.COLOR_MUTED or self.py3.COLOR_BAD
        return self.py3.threshold_get_color(self._volume.level)

    def _icon_for_output(self) -> str:
        return self.blocks[
            min(
                len(self.blocks) - 1,
                int(math.ceil(self._volume.level / 100 * (len(self.blocks) - 1))),
            )
        ]

    def _format_output(self) -> Union[str, Composite]:
        return self.py3.safe_format(format_string=self.format_muted if self._volume.mute else self.format,
                                    param_dict={"icon": self._icon_for_output(),
                                                "percentage": self._volume.level})

    def volume_status(self):
        response = {
            "cached_until": self.py3.CACHE_FOREVER,
            "color": self._color_for_output(),
            "full_text": self._format_output()
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
