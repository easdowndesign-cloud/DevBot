"""Hardware-independent Pi 4 ↔ Arduino Mega serial protocol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union


PROTOCOL_VERSION = 2
DRIVE_SCALE = 1000
REMOTE_CENTRE = 32768
REMOTE_DEADBAND = 6000
CONTROL_MOTION_THRESHOLD = 50

STATE_NAMES = {
    0: "BOOT",
    1: "DISABLED",
    2: "AWAIT_NEUTRAL",
    3: "READY",
    4: "DRIVING_FORWARD",
    5: "DRIVING_REVERSE",
    # The Pi reverses steering before USB transmission to match the assembled
    # robot's physical left/right response. Translate the Mega's logical turn
    # state back to the physical direction shown in both dashboards.
    6: "TURNING_RIGHT",
    7: "TURNING_LEFT",
    8: "OBSTACLE_STOP",
    9: "COMMS_LOST",
    10: "FAULT",
}


@dataclass(frozen=True)
class ControlCommand:
    frame_sequence: int
    remote_sequence: int
    remote_age_ms: int
    enabled: bool
    steering: int
    throttle: int


@dataclass(frozen=True)
class MegaHello:
    protocol_version: int
    device: str
    capability: str


@dataclass(frozen=True)
class ArduinoTelemetry:
    acknowledged_sequence: int
    state_id: int
    state: str
    applied_left: int
    applied_right: int
    driver_enable_mask: int
    bumper_mask: int
    fault_mask: int


MegaMessage = Union[MegaHello, ArduinoTelemetry]


def crc16_ccitt(data: bytes) -> int:
    """Return CRC-16/CCITT-FALSE for the supplied bytes."""
    crc = 0xFFFF
    for value in data:
        crc ^= value << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def encode_frame(*fields: object) -> bytes:
    """Encode one ASCII record with CRC and newline framing."""
    body = ",".join(str(field) for field in fields)
    checksum = crc16_ccitt(body.encode("ascii"))
    return "{}*{:04X}\n".format(body, checksum).encode("ascii")


def decode_frame(raw: bytes) -> list[str] | None:
    """Validate one framed record and return its comma-separated fields."""
    try:
        line = raw.decode("ascii").strip()
        body, checksum_text = line.rsplit("*", 1)
        if len(checksum_text) != 4:
            return None
        received_checksum = int(checksum_text, 16)
    except (UnicodeError, ValueError):
        return None
    if received_checksum != crc16_ccitt(body.encode("ascii")):
        return None
    return body.split(",")


def normalize_axis(raw: int) -> int:
    """Map a 16-bit remote ADC axis into -1000..+1000 with deadband."""
    delta = REMOTE_CENTRE - raw
    if abs(delta) <= REMOTE_DEADBAND:
        return 0
    span = (
        REMOTE_CENTRE - REMOTE_DEADBAND
        if delta > 0
        else 65535 - REMOTE_CENTRE - REMOTE_DEADBAND
    )
    magnitude = round((abs(delta) - REMOTE_DEADBAND) * DRIVE_SCALE / max(span, 1))
    magnitude = max(0, min(DRIVE_SCALE, magnitude))
    return magnitude if delta > 0 else -magnitude


def normalize_remote_axes(raw_x: int, raw_y: int) -> tuple[int, int]:
    """Return Mega steering/throttle with the installed steering polarity."""
    return -normalize_axis(raw_x), normalize_axis(raw_y)


def build_control_frame(command: ControlCommand) -> bytes:
    """Encode the complete latest-state control command for the Mega."""
    return encode_frame(
        "C",
        PROTOCOL_VERSION,
        command.frame_sequence,
        command.remote_sequence,
        command.remote_age_ms,
        int(command.enabled),
        command.steering,
        command.throttle,
    )


def parse_mega_frame(raw: bytes) -> MegaMessage | None:
    """Decode a Mega hello or telemetry frame after validating its CRC."""
    fields = decode_frame(raw)
    if fields is None:
        return None
    try:
        if len(fields) == 4 and fields[0] == "H":
            version = int(fields[1])
            if version != PROTOCOL_VERSION:
                return None
            return MegaHello(version, fields[2], fields[3])
        if len(fields) == 9 and fields[0] == "T":
            version = int(fields[1])
            acknowledged = int(fields[2])
            state_id = int(fields[3])
            left = int(fields[4])
            right = int(fields[5])
            driver_enable_mask = int(fields[6])
            bumpers = int(fields[7])
            faults = int(fields[8])
            if version != PROTOCOL_VERSION or state_id not in STATE_NAMES:
                return None
            if not 0 <= acknowledged <= 65535:
                return None
            if not -DRIVE_SCALE <= left <= DRIVE_SCALE:
                return None
            if not -DRIVE_SCALE <= right <= DRIVE_SCALE:
                return None
            if not 0 <= driver_enable_mask <= 3:
                return None
            if not 0 <= bumpers <= 7 or not 0 <= faults <= 255:
                return None
            return ArduinoTelemetry(
                acknowledged_sequence=acknowledged,
                state_id=state_id,
                state=STATE_NAMES[state_id],
                applied_left=left,
                applied_right=right,
                driver_enable_mask=driver_enable_mask,
                bumper_mask=bumpers,
                fault_mask=faults,
            )
    except ValueError:
        return None
    return None
