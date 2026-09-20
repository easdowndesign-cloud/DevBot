"""Radio receiver logic shared by the CLI and desktop dashboard."""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from typing import Optional


RADIO_GROUP = 73
PICO_RADIO_ADDRESS = 1
PI_RADIO_ADDRESS = 2
RADIO_FREQUENCY = 922
RADIO_SPEED = 2
DIRECTION_THRESHOLD = 6000
LINK_TIMEOUT_SECONDS = 1.0


@dataclass(frozen=True)
class Telemetry:
    sequence: int
    raw_x: int
    raw_y: int
    direction: str
    rssi: int
    received_at: float


@dataclass(frozen=True)
class ReceiverEvent:
    kind: str
    detail: str = ""
    telemetry: Optional[Telemetry] = None


def direction(raw_x: int, raw_y: int) -> str:
    """Convert the two raw ADC readings into the remote direction label."""
    # This joystick's electrical X polarity is opposite to display/drive direction.
    x = 32768 - raw_x
    y = 32768 - raw_y
    horizontal = ""
    vertical = ""
    if abs(x) >= DIRECTION_THRESHOLD:
        horizontal = "RIGHT" if x > 0 else "LEFT"
    if abs(y) >= DIRECTION_THRESHOLD:
        vertical = "FWD" if y > 0 else "REV"
    if vertical and horizontal:
        return vertical + " " + horizontal
    return vertical or horizontal or "CENTRE"


def joystick_marker(raw_x: int, raw_y: int, radius: int) -> tuple[int, int]:
    """Map raw joystick values to signed canvas offsets within ``radius``."""
    x = round((32768 - raw_x) * radius / 32768)
    y = round((raw_y - 32768) * radius / 32768)
    return max(-radius, min(radius, x)), max(-radius, min(radius, y))


def decode_packet(
    source: int,
    payload: bytes,
    rssi: int,
    received_at: Optional[float] = None,
) -> Optional[Telemetry]:
    """Validate and decode one ``J,sequence,x,y`` remote packet."""
    if source != PICO_RADIO_ADDRESS:
        return None
    try:
        fields = payload.decode("ascii").split(",")
        if len(fields) != 4 or fields[0] != "J":
            return None
        sequence = int(fields[1])
        raw_x = int(fields[2])
        raw_y = int(fields[3])
    except (UnicodeError, ValueError):
        return None
    if not 0 <= sequence < 10000:
        return None
    if not 0 <= raw_x <= 65535 or not 0 <= raw_y <= 65535:
        return None
    return Telemetry(
        sequence=sequence,
        raw_x=raw_x,
        raw_y=raw_y,
        direction=direction(raw_x, raw_y),
        rssi=rssi,
        received_at=time.monotonic() if received_at is None else received_at,
    )


class RadioReceiver(threading.Thread):
    """Own the PiicoDev device and publish receiver events to a queue."""

    def __init__(self, events: "queue.Queue[ReceiverEvent]") -> None:
        super().__init__(name="devbot-radio", daemon=True)
        self.events = events
        self.stop_requested = threading.Event()

    def stop(self) -> None:
        self.stop_requested.set()

    def _publish(self, event: ReceiverEvent) -> None:
        try:
            self.events.put_nowait(event)
        except queue.Full:
            try:
                self.events.get_nowait()
            except queue.Empty:
                pass
            self.events.put_nowait(event)

    @staticmethod
    def _open_radio():
        from PiicoDev_Transceiver import PiicoDev_Transceiver

        return PiicoDev_Transceiver(
            bus=1,
            i2c_address=0x1A,
            group=RADIO_GROUP,
            radio_address=PI_RADIO_ADDRESS,
            speed=RADIO_SPEED,
            radio_frequency=RADIO_FREQUENCY,
            tx_power=20,
            suppress_warnings=True,
        )

    def run(self) -> None:
        while not self.stop_requested.is_set():
            self._publish(ReceiverEvent("status", "INITIALISING"))
            try:
                radio = self._open_radio()
                self._publish(ReceiverEvent("status", "READY"))
                self._receive_loop(radio)
            except Exception as error:
                self._publish(ReceiverEvent("error", repr(error)))
                self.stop_requested.wait(2.0)

    def _receive_loop(self, radio) -> None:
        while not self.stop_requested.is_set():
            if radio.receive_bytes():
                telemetry = decode_packet(
                    source=int(radio.source_radio_address),
                    payload=bytes(radio.received_bytes),
                    rssi=int(radio.rssi),
                )
                if telemetry is not None:
                    acknowledgement = "A,{}".format(telemetry.sequence).encode()
                    radio.send_bytes(acknowledgement, address=PICO_RADIO_ADDRESS)
                    self._publish(ReceiverEvent("telemetry", telemetry=telemetry))
            self.stop_requested.wait(0.01)
