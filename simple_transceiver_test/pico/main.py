"""Minimal DevBot Pico remote test: joystick + OLED + radio acknowledgement."""

import framebuf
import time
from machine import ADC, Pin

from PiicoDev_Transceiver import PiicoDev_Transceiver


# Hardware and radio settings.
JOYSTICK_X_PIN = 26
JOYSTICK_Y_PIN = 27
OLED_ADDRESS = 0x3C
RADIO_GROUP = 73
PICO_RADIO_ADDRESS = 1
PI_RADIO_ADDRESS = 2
RADIO_FREQUENCY = 922
RADIO_SPEED = 2

SEND_PERIOD_MS = 100
DISPLAY_PERIOD_MS = 100
LINK_TIMEOUT_MS = 1000


class SSD1306(framebuf.FrameBuffer):
    """Small SSD1306 I2C driver using MicroPython's built-in font."""

    def __init__(self, i2c, address=0x3C, width=128, height=64):
        self.i2c = i2c
        self.address = address
        self.width = width
        self.height = height
        self.pages = height // 8
        self.buffer = bytearray(self.pages * width)
        super().__init__(self.buffer, width, height, framebuf.MONO_VLSB)
        self._command = bytearray(2)
        self._initialize()

    def _write_command(self, command):
        self._command[0] = 0x80
        self._command[1] = command
        self.i2c.writeto(self.address, self._command)

    def _initialize(self):
        commands = (
            0xAE,       # display off
            0x20, 0x00, # horizontal addressing mode
            0x40,       # display start line
            0xA1,       # segment remap
            0xA8, 0x3F, # multiplex ratio: 64 rows
            0xC8,       # COM scan direction
            0xD3, 0x00, # display offset
            0xDA, 0x12, # COM pin configuration
            0xD5, 0x80, # display clock
            0xD9, 0xF1, # precharge
            0xDB, 0x30, # VCOM deselect
            0x81, 0xCF, # contrast
            0xA4,       # output follows RAM
            0xA6,       # normal display
            0x8D, 0x14, # charge pump on
            0xAF,       # display on
        )
        for command in commands:
            self._write_command(command)
        self.fill(0)
        self.show()

    def show(self):
        self._write_command(0x21)
        self._write_command(0)
        self._write_command(self.width - 1)
        self._write_command(0x22)
        self._write_command(0)
        self._write_command(self.pages - 1)
        self.i2c.writevto(self.address, (b"\x40", self.buffer))


def draw_link_icon(display, linked):
    """Draw compact radio bars; an X denotes no acknowledged link."""
    bars = ((72, 20, 4, 5), (80, 14, 4, 11), (88, 8, 4, 17))
    for x, y, width, height in bars:
        if linked:
            display.fill_rect(x, y, width, height, 1)
        else:
            display.rect(x, y, width, height, 1)
    if linked:
        display.fill_rect(98, 20, 5, 5, 1)
    else:
        display.line(98, 9, 112, 23, 1)
        display.line(112, 9, 98, 23, 1)


def draw_robot_feedback_icon(display, robot_movement):
    """Draw a robot plus confirmed movement glyph in the lower status area."""
    display.rect(70, 39, 21, 14, 1)
    display.fill_rect(73, 36, 3, 3, 1)
    display.fill_rect(85, 36, 3, 3, 1)
    display.fill_rect(72, 54, 5, 4, 1)
    display.fill_rect(84, 54, 5, 4, 1)
    display.pixel(76, 44, 1)
    display.pixel(85, 44, 1)

    # Movement is intentionally populated only by future robot feedback.
    cx = 108
    cy = 47
    if robot_movement == "FWD":
        display.vline(cx, 35, 24, 1)
        display.line(cx, 35, cx - 6, 41, 1)
        display.line(cx, 35, cx + 6, 41, 1)
    elif robot_movement in ("REV", "RWD"):
        display.vline(cx, 35, 24, 1)
        display.line(cx, 58, cx - 6, 52, 1)
        display.line(cx, 58, cx + 6, 52, 1)
    elif robot_movement == "LEFT":
        display.hline(97, cy, 24, 1)
        display.line(97, cy, 103, cy - 6, 1)
        display.line(97, cy, 103, cy + 6, 1)
    elif robot_movement == "RIGHT":
        display.hline(97, cy, 24, 1)
        display.line(120, cy, 114, cy - 6, 1)
        display.line(120, cy, 114, cy + 6, 1)
    elif robot_movement == "STOP":
        display.fill_rect(101, 40, 15, 15, 1)
    else:
        display.rect(98, 37, 21, 21, 1)
        display.hline(103, cy, 11, 1)


def draw(display, linked, raw_x, raw_y, robot_movement):
    display.fill(0)

    # The joystick plot uses the full display height on the left.
    display.rect(1, 1, 61, 62, 1)
    display.hline(4, 32, 55, 1)
    display.vline(31, 4, 56, 1)
    # This joystick's electrical X polarity is opposite to screen coordinates.
    marker_x = 31 - ((raw_x - 32768) * 27) // 32768
    marker_y = 32 + ((raw_y - 32768) * 27) // 32768
    marker_x = max(4, min(58, marker_x))
    marker_y = max(4, min(59, marker_y))
    display.fill_rect(marker_x - 2, marker_y - 2, 5, 5, 1)

    # Compact status strip: radio link above, robot feedback below.
    display.vline(65, 0, 64, 1)
    display.hline(68, 30, 58, 1)
    draw_link_icon(display, linked)
    draw_robot_feedback_icon(display, robot_movement)
    display.show()


def main():
    joystick_x = ADC(JOYSTICK_X_PIN)
    joystick_y = ADC(JOYSTICK_Y_PIN)

    # The vendor radio object creates the hardware I2C0 instance. Reuse that
    # exact object for the OLED, so there is only one owner of the shared bus.
    radio = PiicoDev_Transceiver(
        bus=0,
        freq=400000,
        sda=Pin(8),
        scl=Pin(9),
        i2c_address=0x1A,
        group=RADIO_GROUP,
        radio_address=PICO_RADIO_ADDRESS,
        speed=RADIO_SPEED,
        radio_frequency=RADIO_FREQUENCY,
        tx_power=20,
        suppress_warnings=True,
    )
    display = SSD1306(radio.i2c.i2c, OLED_ADDRESS)

    sequence = 0
    # None until confirmed movement feedback is returned by the robot.
    robot_movement = None
    last_ack_ms = None
    now = time.ticks_ms()
    next_send_ms = now
    next_display_ms = now

    while True:
        now = time.ticks_ms()
        raw_x = joystick_x.read_u16()
        raw_y = joystick_y.read_u16()

        if radio.receive_bytes():
            try:
                fields = bytes(radio.received_bytes).decode().split(",")
                if (int(radio.source_radio_address) == PI_RADIO_ADDRESS and
                        len(fields) == 2 and fields[0] == "A"):
                    int(fields[1])  # Confirm acknowledgement sequence is numeric.
                    last_ack_ms = now
            except (ValueError, UnicodeError):
                pass

        if time.ticks_diff(now, next_send_ms) >= 0:
            message = "J,{},{},{}".format(sequence, raw_x, raw_y).encode()
            radio.send_bytes(message, address=PI_RADIO_ADDRESS)
            sequence = (sequence + 1) % 10000
            next_send_ms = time.ticks_add(next_send_ms, SEND_PERIOD_MS)

        linked = (
            last_ack_ms is not None and
            time.ticks_diff(now, last_ack_ms) < LINK_TIMEOUT_MS
        )
        if time.ticks_diff(now, next_display_ms) >= 0:
            draw(display, linked, raw_x, raw_y, robot_movement)
            next_display_ms = time.ticks_add(next_display_ms, DISPLAY_PERIOD_MS)

        time.sleep_ms(10)


main()
