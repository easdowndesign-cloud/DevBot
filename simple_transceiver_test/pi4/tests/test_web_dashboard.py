"""Behavior tests for the headless browser-dashboard status model."""

from __future__ import annotations

import unittest

from receiver_core import ReceiverEvent, Telemetry
from serial_link import SerialEvent
from serial_protocol import ArduinoTelemetry
from web_dashboard import DevBotWebService


class WebDashboardStatusTests(unittest.TestCase):
    def test_remote_packet_updates_browser_snapshot_without_changing_direction(self) -> None:
        service = DevBotWebService()
        telemetry = Telemetry(
            sequence=42,
            raw_x=50000,
            raw_y=10000,
            direction="FWD LEFT",
            rssi=-55,
            received_at=10.0,
        )
        service.receiver_events.put(ReceiverEvent("telemetry", telemetry=telemetry))

        service.process_pending_events(now=10.1)
        remote = service.snapshot(now=10.1)["remote"]

        self.assertEqual(remote["direction"], "FWD LEFT")
        self.assertEqual(remote["raw_x"], 50000)
        self.assertTrue(remote["linked"])

    def test_arduino_telemetry_is_exposed_to_browser(self) -> None:
        service = DevBotWebService()
        telemetry = ArduinoTelemetry(
            acknowledged_sequence=23,
            state_id=7,
            state="TURNING_LEFT",
            applied_left=250,
            applied_right=-100,
            driver_enable_mask=3,
            bumper_mask=1,
            fault_mask=0,
        )
        service.serial_events.put(SerialEvent("telemetry", telemetry=telemetry))

        service.process_pending_events(now=10.0)
        arduino = service.snapshot(now=10.0)["arduino"]

        self.assertEqual(arduino["state"], "TURNING_LEFT")
        self.assertEqual(arduino["driver_enable_mask"], 3)
        self.assertEqual(arduino["bumper_mask"], 1)


if __name__ == "__main__":
    unittest.main()
