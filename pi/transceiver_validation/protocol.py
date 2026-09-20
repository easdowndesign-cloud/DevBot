"""Fixed-width DevBot radio frames and wrap-safe sequence validation."""

try:
    import ustruct as struct
except ImportError:  # Desktop CPython tests.
    import struct

MAGIC = b"DB"
CONTROL_TYPE = 0x01
ACK_TYPE = 0x02

CONTROL_FORMAT_NO_CRC = ">2sBBIHHIhhH"
CONTROL_FORMAT = ">2sBBIHHIhhHH"
ACK_FORMAT_NO_CRC = ">2sBBIHHBBHI"
ACK_FORMAT = ">2sBBIHHBBHIH"
CONTROL_LENGTH = 24
ACK_LENGTH = 22

FLAG_ACTIVE = 1 << 0
FLAG_CENTRED_ONCE = 1 << 1
FLAG_REMOTE_FAULT = 1 << 2
FLAG_DISPLAY_DEGRADED = 1 << 3
FLAG_LINK_RECOVERY = 1 << 4
KNOWN_CONTROL_FLAGS = 0x001F
KNOWN_ROBOT_FAULT_FLAGS = 0x001F
MAX_ROBOT_STATE = 8


class ProtocolError(ValueError):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def crc16_ccitt(data, initial=0xFFFF):
    """CRC-16-CCITT-FALSE: polynomial 0x1021, initial value 0xFFFF."""
    crc = initial
    for value in data:
        crc ^= value << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def _bounded_axis(value):
    value = int(value)
    if value < -1000 or value > 1000:
        raise ProtocolError("axis")
    return value


def pack_control(version, pair_id, session_id, sequence, uptime_ms,
                 steer, throttle, flags):
    steer = _bounded_axis(steer)
    throttle = _bounded_axis(throttle)
    flags = int(flags)
    if flags & ~KNOWN_CONTROL_FLAGS:
        raise ProtocolError("flags")
    if not (flags & FLAG_ACTIVE) and (steer != 0 or throttle != 0):
        raise ProtocolError("inactive_axes")
    body = struct.pack(
        CONTROL_FORMAT_NO_CRC, MAGIC, int(version), CONTROL_TYPE,
        int(pair_id) & 0xFFFFFFFF, int(session_id) & 0xFFFF,
        int(sequence) & 0xFFFF, int(uptime_ms) & 0xFFFFFFFF,
        steer, throttle, flags,
    )
    return body + struct.pack(">H", crc16_ccitt(body))


def unpack_control(frame, expected_version=None, expected_pair_id=None):
    if len(frame) != CONTROL_LENGTH:
        raise ProtocolError("length")
    values = struct.unpack(CONTROL_FORMAT, frame)
    magic, version, message_type, pair_id, session_id, sequence, uptime_ms, steer, throttle, flags, received_crc = values
    if crc16_ccitt(frame[:-2]) != received_crc:
        raise ProtocolError("crc")
    if magic != MAGIC:
        raise ProtocolError("magic")
    if message_type != CONTROL_TYPE:
        raise ProtocolError("type")
    if expected_version is not None and version != expected_version:
        raise ProtocolError("version")
    if expected_pair_id is not None and pair_id != expected_pair_id:
        raise ProtocolError("pairing")
    _bounded_axis(steer)
    _bounded_axis(throttle)
    if flags & ~KNOWN_CONTROL_FLAGS:
        raise ProtocolError("flags")
    if not (flags & FLAG_ACTIVE) and (steer != 0 or throttle != 0):
        raise ProtocolError("inactive_axes")
    return {
        "version": version, "pair_id": pair_id, "session_id": session_id,
        "sequence": sequence, "uptime_ms": uptime_ms, "steer": steer,
        "throttle": throttle, "flags": flags,
    }


def pack_ack(version, pair_id, session_id, ack_sequence, robot_state,
             bumper_mask, fault_flags, robot_uptime_ms):
    if not 0 <= int(robot_state) <= MAX_ROBOT_STATE:
        raise ProtocolError("robot_state")
    if int(bumper_mask) & ~0x07:
        raise ProtocolError("bumper_mask")
    if int(fault_flags) & ~KNOWN_ROBOT_FAULT_FLAGS:
        raise ProtocolError("fault_flags")
    body = struct.pack(
        ACK_FORMAT_NO_CRC, MAGIC, int(version), ACK_TYPE,
        int(pair_id) & 0xFFFFFFFF, int(session_id) & 0xFFFF,
        int(ack_sequence) & 0xFFFF, int(robot_state), int(bumper_mask),
        int(fault_flags), int(robot_uptime_ms) & 0xFFFFFFFF,
    )
    return body + struct.pack(">H", crc16_ccitt(body))


def unpack_ack(frame, expected_version, expected_pair_id, expected_session_id):
    if len(frame) != ACK_LENGTH:
        raise ProtocolError("length")
    values = struct.unpack(ACK_FORMAT, frame)
    magic, version, message_type, pair_id, session_id, ack_sequence, robot_state, bumper_mask, fault_flags, robot_uptime_ms, received_crc = values
    if crc16_ccitt(frame[:-2]) != received_crc:
        raise ProtocolError("crc")
    if magic != MAGIC:
        raise ProtocolError("magic")
    if version != expected_version:
        raise ProtocolError("version")
    if message_type != ACK_TYPE:
        raise ProtocolError("type")
    if pair_id != expected_pair_id:
        raise ProtocolError("pairing")
    if session_id != expected_session_id:
        raise ProtocolError("session")
    if robot_state > MAX_ROBOT_STATE:
        raise ProtocolError("robot_state")
    if bumper_mask & ~0x07:
        raise ProtocolError("bumper_mask")
    if fault_flags & ~KNOWN_ROBOT_FAULT_FLAGS:
        raise ProtocolError("fault_flags")
    return {
        "ack_sequence": ack_sequence, "robot_state": robot_state,
        "bumper_mask": bumper_mask, "fault_flags": fault_flags,
        "robot_uptime_ms": robot_uptime_ms,
    }


def sequence_is_newer(candidate, reference):
    """True when candidate is ahead of reference in modulo-65536 order."""
    difference = (int(candidate) - int(reference)) & 0xFFFF
    return 0 < difference < 0x8000


def sequence_is_current_or_newer(candidate, reference):
    return int(candidate) == int(reference) or sequence_is_newer(candidate, reference)


def sequence_was_transmitted(candidate, latest_transmitted):
    """Reject future acknowledgements while allowing recent values across wrap."""
    age = (int(latest_transmitted) - int(candidate)) & 0xFFFF
    return age < 0x8000

