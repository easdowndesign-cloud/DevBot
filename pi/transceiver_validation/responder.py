"""Motor-free Pi 4 endpoint for validating the DevBot Pico radio link."""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass

import protocol
import validation_config as config


ROBOT_READY = 2
ROBOT_FORWARD = 3
ROBOT_REVERSE = 4
ROBOT_TURN_LEFT = 5
ROBOT_TURN_RIGHT = 6


def direction_label(steer: int, throttle: int, active: bool) -> str:
    if not active:
        return "NEUTRAL"
    major = max(abs(steer), abs(throttle), 1)
    threshold = max(60, major // 3)
    vertical = ""
    horizontal = ""
    if abs(throttle) >= threshold:
        vertical = "FWD" if throttle > 0 else "REV"
    if abs(steer) >= threshold:
        horizontal = "RIGHT" if steer > 0 else "LEFT"
    if vertical and horizontal:
        return vertical + " " + horizontal
    return vertical or horizontal or "NEUTRAL"


def robot_state_for(steer: int, throttle: int, active: bool) -> int:
    """Collapse semantic direction into the v1 robot-state enumeration."""
    if not active:
        return ROBOT_READY
    if abs(throttle) >= abs(steer):
        return ROBOT_FORWARD if throttle > 0 else ROBOT_REVERSE
    return ROBOT_TURN_RIGHT if steer > 0 else ROBOT_TURN_LEFT


@dataclass
class Result:
    acknowledgement: bytes
    sequence: int
    session_id: int
    steer: int
    throttle: int
    active: bool
    direction: str


class ValidationResponder:
    """Pure protocol state; hardware is kept out so this can be unit tested."""

    def __init__(self) -> None:
        self.session_id: int | None = None
        self.last_sequence: int | None = None
        self.last_valid_receive_s: float | None = None
        self.accepted = 0
        self.rejected = 0
        self.reject_reasons: dict[str, int] = {}

    def _reject(self, reason: str) -> None:
        self.rejected += 1
        self.reject_reasons[reason] = self.reject_reasons.get(reason, 0) + 1

    def handle(self, payload: bytes, source: int, now_s: float) -> Result | None:
        if source != config.REMOTE_RADIO_ADDRESS:
            self._reject("source")
            return None
        try:
            command = protocol.unpack_control(
                payload, config.PROTOCOL_VERSION, config.PAIR_ID
            )
        except protocol.ProtocolError as exc:
            self._reject(exc.reason)
            return None

        session_id = command["session_id"]
        active = bool(command["flags"] & protocol.FLAG_ACTIVE)
        if session_id != self.session_id:
            # A new controller session is accepted only from a neutral frame.
            if active or command["steer"] != 0 or command["throttle"] != 0:
                self._reject("new_session_active")
                return None
            self.session_id = session_id
            self.last_sequence = None

        sequence = command["sequence"]
        if self.last_sequence is not None:
            if sequence == self.last_sequence:
                self._reject("duplicate")
                return None
            if not protocol.sequence_is_newer(sequence, self.last_sequence):
                self._reject("out_of_order")
                return None

        self.last_sequence = sequence
        self.last_valid_receive_s = now_s
        self.accepted += 1
        steer = command["steer"]
        throttle = command["throttle"]
        direction = direction_label(steer, throttle, active)
        acknowledgement = protocol.pack_ack(
            config.PROTOCOL_VERSION,
            config.PAIR_ID,
            session_id,
            sequence,
            robot_state_for(steer, throttle, active),
            0,  # No bumpers are connected for this validation test.
            0,  # No robot-side faults are simulated.
            int(now_s * 1000) & 0xFFFFFFFF,
        )
        return Result(
            acknowledgement, sequence, session_id, steer, throttle,
            active, direction,
        )


def probe_transceiver() -> None:
    """Probe before vendor construction to avoid its unbounded ready wait."""
    from PiicoDev_Unified import create_unified_i2c

    bus = create_unified_i2c(bus=config.I2C_BUS, suppress_warnings=True)
    try:
        raw = bytes(bus.readfrom_mem(config.TRANSCEIVER_I2C_ADDRESS, 0x01, 2))
    finally:
        close = getattr(getattr(bus, "i2c", None), "close", None)
        if close is not None:
            close()
    device_id = int.from_bytes(raw, "big")
    if device_id != config.TRANSCEIVER_DEVICE_ID:
        raise RuntimeError(
            "Expected PiicoDev transceiver ID {}, received {}".format(
                config.TRANSCEIVER_DEVICE_ID, device_id
            )
        )


def build_radio(tx_power: int):
    probe_transceiver()
    from PiicoDev_Transceiver import PiicoDev_Transceiver

    radio = PiicoDev_Transceiver(
        bus=config.I2C_BUS,
        i2c_address=config.TRANSCEIVER_I2C_ADDRESS,
        group=config.RADIO_GROUP,
        radio_address=config.ROBOT_RADIO_ADDRESS,
        speed=config.RADIO_SPEED,
        radio_frequency=config.RADIO_FREQUENCY,
        tx_power=tx_power,
        suppress_warnings=True,
    )
    if radio.whoami != config.TRANSCEIVER_DEVICE_ID:
        raise RuntimeError("PiicoDev transceiver identity check failed")
    return radio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Acknowledge DevBot Pico frames without Arduino or motors"
    )
    parser.add_argument(
        "--tx-power", type=int, default=config.RADIO_TX_POWER,
        choices=range(-2, 21), metavar="-2..20",
        help="Pi transceiver power in dBm (default: %(default)s)",
    )
    return parser.parse_args()


def run(tx_power: int) -> None:
    radio = build_radio(tx_power)
    responder = ValidationResponder()
    started = time.monotonic()
    next_health = started + config.HEALTH_PERIOD_SECONDS
    last_signature = None
    reported_lost = False
    print(
        "READY group={} radio={} destination={} frequency={}MHz speed={} tx_power={}dBm".format(
            config.RADIO_GROUP, config.ROBOT_RADIO_ADDRESS,
            config.REMOTE_RADIO_ADDRESS, config.RADIO_FREQUENCY,
            config.RADIO_SPEED, tx_power,
        )
    )
    print("Waiting for DevBot Pico control frames. Press Ctrl+C to stop.")

    try:
        while True:
            now = time.monotonic()
            try:
                received = radio.receive_bytes()
            except Exception as exc:
                print("RADIO ERROR receive={!r}".format(exc))
                time.sleep(1.0)
                continue

            if received:
                payload = bytes(radio.received_bytes)
                source = int(radio.source_radio_address)
                rssi = int(radio.rssi)
                result = responder.handle(payload, source, now - started)
                if result is not None:
                    try:
                        radio.send_bytes(
                            result.acknowledgement,
                            address=config.REMOTE_RADIO_ADDRESS,
                        )
                    except Exception as exc:
                        print("RADIO ERROR send={!r}".format(exc))
                        time.sleep(1.0)
                        continue
                    signature = (result.session_id, result.active, result.direction)
                    if signature != last_signature:
                        print(
                            "LINKED session={} seq={} dir={} steer={} throttle={} rssi={}dBm".format(
                                result.session_id, result.sequence,
                                result.direction, result.steer,
                                result.throttle, rssi,
                            )
                        )
                        last_signature = signature
                    reported_lost = False

            if now >= next_health:
                age = (
                    None if responder.last_valid_receive_s is None
                    else (now - started) - responder.last_valid_receive_s
                )
                if (age is not None and
                        age > config.LINK_REPORT_LOST_SECONDS and
                        not reported_lost):
                    print("LINK LOST: no valid Pico frame for {:.2f}s".format(age))
                    reported_lost = True
                    last_signature = None
                print(
                    "HEALTH accepted={} rejected={} last_age={} reasons={}".format(
                        responder.accepted, responder.rejected,
                        "none" if age is None else "{:.3f}s".format(age),
                        responder.reject_reasons,
                    )
                )
                next_health = now + config.HEALTH_PERIOD_SECONDS

            time.sleep(config.LOOP_SLEEP_SECONDS)
    except KeyboardInterrupt:
        print("\nStopped. No Arduino or motor commands were produced.")


def main() -> None:
    args = parse_args()
    try:
        run(args.tx_power)
    except (OSError, RuntimeError) as exc:
        raise SystemExit("STARTUP ERROR: {}".format(exc))


if __name__ == "__main__":
    main()
