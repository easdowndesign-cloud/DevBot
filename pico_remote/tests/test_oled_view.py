import os
import sys
import unittest


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from oled_view import OledView


class FakeDisplay:
    def __init__(self):
        self.comms_err = False
        self.calls = []

    def fill(self, *args):
        self.calls.append(("fill", args))

    def text(self, *args):
        self.calls.append(("text", args))

    def rect(self, *args):
        self.calls.append(("rect", args))

    def hline(self, *args):
        self.calls.append(("hline", args))

    def vline(self, *args):
        self.calls.append(("vline", args))

    def fill_rect(self, *args):
        self.calls.append(("fill_rect", args))

    def show(self):
        self.calls.append(("show", ()))


def snapshot(**overrides):
    result = {
        "state": "ACTIVE", "link": "OK", "robot_state": 3,
        "steer": 500, "throttle": 800, "active": True,
        "bumper_mask": 0, "fault_flags": 0, "startup_step": 6,
        "adc_ok": True, "oled_ok": True, "radio_ok": True,
    }
    result.update(overrides)
    return result


class OledViewTests(unittest.TestCase):
    def setUp(self):
        self.view = OledView()
        self.view.display = FakeDisplay()
        self.view.operational = True

    def test_main_view_draws_link_direction_crosshair_and_marker(self):
        self.assertTrue(self.view.render(snapshot()))
        calls = self.view.display.calls
        text_values = [call[1][0] for call in calls if call[0] == "text"]
        self.assertIn("LINKED ACTIVE", text_values)
        self.assertIn("DIR FWD RIGHT", text_values)
        self.assertTrue(any(call[0] == "rect" for call in calls))
        self.assertTrue(any(call[0] == "fill_rect" for call in calls))
        self.assertEqual(calls[-1][0], "show")

    def test_unchanged_snapshot_is_not_redrawn(self):
        value = snapshot(state="READY", steer=0, throttle=0, active=False)
        self.assertTrue(self.view.render(value))
        call_count = len(self.view.display.calls)
        self.assertFalse(self.view.render(value))
        self.assertEqual(len(self.view.display.calls), call_count)


if __name__ == "__main__":
    unittest.main()

