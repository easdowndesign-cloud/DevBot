import os
import sys
import unittest


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from joystick import ActivationLatch, AxisProcessor, NeutralHold, median3
from oled_view import direction_label


def ticks_diff(a, b):
    return a - b


class JoystickTests(unittest.TestCase):
    def test_direction_labels_include_diagonals(self):
        self.assertEqual(direction_label(0, 0, False), "CENTRE")
        self.assertEqual(direction_label(0, 800, True), "FWD")
        self.assertEqual(direction_label(0, -800, True), "REV")
        self.assertEqual(direction_label(-800, 0, True), "LEFT")
        self.assertEqual(direction_label(800, 0, True), "RIGHT")
        self.assertEqual(direction_label(700, 900, True), "FWD RIGHT")
        self.assertEqual(direction_label(-700, -900, True), "REV LEFT")

    def test_median_filter_helper(self):
        self.assertEqual(median3(2, 99, 3), 3)
        self.assertEqual(median3(9, 1, 5), 5)

    def test_asymmetric_normalization_and_deadband(self):
        axis = AxisProcessor(1000, 30000, 60000, 100, ema_alpha=1)
        self.assertEqual(axis.normalize(30000), 0)
        self.assertEqual(axis.normalize(31000), 0)
        self.assertEqual(axis.normalize(1000), -1000)
        self.assertEqual(axis.normalize(60000), 1000)

    def test_inversion(self):
        axis = AxisProcessor(0, 30000, 65535, 0, invert=True, ema_alpha=1)
        self.assertLess(axis.normalize(50000), 0)

    def test_single_sample_spike_is_rejected_by_median(self):
        axis = AxisProcessor(0, 32768, 65535, 70, ema_alpha=1)
        self.assertEqual(axis.process(65535), 0)
        self.assertEqual(axis.process(32768), 0)

    def test_processed_input_clamps_to_adc_and_command_ranges(self):
        axis = AxisProcessor(1000, 30000, 60000, 0, ema_alpha=1)
        axis.process(99999)
        axis.process(99999)
        self.assertEqual(axis.process(99999), 1000)
        axis.process(-100)
        axis.process(-100)
        self.assertEqual(axis.process(-100), -1000)

    def test_neutral_hold_requires_stable_full_duration(self):
        hold = NeutralHold(30000, 31000, 1000, 200, 500, ticks_diff)
        self.assertIsNone(hold.update(30000, 31000, 0))
        self.assertIsNone(hold.update(30050, 30950, 250))
        self.assertEqual(hold.update(30025, 31025, 500), (30025, 30991))

    def test_neutral_hold_resets_when_deflected(self):
        hold = NeutralHold(30000, 31000, 1000, 200, 500, ticks_diff)
        hold.update(30000, 31000, 0)
        self.assertIsNone(hold.update(33000, 31000, 400))
        self.assertIsNone(hold.update(30000, 31000, 500))
        self.assertEqual(hold.update(30000, 31000, 1000), (30000, 31000))

    def test_activation_hysteresis_and_release_hold(self):
        latch = ActivationLatch(60, 40, 100, ticks_diff)
        self.assertFalse(latch.update(59, 0, 0))
        self.assertTrue(latch.update(60, 0, 10))
        self.assertTrue(latch.update(20, 0, 20))
        self.assertTrue(latch.update(20, 0, 119))
        self.assertFalse(latch.update(20, 0, 120))


if __name__ == "__main__":
    unittest.main()
