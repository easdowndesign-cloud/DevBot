"""Behavior tests for the receiver's hardware-independent model."""

from __future__ import annotations

import unittest

from receiver_core import decode_packet, direction, joystick_marker


class DirectionTests(unittest.TestCase):
    def test_centre(self) -> None:
        self.assertEqual(direction(32768, 32768), "CENTRE")

    def test_cardinal_directions(self) -> None:
        self.assertEqual(direction(50000, 32768), "LEFT")
        self.assertEqual(direction(10000, 32768), "RIGHT")
        self.assertEqual(direction(32768, 10000), "FWD")
        self.assertEqual(direction(32768, 50000), "REV")

    def test_diagonal_direction(self) -> None:
        self.assertEqual(direction(50000, 10000), "FWD LEFT")


class PacketTests(unittest.TestCase):
    def test_valid_packet(self) -> None:
        packet = decode_packet(1, b"J,42,50000,10000", -55, received_at=12.5)
        self.assertIsNotNone(packet)
        assert packet is not None
        self.assertEqual(packet.sequence, 42)
        self.assertEqual(packet.direction, "FWD LEFT")
        self.assertEqual(packet.rssi, -55)
        self.assertEqual(packet.received_at, 12.5)

    def test_wrong_source_and_bad_payload_are_ignored(self) -> None:
        self.assertIsNone(decode_packet(7, b"J,1,2,3", -80))
        self.assertIsNone(decode_packet(1, b"not-a-packet", -80))
        self.assertIsNone(decode_packet(1, b"J,1,70000,3", -80))

    def test_joystick_marker_is_clamped(self) -> None:
        self.assertEqual(joystick_marker(0, 0, 100), (100, -100))
        self.assertEqual(joystick_marker(65535, 65535, 100), (-100, 100))


if __name__ == "__main__":
    unittest.main()
