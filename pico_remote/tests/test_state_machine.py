import os
import sys
import unittest


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import config
import protocol
from diagnostics import Diagnostics
from joystick import ActivationLatch, AxisProcessor, JoystickSample, NeutralHold
from remote_controller import ACTIVE, LINK_LOST, READY, UNLINKED, WAIT_NEUTRAL, RemoteController


def ticks_diff(a, b):
    return a - b


def ticks_add(a, b):
    return a + b


class FakeAxis:
    def __init__(self):
        self.centre = 32768

    def set_session_centre(self, centre):
        self.centre = centre


class FakeJoystick:
    def __init__(self):
        self.x_axis = FakeAxis()
        self.y_axis = FakeAxis()
        self.value = JoystickSample(32768, 32768, 0, 0)

    def sample(self):
        return self.value


class FakeRadio:
    def __init__(self):
        self.operational = False
        self.sent = []
        self.pending = []
        self.fail_sends = False
        self.fail_initialize = False

    def initialize(self):
        if self.fail_initialize:
            raise OSError("simulated radio init fault")
        self.operational = True

    def mark_failed(self):
        self.operational = False

    def send(self, payload):
        if self.fail_sends:
            raise OSError("simulated send fault")
        self.sent.append(payload)

    def receive_pending(self, maximum):
        result = self.pending[:maximum]
        del self.pending[:maximum]
        return result


class FakeOled:
    def __init__(self):
        self.operational = False
        self.snapshots = []
        self.fail_initialize = False

    def initialize(self):
        if self.fail_initialize:
            raise OSError("simulated OLED init fault")
        self.operational = True

    def mark_failed(self):
        self.operational = False

    def render(self, snapshot):
        self.snapshots.append(snapshot)


class StateMachineTests(unittest.TestCase):
    def make_controller(self, radio=None, oled=None):
        radio = radio or FakeRadio()
        oled = oled or FakeOled()
        controller = RemoteController(
            self.joystick,
            NeutralHold(32768, 32768, 3500, 1400, 500, ticks_diff),
            ActivationLatch(60, 40, 100, ticks_diff),
            radio, oled, Diagnostics(False), 0x1234,
            ticks_diff, ticks_add,
        )
        return controller, radio, oled

    def setUp(self):
        self.joystick = FakeJoystick()
        self.controller, self.radio, self.oled = self.make_controller()
        self.controller.start(0)

    def run_cycles(self, start, end, step=10):
        for now in range(start, end + 1, step):
            self.controller.cycle(now)

    def queue_ack(self, now, sequence=None):
        if sequence is None:
            sequence = self.controller.last_tx_sequence
        frame = protocol.pack_ack(
            config.PROTOCOL_VERSION, config.PAIR_ID,
            self.controller.session_id, sequence, 2, 0, 0, now,
        )
        self.radio.pending.append((frame, config.ROBOT_RADIO_ADDRESS, -55))

    def latest_control(self):
        return protocol.unpack_control(
            self.radio.sent[-1], config.PROTOCOL_VERSION, config.PAIR_ID
        )

    def test_startup_neutral_then_ack_enables_commands(self):
        self.assertEqual(self.controller.state, "SELF TEST")
        self.run_cycles(0, 1100)
        self.assertEqual(self.controller.state, UNLINKED)
        self.assertEqual(self.latest_control()["steer"], 0)

        self.queue_ack(1110)
        self.controller.cycle(1110)
        self.assertEqual(self.controller.state, READY)

        self.joystick.value = JoystickSample(40000, 32768, 250, 0)
        self.controller.cycle(1120)
        self.assertEqual(self.controller.state, ACTIVE)
        control = self.latest_control()
        self.assertEqual(control["steer"], 250)
        self.assertTrue(control["flags"] & protocol.FLAG_ACTIVE)

    def test_link_loss_forces_neutral_and_requires_recentering(self):
        self.run_cycles(0, 1100)
        self.queue_ack(1110)
        self.controller.cycle(1110)
        self.joystick.value = JoystickSample(40000, 32768, 250, 0)
        self.controller.cycle(1120)
        self.assertEqual(self.controller.state, ACTIVE)

        self.controller.cycle(1620)
        self.assertEqual(self.controller.state, LINK_LOST)
        control = self.latest_control()
        self.assertEqual((control["steer"], control["throttle"]), (0, 0))
        self.assertFalse(control["flags"] & protocol.FLAG_ACTIVE)

        self.queue_ack(1630)
        self.controller.cycle(1630)
        self.assertEqual(self.controller.state, WAIT_NEUTRAL)
        self.joystick.value = JoystickSample(40000, 32768, 250, 0)
        self.run_cycles(1640, 2200)
        self.assertEqual(self.controller.state, WAIT_NEUTRAL)

    def test_duplicate_ack_does_not_refresh_link_timer(self):
        self.run_cycles(0, 1100)
        self.queue_ack(1110)
        self.controller.cycle(1110)
        accepted_at = self.controller.last_valid_ack_ms
        duplicate_sequence = self.controller.last_ack_sequence
        self.queue_ack(1300, duplicate_sequence)
        self.controller.cycle(1300)
        self.assertEqual(self.controller.last_valid_ack_ms, accepted_at)
        self.assertEqual(self.controller.diagnostics.counters["reject_sequence"], 1)

    def test_boot_with_deflected_stick_never_completes_interlock(self):
        self.joystick.value = JoystickSample(45000, 32768, 400, 0)
        self.run_cycles(0, 1800)
        self.assertEqual(self.controller.state, WAIT_NEUTRAL)
        self.assertFalse(self.controller.centred_once)
        self.assertTrue(all(
            protocol.unpack_control(
                frame, config.PROTOCOL_VERSION, config.PAIR_ID
            )["steer"] == 0 for frame in self.radio.sent
        ))

    def test_neutral_hold_release_returns_active_to_ready(self):
        self.run_cycles(0, 1100)
        self.queue_ack(1110)
        self.controller.cycle(1110)
        self.joystick.value = JoystickSample(40000, 32768, 250, 0)
        self.controller.cycle(1120)
        self.assertEqual(self.controller.state, ACTIVE)
        self.joystick.value = JoystickSample(32768, 32768, 0, 0)
        self.controller.cycle(1130)
        self.controller.cycle(1230)
        self.assertEqual(self.controller.state, READY)

    def test_three_transmit_exceptions_enter_fault(self):
        self.radio.fail_sends = True
        self.controller.cycle(0)
        self.controller.cycle(20)
        self.controller.cycle(40)
        self.assertEqual(self.controller.state, "FAULT")
        self.assertFalse(self.radio.operational)

    def test_radio_fault_retries_then_requires_neutral(self):
        self.radio.fail_sends = True
        self.controller.cycle(0)
        self.controller.cycle(20)
        self.controller.cycle(40)
        self.radio.fail_sends = False
        self.controller.cycle(config.PERIPHERAL_RETRY_MS)
        self.assertEqual(self.controller.state, WAIT_NEUTRAL)
        self.assertTrue(self.radio.operational)

    def test_radio_initialization_failure_is_critical(self):
        radio = FakeRadio()
        radio.fail_initialize = True
        controller, _radio, _oled = self.make_controller(radio=radio)
        controller.start(0)
        self.assertEqual(controller.state, "FAULT")
        self.assertFalse(controller.centred_once)

    def test_oled_initialization_failure_is_degraded_only(self):
        oled = FakeOled()
        oled.fail_initialize = True
        controller, radio, _oled = self.make_controller(oled=oled)
        controller.start(0)
        self.assertEqual(controller.state, "SELF TEST")
        self.assertTrue(controller.display_degraded)
        controller.cycle(0)
        control = protocol.unpack_control(
            radio.sent[-1], config.PROTOCOL_VERSION, config.PAIR_ID
        )
        self.assertTrue(control["flags"] & protocol.FLAG_DISPLAY_DEGRADED)

    def test_reconnect_with_neutral_hold_returns_ready(self):
        self.run_cycles(0, 1100)
        self.queue_ack(1110)
        self.controller.cycle(1110)
        self.joystick.value = JoystickSample(40000, 32768, 250, 0)
        self.controller.cycle(1120)
        self.controller.cycle(1620)
        self.queue_ack(1630)
        self.controller.cycle(1630)
        self.joystick.value = JoystickSample(32768, 32768, 0, 0)
        for now in range(1640, 2150, 10):
            if now % 100 == 0:
                self.queue_ack(now)
            self.controller.cycle(now)
        self.assertEqual(self.controller.state, READY)
        self.assertFalse(self.controller.link_recovery)


if __name__ == "__main__":
    unittest.main()
