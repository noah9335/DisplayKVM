
import board
import digitalio
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306

# noah modifications
import sys
import socket
import signal
import itertools
import logging
import datetime
import time
import netifaces

# Define the Reset Pin
oled_reset = None

# Change these
# to the right size for your display!
WIDTH = 128
HEIGHT = 32  # Change to 64 if needed
BORDER = 5

# Use for I2C.
i2c = busio.I2("I2C2_SCL", "I2C2_SDA")
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
oled = adafruit_ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c, addr=0x3C, reset=oled_reset)

# Clear display.
oled.fill(0)
oled.show()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
image = Image.new("1", (oled.width, oled.height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a white background
draw.rectangle((0, 0, oled.width, oled.height), outline=255, fill=255)

# Draw a smaller inner rectangle
draw.rectangle(
    (BORDER, BORDER, oled.width - BORDER - 1, oled.height - BORDER - 1),
    outline=0,
    fill=0,
)

# Load default font.
font = ImageFont.load_default()

## noah modifications to print IP

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

iface, ip = _get_ip()
print(f"Interface: {iface}, IP Address: {ip}")







# Draw Some Text
text = "{ip}"
(font_width, font_height) = font.getsize(text)
draw.text(
    (oled.width // 2 - font_width // 2, oled.height // 2 - font_height // 2),
    text,
    font=font,
    fill=255,
)

# Display image
oled.image(image)
oled.show()
