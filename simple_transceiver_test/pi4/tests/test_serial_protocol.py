"""Behavior tests for the Pi 4 ↔ Mega serial contract."""

from __future__ import annotations

import unittest

from serial_protocol import (
    ArduinoTelemetry,
    ControlCommand,
    MegaHello,
    PROTOCOL_VERSION,
    build_control_frame,
    decode_frame,
    encode_frame,
    normalize_remote_axes,
    parse_mega_frame,
)


class CrcFrameTests(unittest.TestCase):
    def test_control_frame_round_trip(self) -> None:
        frame = build_control_frame(
            ControlCommand(
                frame_sequence=7,
                remote_sequence=42,
                remote_age_ms=18,
                enabled=True,
                steering=250,
                throttle=-500,
            )
        )
        self.assertEqual(
            decode_frame(frame),
            ["C", str(PROTOCOL_VERSION), "7", "42", "18", "1", "250", "-500"],
        )

    def test_corrupt_frame_is_rejected(self) -> None:
        frame = bytearray(
            encode_frame("H", PROTOCOL_VERSION, "DEVBOT_MEGA", "DRIVE_HW")
        )
        frame[0] = ord("X")
        self.assertIsNone(decode_frame(bytes(frame)))


class AxisTests(unittest.TestCase):
    def test_installed_robot_steering_polarity(self) -> None:
        self.assertEqual(normalize_remote_axes(32768, 32768), (0, 0))
        steering, throttle = normalize_remote_axes(10000, 10000)
        self.assertLess(steering, 0)  # physical right, reversed for the Mega
        self.assertGreater(throttle, 0)  # physical forward
        steering, throttle = normalize_remote_axes(50000, 50000)
        self.assertGreater(steering, 0)  # physical left, reversed for the Mega
        self.assertLess(throttle, 0)  # physical reverse


class MegaMessageTests(unittest.TestCase):
    def test_hello(self) -> None:
        message = parse_mega_frame(
            encode_frame("H", PROTOCOL_VERSION, "DEVBOT_MEGA", "DRIVE_HW")
        )
        self.assertIsInstance(message, MegaHello)
        assert isinstance(message, MegaHello)
        self.assertEqual(message.capability, "DRIVE_HW")

    def test_telemetry(self) -> None:
        message = parse_mega_frame(
            encode_frame("T", PROTOCOL_VERSION, 23, 7, 250, -100, 3, 0, 0)
        )
        self.assertIsInstance(message, ArduinoTelemetry)
        assert isinstance(message, ArduinoTelemetry)
        self.assertEqual(message.state, "TURNING_LEFT")
        self.assertEqual((message.applied_left, message.applied_right), (250, -100))
        self.assertEqual(message.driver_enable_mask, 3)

    def test_invalid_driver_enable_mask_is_rejected(self) -> None:
        frame = encode_frame(
            "T", PROTOCOL_VERSION, 23, 7, 250, -100, 4, 0, 0
        )
        self.assertIsNone(parse_mega_frame(frame))


if __name__ == "__main__":
    unittest.main()
