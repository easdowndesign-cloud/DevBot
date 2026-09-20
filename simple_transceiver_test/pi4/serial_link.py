"""Threaded USB serial bridge between remote telemetry and the Arduino Mega."""

from __future__ import annotations

import glob
import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from receiver_core import Telemetry
from serial_protocol import (
    CONTROL_MOTION_THRESHOLD,
    ArduinoTelemetry,
    ControlCommand,
    MegaHello,
    build_control_frame,
    normalize_remote_axes,
    parse_mega_frame,
)


SERIAL_BAUD = 115200
SERIAL_SEND_INTERVAL_SECONDS = 0.04
REMOTE_CONTROL_TIMEOUT_SECONDS = 0.30
NO_REMOTE_AGE_MS = 60000


@dataclass(frozen=True)
class SerialEvent:
    kind: str
    detail: str = ""
    raw: str = ""
    telemetry: Optional[ArduinoTelemetry] = None
    hello: Optional[MegaHello] = None


def discover_arduino_port() -> str | None:
    """Prefer stable by-id names, then fall back to ACM/USB serial devices."""
    by_id = sorted(glob.glob("/dev/serial/by-id/*"))
    for candidate in by_id:
        name = Path(candidate).name.lower()
        if "arduino" in name or "mega" in name:
            return candidate
    if by_id:
        return by_id[0]
    fallback = sorted(glob.glob("/dev/ttyACM*")) + sorted(glob.glob("/dev/ttyUSB*"))
    return fallback[0] if fallback else None


class SerialControlBridge(threading.Thread):
    """Own one persistent serial port and exchange framed control records."""

    def __init__(self, events: "queue.Queue[SerialEvent]") -> None:
        super().__init__(name="devbot-arduino-serial", daemon=True)
        self.events = events
        self.stop_requested = threading.Event()
        self._remote_lock = threading.Lock()
        self._latest_remote: Telemetry | None = None
        self._frame_sequence = 0

    def stop(self) -> None:
        self.stop_requested.set()

    def set_remote_telemetry(self, telemetry: Telemetry) -> None:
        with self._remote_lock:
            self._latest_remote = telemetry

    def _publish(self, event: SerialEvent) -> None:
        try:
            self.events.put_nowait(event)
        except queue.Full:
            try:
                self.events.get_nowait()
            except queue.Empty:
                pass
            self.events.put_nowait(event)

    def _next_command(self, now: float) -> ControlCommand:
        with self._remote_lock:
            remote = self._latest_remote

        if remote is None:
            remote_sequence = 0
            age_ms = NO_REMOTE_AGE_MS
            steering = 0
            throttle = 0
            enabled = False
        else:
            age_seconds = max(0.0, now - remote.received_at)
            age_ms = min(NO_REMOTE_AGE_MS, round(age_seconds * 1000))
            remote_sequence = remote.sequence
            if age_seconds <= REMOTE_CONTROL_TIMEOUT_SECONDS:
                steering, throttle = normalize_remote_axes(remote.raw_x, remote.raw_y)
                # Commissioning policy until the remote payload gains a physical
                # dead-man bit: non-neutral motion enables the real drivers and
                # returning to centre disables them. The Mega still independently
                # enforces neutral re-arm and both communications watchdogs.
                enabled = (
                    abs(steering) > CONTROL_MOTION_THRESHOLD
                    or abs(throttle) > CONTROL_MOTION_THRESHOLD
                )
            else:
                steering = 0
                throttle = 0
                enabled = False

        command = ControlCommand(
            frame_sequence=self._frame_sequence,
            remote_sequence=remote_sequence,
            remote_age_ms=age_ms,
            enabled=enabled,
            steering=steering,
            throttle=throttle,
        )
        self._frame_sequence = (self._frame_sequence + 1) & 0xFFFF
        return command

    def run(self) -> None:
        while not self.stop_requested.is_set():
            port = discover_arduino_port()
            if port is None:
                self._publish(SerialEvent("status", "NOT_FOUND"))
                self.stop_requested.wait(1.0)
                continue
            try:
                self._run_connection(port)
            except Exception as error:
                self._publish(SerialEvent("error", repr(error)))
                self._publish(SerialEvent("status", "DISCONNECTED"))
                self.stop_requested.wait(2.0)

    def _run_connection(self, port: str) -> None:
        import serial

        self._publish(SerialEvent("status", "OPENING {}".format(port)))
        with serial.Serial(
            port=port,
            baudrate=SERIAL_BAUD,
            timeout=0.02,
            write_timeout=0.1,
            exclusive=True,
        ) as connection:
            self._publish(SerialEvent("status", "WAITING_FOR_MEGA"))
            ready = False
            opened_at = time.monotonic()
            next_send_at = opened_at

            while not self.stop_requested.is_set():
                raw = connection.readline()
                if raw:
                    visible = raw.decode("ascii", errors="replace").strip()
                    self._publish(SerialEvent("rx", raw=visible))
                    message = parse_mega_frame(raw)
                    if isinstance(message, MegaHello):
                        ready = True
                        self._publish(SerialEvent("hello", hello=message))
                        self._publish(SerialEvent("status", "READY"))
                    elif isinstance(message, ArduinoTelemetry):
                        self._publish(SerialEvent("telemetry", telemetry=message))

                now = time.monotonic()
                if not ready and now - opened_at > 5.0:
                    raise TimeoutError("Mega did not send a valid HELLO frame")
                if ready and now >= next_send_at:
                    frame = build_control_frame(self._next_command(now))
                    connection.write(frame)
                    self._publish(
                        SerialEvent(
                            "tx",
                            raw=frame.decode("ascii").strip(),
                        )
                    )
                    next_send_at = now + SERIAL_SEND_INTERVAL_SECONDS
