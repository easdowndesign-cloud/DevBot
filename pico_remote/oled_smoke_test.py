"""Standalone PiicoDev OLED commissioning test for the Pico remote."""

from machine import I2C, Pin

import config
from PiicoDev_SSD1306 import create_PiicoDev_SSD1306


def release_bus(bus):
    deinitialize = getattr(bus, "deinit", None)
    if deinitialize is not None:
        deinitialize()


print("Scanning I2C0 at {} Hz...".format(config.I2C_FREQUENCY_HZ))
probe = I2C(
    config.I2C_BUS,
    sda=Pin(config.I2C_SDA_PIN),
    scl=Pin(config.I2C_SCL_PIN),
    freq=config.I2C_FREQUENCY_HZ,
)
try:
    addresses = probe.scan()
    print("Found:", [hex(address) for address in addresses])
    if config.OLED_I2C_ADDRESS not in addresses:
        raise OSError("OLED 0x3C not found")
finally:
    release_bus(probe)

display = create_PiicoDev_SSD1306(
    address=config.OLED_I2C_ADDRESS,
    bus=config.I2C_BUS,
    freq=config.I2C_FREQUENCY_HZ,
    sda=Pin(config.I2C_SDA_PIN),
    scl=Pin(config.I2C_SCL_PIN),
)
if getattr(display, "comms_err", False):
    raise OSError("OLED driver reported an initialization error")

display.fill(0)
display.rect(0, 0, 127, 63, 1)
display.text("DEVBOT OLED OK", 8, 10, 1)
display.text("ADDR 0x3C", 20, 28, 1)
display.text("I2C 400kHz", 20, 44, 1)
display.show()

if getattr(display, "comms_err", False):
    raise OSError("OLED driver reported a drawing error")
print("PASS: OLED should show a border and three lines of text.")

