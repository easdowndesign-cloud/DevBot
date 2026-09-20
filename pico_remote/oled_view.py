"""Fault-isolated, dirty-refresh OLED presentation."""

import config

def direction_label(steer, throttle, active):
    """Return a stable text direction while preserving a diagonal intent."""
    if not active:
        return "CENTRE"
    steer = int(steer)
    throttle = int(throttle)
    major = max(abs(steer), abs(throttle), 1)
    component_threshold = max(config.ACTIVE_ON, major // 3)
    horizontal = ""
    vertical = ""
    if abs(steer) >= component_threshold:
        horizontal = "RIGHT" if steer > 0 else "LEFT"
    if abs(throttle) >= component_threshold:
        vertical = "FWD" if throttle > 0 else "REV"
    if vertical and horizontal:
        return vertical + " " + horizontal
    return vertical or horizontal or "CENTRE"


class OledView:
    def __init__(self):
        self.display = None
        self.operational = False
        self._last_signature = None

    def initialize(self):
        from machine import I2C, Pin
        from PiicoDev_SSD1306 import create_PiicoDev_SSD1306

        bus = I2C(
            config.I2C_BUS,
            sda=Pin(config.I2C_SDA_PIN),
            scl=Pin(config.I2C_SCL_PIN),
            freq=config.I2C_FREQUENCY_HZ,
        )
        try:
            if config.OLED_I2C_ADDRESS not in bus.scan():
                raise OSError("PiicoDev OLED 0x3C not found")
        finally:
            # The vendor driver creates its own I2C object. Release this
            # short-lived scan object first; keeping two owners of I2C0 can
            # make later register writes fail on some MicroPython builds.
            deinitialize = getattr(bus, "deinit", None)
            if deinitialize is not None:
                deinitialize()
        self.display = create_PiicoDev_SSD1306(
            address=config.OLED_I2C_ADDRESS,
            bus=config.I2C_BUS,
            freq=config.I2C_FREQUENCY_HZ,
            sda=Pin(config.I2C_SDA_PIN),
            scl=Pin(config.I2C_SCL_PIN),
        )
        if getattr(self.display, "comms_err", False):
            raise OSError("OLED initialization failed")
        self.operational = True
        self._last_signature = None
        self._show_lines("DEVBOT REMOTE", "FW " + config.FIRMWARE_VERSION,
                         "PROTO {}".format(config.PROTOCOL_VERSION), "SELF TEST")

    def mark_failed(self):
        self.operational = False
        self.display = None
        self._last_signature = None

    def _show_lines(self, *lines):
        if not self.operational or self.display is None:
            return
        self.display.fill(0)
        for row, line in enumerate(lines[:6]):
            self.display.text(str(line)[:16], 0, row * 10, 1)
        self.display.show()
        if getattr(self.display, "comms_err", False):
            raise OSError("OLED write failed")

    def _show_main(self, snapshot):
        state = snapshot["state"]
        link = snapshot["link"]
        if link == "OK" and state in ("READY", "ACTIVE"):
            heading = "LINKED " + state
        elif link == "STALE":
            heading = "LINK STALE"
        elif state == "LINK LOST":
            heading = "LINK LOST"
        else:
            heading = "UNLINKED" if state == "UNLINKED" else state

        direction = direction_label(
            snapshot["steer"], snapshot["throttle"], snapshot["active"]
        )
        if snapshot["bumper_mask"]:
            direction = "BUMPER {:03b}".format(snapshot["bumper_mask"])
        elif snapshot["fault_flags"]:
            direction = "FAULT {:04X}".format(snapshot["fault_flags"])

        # A live crosshair makes direction and magnitude visible without
        # requiring the user to interpret raw numbers. Positive throttle is up.
        marker_x = 64 + (int(snapshot["steer"]) * 26) // 1000
        marker_y = 37 - (int(snapshot["throttle"]) * 13) // 1000
        marker_x = max(38, min(90, marker_x))
        marker_y = max(24, min(50, marker_y))

        self.display.fill(0)
        self.display.text(heading[:16], 0, 0, 1)
        self.display.text(("DIR " + direction)[:16], 0, 10, 1)
        self.display.rect(35, 21, 58, 32, 1)
        self.display.hline(38, 37, 52, 1)
        self.display.vline(64, 24, 26, 1)
        self.display.fill_rect(marker_x - 2, marker_y - 2, 4, 4, 1)
        self.display.text(
            "X{:+4d} Y{:+4d}".format(
                snapshot["steer"], snapshot["throttle"]
            )[:16],
            0, 55, 1,
        )
        self.display.show()
        if getattr(self.display, "comms_err", False):
            raise OSError("OLED write failed")

    def render(self, snapshot):
        if not self.operational:
            return False
        signature = (
            snapshot["state"], snapshot["link"], snapshot["robot_state"],
            snapshot["steer"], snapshot["throttle"], snapshot["active"],
            snapshot["bumper_mask"], snapshot["fault_flags"],
            snapshot["startup_step"], snapshot["adc_ok"],
            snapshot["oled_ok"], snapshot["radio_ok"],
        )
        if signature == self._last_signature:
            return False
        self._last_signature = signature
        if snapshot["state"] == "SELF TEST":
            step = snapshot["startup_step"]
            if step < 3:
                sweep = (" " * (step * 4)) + ">>>"
                self._show_lines(
                    "DEVBOT REMOTE", "FW " + config.FIRMWARE_VERSION,
                    "PROTO {}".format(config.PROTOCOL_VERSION),
                    "RADIO " + sweep,
                )
            else:
                self._show_lines(
                    "SELF TEST",
                    "ADC   " + ("OK" if snapshot["adc_ok"] else "CHECK"),
                    "OLED  " + ("OK" if snapshot["oled_ok"] else "DEGRADED"),
                    "RADIO " + ("OK" if snapshot["radio_ok"] else "FAULT"),
                )
            return True
        if snapshot["state"] == "WAIT NEUTRAL":
            self._show_lines(
                "CENTRE JOYSTICK", "HOLD STILL 0.5S",
                "X {:+5d}".format(snapshot["steer"]),
                "Y {:+5d}".format(snapshot["throttle"]),
                "LINK " + snapshot["link"],
            )
            return True
        self._show_main(snapshot)
        return True
