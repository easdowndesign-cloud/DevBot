"""Minimal Pico boot entry point for the DevBot handheld remote."""

import time
import machine
from machine import ADC, WDT, unique_id

import config
from diagnostics import Diagnostics
from joystick import ActivationLatch, AxisProcessor, Joystick, NeutralHold
from oled_view import OledView
from radio_link import PiicoDevRadioLink
from remote_controller import RemoteController


def make_session_id(adc_x, adc_y):
    value = time.ticks_us() ^ adc_x.read_u16() ^ (adc_y.read_u16() << 1)
    try:
        for byte in unique_id():
            value = ((value << 5) - value + byte) & 0xFFFFFFFF
    except Exception:
        pass
    session = (value ^ (value >> 16)) & 0xFFFF
    return session or 1


def record_reset_cause(diagnostics):
    """Log the platform reset cause when the active MicroPython port exposes it."""
    cause_function = getattr(machine, "reset_cause", None)
    if cause_function is None:
        return
    try:
        cause = cause_function()
        if cause == getattr(machine, "WDT_RESET", None):
            diagnostics.increment("watchdog_resets")
        diagnostics.event("RESET", "cause={}".format(cause))
    except Exception:
        # Reset-cause reporting is diagnostic only and must not block startup.
        pass


def build_controller():
    adc_x = ADC(config.JOYSTICK_X_PIN)
    adc_y = ADC(config.JOYSTICK_Y_PIN)
    x_axis = AxisProcessor(
        config.JOYSTICK_X_MIN, config.JOYSTICK_X_CENTRE,
        config.JOYSTICK_X_MAX, config.DEADBAND, config.COMMAND_SCALE,
        config.INVERT_X, config.EMA_ALPHA,
    )
    y_axis = AxisProcessor(
        config.JOYSTICK_Y_MIN, config.JOYSTICK_Y_CENTRE,
        config.JOYSTICK_Y_MAX, config.DEADBAND, config.COMMAND_SCALE,
        config.INVERT_Y, config.EMA_ALPHA,
    )
    joystick = Joystick(adc_x.read_u16, adc_y.read_u16, x_axis, y_axis)
    neutral_hold = NeutralHold(
        config.JOYSTICK_X_CENTRE, config.JOYSTICK_Y_CENTRE,
        config.BOOT_CENTRE_WINDOW_RAW, config.BOOT_STABILITY_SPREAD_RAW,
        config.BOOT_NEUTRAL_HOLD_MS, time.ticks_diff,
    )
    activation = ActivationLatch(
        config.ACTIVE_ON, config.ACTIVE_OFF,
        config.ACTIVE_OFF_HOLD_MS, time.ticks_diff,
    )
    diagnostics = Diagnostics(config.USB_LOGGING)
    record_reset_cause(diagnostics)
    return RemoteController(
        joystick, neutral_hold, activation, PiicoDevRadioLink(), OledView(),
        diagnostics, make_session_id(adc_x, adc_y),
        time.ticks_diff, time.ticks_add,
    )


def run():
    # A vendor driver that stalls cannot feed this watchdog. The reset always
    # returns through WAIT_NEUTRAL, never directly to an active command.
    watchdog = (
        WDT(timeout=config.WATCHDOG_TIMEOUT_MS)
        if config.WATCHDOG_ENABLED else None
    )
    controller = build_controller()
    controller.start(time.ticks_ms())
    while True:
        try:
            controller.cycle(time.ticks_ms())
            if watchdog is not None:
                watchdog.feed()
            time.sleep_ms(config.LOOP_YIELD_MS)
        except Exception as exc:
            print("FATAL {}".format(repr(exc)))
            controller.emergency_neutral(time.ticks_ms())
            if watchdog is not None:
                # Do not feed it; hardware reset restores safe startup.
                while True:
                    time.sleep_ms(100)
            # Bench mode has no watchdog: surface the complete traceback to
            # Thonny after the best-effort neutral frame.
            raise


run()
