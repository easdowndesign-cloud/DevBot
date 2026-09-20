import os
import sys
import unittest


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import protocol
import validation_config as config
from responder import ValidationResponder, direction_label, robot_state_for


class ResponderTests(unittest.TestCase):
    def control(self, session=7, sequence=1, steer=0, throttle=0, active=False):
        flags = protocol.FLAG_CENTRED_ONCE
        if active:
            flags |= protocol.FLAG_ACTIVE
        return protocol.pack_control(
            config.PROTOCOL_VERSION, config.PAIR_ID, session, sequence,
            100, steer, throttle, flags,
        )

    def test_neutral_frame_establishes_session_and_is_acknowledged(self):
        responder = ValidationResponder()
        result = responder.handle(self.control(), config.REMOTE_RADIO_ADDRESS, 1.0)
        self.assertIsNotNone(result)
        ack = protocol.unpack_ack(
            result.acknowledgement, config.PROTOCOL_VERSION,
            config.PAIR_ID, 7,
        )
        self.assertEqual(ack["ack_sequence"], 1)
        self.assertEqual(ack["robot_state"], 2)
        self.assertEqual(ack["bumper_mask"], 0)

    def test_active_new_session_is_rejected(self):
        responder = ValidationResponder()
        result = responder.handle(
            self.control(steer=500, active=True),
            config.REMOTE_RADIO_ADDRESS, 1.0,
        )
        self.assertIsNone(result)
        self.assertEqual(responder.reject_reasons["new_session_active"], 1)

    def test_duplicate_out_of_order_and_wrong_source_are_rejected(self):
        responder = ValidationResponder()
        self.assertIsNotNone(responder.handle(
            self.control(sequence=10), config.REMOTE_RADIO_ADDRESS, 1.0
        ))
        self.assertIsNone(responder.handle(
            self.control(sequence=10), config.REMOTE_RADIO_ADDRESS, 1.1
        ))
        self.assertIsNone(responder.handle(
            self.control(sequence=9), config.REMOTE_RADIO_ADDRESS, 1.2
        ))
        self.assertIsNone(responder.handle(
            self.control(sequence=11), 99, 1.3
        ))

    def test_sequence_wrap_is_accepted(self):
        responder = ValidationResponder()
        self.assertIsNotNone(responder.handle(
            self.control(sequence=65535), config.REMOTE_RADIO_ADDRESS, 1.0
        ))
        self.assertIsNotNone(responder.handle(
            self.control(sequence=0), config.REMOTE_RADIO_ADDRESS, 1.1
        ))

    def test_direction_and_state_mapping(self):
        self.assertEqual(direction_label(700, 900, True), "FWD RIGHT")
        self.assertEqual(direction_label(-700, -900, True), "REV LEFT")
        self.assertEqual(robot_state_for(700, 900, True), 3)
        self.assertEqual(robot_state_for(-900, 200, True), 5)
        self.assertEqual(robot_state_for(0, 0, False), 2)


if __name__ == "__main__":
    unittest.main()

