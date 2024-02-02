#!/usr/bin/env python3
# ========================================================================== #
#                                                                            #
#    KVMD-OLED - A small OLED daemon for PiKVM.                              #
#                                                                            #
#    Copyright (C) 2018  Maxim Devaev <mdevaev@gmail.com>                    #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU General Public License as published by    #
#    the Free Software Foundation, either version 3 of the License, or       #
#    (at your option) any later version.                                     #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU General Public License for more details.                            #
#                                                                            #
#    You should have received a copy of the GNU General Public License       #
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.  #
#                                                                            #
# ========================================================================== #


import sys
import socket
import signal
import itertools
import logging
import datetime
import time

import netifaces
import psutil
import usb.core

from luma.core import cmdline as luma_cmdline
from luma.core.device import device as luma_device
from luma.core.render import canvas as luma_canvas

from PIL import Image
from PIL import ImageFont


# =====
_logger = logging.getLogger("oled")


# =====
def _get_ip() -> tuple[str, str]:
    try:
        gws = netifaces.gateways()
        if "default" in gws:
            for proto in [socket.AF_INET, socket.AF_INET6]:
                if proto in gws["default"]:
                    iface = gws["default"][proto][1]
                    addrs = netifaces.ifaddresses(iface)
                    return (iface, addrs[proto][0]["addr"])

        for iface in netifaces.interfaces():
            if not iface.startswith(("lo", "docker")):
                addrs = netifaces.ifaddresses(iface)
                for proto in [socket.AF_INET, socket.AF_INET6]:
                    if proto in addrs:
                        return (iface, addrs[proto][0]["addr"])
    except Exception:
        # _logger.exception("Can't get iface/IP")
        pass
    return ("<no-iface>", "<no-ip>")


def _get_uptime() -> str:
    uptime = datetime.timedelta(seconds=int(time.time() - psutil.boot_time()))
    pl = {"days": uptime.days}
    (pl["hours"], rem) = divmod(uptime.seconds, 3600)
    (pl["mins"], pl["secs"]) = divmod(rem, 60)
    return "{days}d {hours}h {mins}m".format(**pl)


def _get_temp(fahrenheit: bool) -> str:
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as temp_file:
            temp = int((temp_file.read().strip())) / 1000
            if fahrenheit:
                temp = temp * 9 / 5 + 32
                return f"{temp:.1f}\u00b0F"
            return f"{temp:.1f}\u00b0C"
    except Exception:
        # _logger.exception("Can't read temp")
        return "<no-temp>"


def _get_cpu() -> str:
    st = psutil.cpu_times_percent()
    user = st.user - st.guest
    nice = st.nice - st.guest_nice
    idle_all = st.idle + st.iowait
    system_all = st.system + st.irq + st.softirq
    virtual = st.guest + st.guest_nice
    total = max(1, user + nice + system_all + idle_all + st.steal + virtual)
    percent = int(
        st.nice / total * 100
        + st.user / total * 100
        + system_all / total * 100
        + (st.steal + st.guest) / total * 100
    )
    return f"{percent}%"


def _get_mem() -> str:
    return f"{int(psutil.virtual_memory().percent)}%"


# =====
class Screen:
    def __init__(
        self,
        device: luma_device,
        font: ImageFont.FreeTypeFont,
        font_spacing: int,
        offset: tuple[int, int],
    ) -> None:

        self.__device = device
        self.__font = font
        self.__font_spacing = font_spacing
        self.__offset = offset

    def draw_text(self, text: str, offset_x: int=0) -> None:
        with luma_canvas(self.__device) as draw:
            offset = list(self.__offset)
            offset[0] += offset_x
            draw.multiline_text(offset, text, font=self.__font, spacing=self.__font_spacing, fill="white")

    def draw_image(self, image_path: str) -> None:
        with luma_canvas(self.__device) as draw:
            draw.bitmap(self.__offset, Image.open(image_path).convert("1"), fill="white")


def _detect_geometry() -> dict:
    with open("/proc/device-tree/model") as file:
        is_cm4 = ("Compute Module 4" in file.read())
    has_usb = bool(list(usb.core.find(find_all=True)))
    if is_cm4 and has_usb:
        return {"height": 64, "rotate": 2}
    return {"height": 32, "rotate": 0}


# =====
def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("PIL").setLevel(logging.ERROR)

    parser = luma_cmdline.create_parser(description="Display FQDN and IP on the OLED")
    parser.set_defaults(**_detect_geometry())

    parser.add_argument("--font", default="/usr/share/fonts/TTF/ProggySquare.ttf", help="Font path")
    parser.add_argument("--font-size", default=16, type=int, help="Font size")
    parser.add_argument("--font-spacing", default=2, type=int, help="Font line spacing")
    parser.add_argument("--offset-x", default=0, type=int, help="Horizontal offset")
    parser.add_argument("--offset-y", default=0, type=int, help="Vertical offset")
    parser.add_argument("--interval", default=5, type=int, help="Screens interval")
    parser.add_argument("--image", default="", help="Display some image, wait a single interval and exit")
    parser.add_argument("--text", default="", help="Display some text, wait a single interval and exit")
    parser.add_argument("--pipe", action="store_true", help="Read and display lines from stdin until EOF, wait a single interval and exit")
    parser.add_argument("--clear-on-exit", action="store_true", help="Clear display on exit")
    parser.add_argument("--contrast", default=64, type=int, help="Set OLED contrast, values from 0 to 255")
    parser.add_argument("--fahrenheit", action="store_true", help="Display temperature in Fahrenheit instead of Celsius")
    options = parser.parse_args(sys.argv[1:])
    if options.config:
        config = luma_cmdline.load_config(options.config)
        options = parser.parse_args(config + sys.argv[1:])

    device = luma_cmdline.create_device(options)
    device.cleanup = (lambda _: None)
    screen = Screen(
        device=device,
        font=ImageFont.truetype(options.font, options.font_size),
        font_spacing=options.font_spacing,
        offset=(options.offset_x, options.offset_y),
    )

    if options.display not in luma_cmdline.get_display_types()["emulator"]:
        _logger.info("Iface: %s", options.interface)
    _logger.info("Display: %s", options.display)
    _logger.info("Size: %dx%d", device.width, device.height)
    options.contrast = min(max(options.contrast, 0), 255)
    _logger.info("Contrast: %d", options.contrast)
    device.contrast(options.contrast)

    try:
        if options.image:
            screen.draw_image(options.image)
            time.sleep(options.interval)

        elif options.text:
            screen.draw_text(options.text.replace("\\n", "\n"))
            time.sleep(options.interval)

        elif options.pipe:
            text = ""
            for line in sys.stdin:
                text += line
                if "\0" in text:
                    screen.draw_text(text.replace("\0", ""))
                    text = ""
            time.sleep(options.interval)

        else:
            stop_reason: (str | None) = None

            def sigusr_handler(signum: int, _) -> None:  # type: ignore
                nonlocal stop_reason
                if signum in (signal.SIGINT, signal.SIGTERM):
                    stop_reason = ""
                elif signum == signal.SIGUSR1:
                    stop_reason = "Rebooting...\nPlease wait"
                elif signum == signal.SIGUSR2:
                    stop_reason = "Halted"

            for signum in [signal.SIGTERM, signal.SIGINT, signal.SIGUSR1, signal.SIGUSR2]:
                signal.signal(signum, sigusr_handler)

            hb = itertools.cycle(r"/-\|")  # Heartbeat
            swim = 0

            def draw(text: str) -> None:
                nonlocal swim
                count = 0
                while (count < max(options.interval, 1) * 2) and stop_reason is None:
                    screen.draw_text(
                        text=text.replace("__hb__", next(hb)),
                        offset_x=(3 if swim < 0 else 0),
                    )
                    count += 1
                    if swim >= 1200:
                        swim = -1200
                    else:
                        swim += 1
                    time.sleep(0.5)

            if device.height >= 64:
                while stop_reason is None:
                    (iface, ip) = _get_ip()
                    text = f"{socket.getfqdn()}\n{ip}\niface: {iface}\ntemp: {_get_temp(options.fahrenheit)}"
                    text += f"\ncpu: {_get_cpu()} mem: {_get_mem()}\n(__hb__) {_get_uptime()}"
                    draw(text)
            else:
                summary = True
                while stop_reason is None:
                    if summary:
                        text = f"{socket.getfqdn()}\n(__hb__) {_get_uptime()}\ntemp: {_get_temp(options.fahrenheit)}"
                    else:
                        (iface, ip) = _get_ip()
                        text = "%s\n(__hb__) iface: %s\ncpu: %s mem: %s" % (ip, iface, _get_cpu(), _get_mem())
                    draw(text)
                    summary = (not summary)

            if stop_reason is not None:
                if len(stop_reason) > 0:
                    options.clear_on_exit = False
                    screen.draw_text(stop_reason)
                while len(stop_reason) > 0:
                    time.sleep(0.1)

    except (SystemExit, KeyboardInterrupt):
        pass

    if options.clear_on_exit:
        screen.draw_text("")


if __name__ == "__main__":
    main()
