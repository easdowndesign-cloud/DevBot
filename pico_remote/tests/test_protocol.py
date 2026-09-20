import os
import struct
import sys
import unittest


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import protocol


class ProtocolTests(unittest.TestCase):
    def rebuild_crc(self, frame):
        frame = bytes(frame)
        return frame[:-2] + struct.pack(">H", protocol.crc16_ccitt(frame[:-2]))

    def test_crc_known_vector(self):
        self.assertEqual(protocol.crc16_ccitt(b"123456789"), 0x29B1)

    def test_control_round_trip(self):
        frame = protocol.pack_control(
            1, 0x44425631, 0x1234, 65535, 123456, -321, 987,
            protocol.FLAG_ACTIVE | protocol.FLAG_CENTRED_ONCE,
        )
        self.assertEqual(len(frame), protocol.CONTROL_LENGTH)
        decoded = protocol.unpack_control(frame, 1, 0x44425631)
        self.assertEqual(decoded["session_id"], 0x1234)
        self.assertEqual(decoded["sequence"], 65535)
        self.assertEqual(decoded["steer"], -321)
        self.assertEqual(decoded["throttle"], 987)

    def test_ack_round_trip(self):
        frame = protocol.pack_ack(1, 0x44425631, 7, 42, 3, 0x05, 0x02, 7654)
        self.assertEqual(len(frame), protocol.ACK_LENGTH)
        decoded = protocol.unpack_ack(frame, 1, 0x44425631, 7)
        self.assertEqual(decoded["ack_sequence"], 42)
        self.assertEqual(decoded["bumper_mask"], 0x05)

    def test_corruption_is_rejected(self):
        original = protocol.pack_ack(1, 0x44425631, 7, 42, 3, 0, 0, 10)
        for offset in (0, 2, 3, 4, 8, 10, 12, 13, 14, 16):
            frame = bytearray(original)
            frame[offset] ^= 0x01
            with self.assertRaisesRegex(protocol.ProtocolError, "crc"):
                protocol.unpack_ack(bytes(frame), 1, 0x44425631, 7)

    def test_wrong_control_identity_fields_are_rejected(self):
        original = bytearray(protocol.pack_control(1, 0x44425631, 7, 1, 10, 0, 0, 0))
        cases = ((0, "magic"), (2, "version"), (3, "type"), (4, "pairing"))
        for offset, reason in cases:
            frame = bytearray(original)
            frame[offset] ^= 0x01
            frame = self.rebuild_crc(frame)
            with self.assertRaisesRegex(protocol.ProtocolError, reason):
                protocol.unpack_control(frame, 1, 0x44425631)

    def test_wrong_ack_session_and_length_are_rejected(self):
        original = bytearray(protocol.pack_ack(1, 0x44425631, 7, 42, 3, 0, 0, 10))
        original[8] = 0
        original[9] = 8
        with self.assertRaisesRegex(protocol.ProtocolError, "session"):
            protocol.unpack_ack(self.rebuild_crc(original), 1, 0x44425631, 7)
        with self.assertRaisesRegex(protocol.ProtocolError, "length"):
            protocol.unpack_ack(bytes(original[:-1]), 1, 0x44425631, 7)

    def test_reserved_bits_and_invalid_state_are_rejected(self):
        with self.assertRaisesRegex(protocol.ProtocolError, "fault_flags"):
            protocol.pack_ack(1, 1, 1, 1, 1, 0, 0x20, 0)
        with self.assertRaisesRegex(protocol.ProtocolError, "robot_state"):
            protocol.pack_ack(1, 1, 1, 1, 9, 0, 0, 0)

    def test_inactive_frame_must_be_neutral(self):
        with self.assertRaisesRegex(protocol.ProtocolError, "inactive_axes"):
            protocol.pack_control(1, 1, 1, 1, 1, 1, 0, 0)

    def test_semantically_invalid_inactive_packet_is_rejected(self):
        body = struct.pack(
            protocol.CONTROL_FORMAT_NO_CRC,
            protocol.MAGIC, 1, protocol.CONTROL_TYPE, 0x44425631,
            2, 3, 4, 250, 0, protocol.FLAG_CENTRED_ONCE,
        )
        frame = body + struct.pack(">H", protocol.crc16_ccitt(body))
        with self.assertRaisesRegex(protocol.ProtocolError, "inactive_axes"):
            protocol.unpack_control(frame, 1, 0x44425631)

    def test_sequence_wrap_rules(self):
        self.assertTrue(protocol.sequence_is_newer(0, 65535))
        self.assertFalse(protocol.sequence_is_newer(65535, 0))
        self.assertFalse(protocol.sequence_is_newer(12, 12))
        self.assertFalse(protocol.sequence_is_newer(10, 11))
        self.assertTrue(protocol.sequence_was_transmitted(65535, 1))
        self.assertFalse(protocol.sequence_was_transmitted(2, 1))


if __name__ == "__main__":
    unittest.main()
