# -*- coding: utf-8 -*-
"""
Display vnStat traffic statistics.

Configuration parameters:
    cache_timeout: refresh interval for this module (default 180)
    format: display format for this module
        *(default "vnStat [\?color=good {daily_rx} {daily_rx_unit}] "
        "[\?color=bad {daily_tx} {daily_tx_unit}] "
        "[\?color=darkgray {daily_total} {daily_total_unit}]")*
    thresholds:  specify color thresholds to use (default [])

Format placeholders:
    {version}           eg 1
    {interface}         eg eno1
    {daily_timestamp}   eg 2019-02-04
    {daily_rx}          eg 954.6  # MiB
    {daily_tx}          eg 58.2  # MiB
    {daily_total}       eg 1.0  # GiB
    {daily_avg}         eg 27.4  # KiB
    {monthly_timestamp} eg 2019-02
    {monthly_rx}        eg 15.0  # GiB
    {monthly_tx}        eg 1.6  # GiB
    {monthly_total}     eg 16.5  # GiB
    {monthly_avg}       eg 58.4  # KiB
    {all_time_rx}       eg 271.4  # GiB
    {all_time_tx}       eg 16.7  # GiB
    {all_time_total}    eg 288.0  # GiB

    You can replicate placeholders with an unit (e.g., '{daily_total_unit}')
    to display `KiB`, `MiB`, `GiB`, etc to be used with `{daily_total}`.

Color thresholds:
    xxx: print a color based on the value of `xxx` placeholder

Requires:
    vnstat: a console-based network traffic monitor

Examples:
```
# colorize thresholds
vnstat {
    format = '[\?color=daily_total {daily_total} {daily_total_unit}]'
    thresholds = [
        (838860800, "degraded"),  # 838860800 B -> 800 MiB
        (943718400, "bad"),       # 943718400 B -> 900 MiB
    ]
}

# show daily placeholders
vnstat {
    format = "vnStat: "
    format += "[\?color=darkgray&show daily] "
    format += "[\?color=white {daily_timestamp}] "
    format += "[\?color=good {daily_rx} {daily_rx_unit}] "
    format += "[\?color=bad {daily_tx} {daily_tx_unit}] "
    format += "[\?color=degraded {daily_total} {daily_total_unit}] "
    format += "[\?color=deepskyblue {daily_avg} {daily_avg_unit}]"
}

# show monthly placeholders
vnstat {
    format = "vnStat: "
    format += "[\?color=darkgray&show monthly] "
    format += "[\?color=white {monthly_timestamp}] "
    format += "[\?color=good {monthly_rx} {monthly_rx_unit}] "
    format += "[\?color=bad {monthly_tx} {monthly_tx_unit}] "
    format += "[\?color=degraded {monthly_total} {monthly_total_unit}] "
    format += "[\?color=deepskyblue {monthly_avg} {monthly_avg_unit}]"
}

# show all times placeholders
vnstat {
    format = "vnStat: "
    format += "[\?color=darkgray&show all time] "
    format += "[\?color=good {all_time_rx} {all_time_rx_unit}] "
    format += "[\?color=bad {all_time_tx} {all_time_tx_unit}] "
    format += "[\?color=degraded {all_time_total} {all_time_total_unit}]"
}

# show statisitcs image
vnstat {
    on_click 1 = "exec ~/.config/py3status/vnstati.sh"

    # #!/usr/bin/env sh
    # vnstati -i eno1 --fiveminutes -o /tmp/pystatus_vnstat-0.png
    # vnstati -i eno1 -h -o /tmp/pystatus_vnstat-1.png
    # vnstati -i eno1 -d -o /tmp/pystatus_vnstat-2.png
    # vnstati -i eno1 -m -o /tmp/pystatus_vnstat-3.png
    # vnstati -i eno1 --top -o /tmp/pystatus_vnstat-4.png
    # convert -append /tmp/pystatus_vnstat* /tmp/py3status_vnstat.png
    # rm /tmp/pystatus_vnstat-*.png
    # xdg-open /tmp/py3status_vnstat.png
}
```

@author shadowprince, lasers
@license Eclipse Public License

SAMPLE OUTPUT
[
    {'full_text': 'vnStat '},
    {'full_text': '978.1 MiB ', 'color': '#00FF00'},
    {'full_text': '66.2 MiB ', 'color': '#FF0000'},
    {'full_text': '1.0 GiB', 'color': '#A9A9A9'}
]

monthly
[
    {'full_text': 'vnStat '},
    {'full_text': '15.1 GiB ', 'color': '#00FF00'},
    {'full_text': '1.6 GiB ', 'color': '#FF0000'},
    {'full_text': '16.7 GiB', 'color': '#A9A9A9'}
]

all_time
[
    {'full_text': 'vnStat '},
    {'full_text': '271.5 GiB ', 'color': '#00FF00'},
    {'full_text': '16.7 GiB ', 'color': '#FF0000'},
    {'full_text': '288.2 GiB', 'color': '#A9A9A9'}
]
"""

STRING_NOT_INSTALLED = "not installed"


class Py3status:
    """
    """

    # available configuration parameters
    cache_timeout = 180
    format = (
        u"vnStat "
        u"[\?color=good {daily_rx} {daily_rx_unit}] "
        u"[\?color=bad {daily_tx} {daily_tx_unit}] "
        u"[\?color=darkgray {daily_total} {daily_total_unit}]"
    )
    thresholds = []

    def post_config_hook(self):
        if not self.py3.check_commands("vnstat"):
            raise Exception(STRING_NOT_INSTALLED)

        placeholders = self.py3.get_placeholders_list(self.format)
        abbrs = ("_rx", "_tx", "_total", "_avg")
        self.format = self.py3.update_placeholder_formats(
            self.format, {x: ":g" for x in placeholders if x.endswith(abbrs)}
        )
        self.button_open = 1
        self.placeholders = placeholders
        self.keys = [
            "version",
            "interface",
            "daily_timestamp",
            "daily_rx",
            "daily_tx",
            "daily_total",
            "daily_avg",
            "monthly_timestamp",
            "monthly_rx",
            "monthly_tx",
            "monthly_total",
            "monthly_avg",
            "all_time_rx",
            "all_time_tx",
            "all_time_total",
        ]

        # deprecations
        self.statistics_type = {"d": "daily_", "m": "monthly_"}.get(
            getattr(self, "statistics_type", "d"), "daily_"
        )
        self.coloring = getattr(self, "coloring", {})
        if self.coloring and "total" in placeholders and not self.thresholds:
            self.thresholds = [
                (num * 1024 ** 2, col) for num, col in self.coloring.items()
            ]
        else:
            self.coloring = False

        self.thresholds_init = self.py3.get_color_names_list(self.format)

    def _get_vnstat_data(self):
        lines = self.py3.command_output(["vnstat", "--oneline", "b"])
        return dict(zip(self.keys, lines.splitlines()[0].split(";")))

    def vnstat(self):
        vnstat_data = self._get_vnstat_data()

        # deprecations
        color = None
        for x, y in (("tx", "up"), ("rx", "down"), ("total", "total")):
            vnstat_data[y] = vnstat_data[self.statistics_type + x]
        if self.coloring:
            color = self.py3.threshold_get_color(vnstat_data["total"])

        for x in self.thresholds_init:
            if x in vnstat_data:
                self.py3.threshold_get_color(vnstat_data[x], x)

        for x in list(self.placeholders):
            try:
                keys, value = [x, x + "_unit"], int(vnstat_data[x])
                vnstat_data.update(zip(keys, self.py3.format_units(value)))
            except (KeyError, ValueError):
                self.placeholders.remove(x)

        response = {
            "cached_until": self.py3.time_in(self.cache_timeout),
            "full_text": self.py3.safe_format(self.format, vnstat_data),
        }
        if color:
            response["color"] = color
        return response


if __name__ == "__main__":
    """
    Run module in test mode.
    """
    from py3status.module_test import module_test

    module_test(Py3status)
