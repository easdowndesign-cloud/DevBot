"""Headless local web dashboard for the DevBot receiver and Arduino bridge."""

from __future__ import annotations

import json
import os
import queue
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from receiver_core import LINK_TIMEOUT_SECONDS, RadioReceiver, ReceiverEvent, Telemetry
from serial_link import SerialControlBridge, SerialEvent


WEB_HOST = "0.0.0.0"
WEB_PORT = 8080
EVENT_INTERVAL_SECONDS = 0.05
MAX_LOG_ENTRIES = 250
INDEX_PATH = Path(__file__).with_name("web") / "index.html"


@dataclass
class RemoteStatus:
    radio_state: str = "STARTING"
    linked: bool = False
    packet_received: bool = False
    sequence: int = 0
    raw_x: int = 32768
    raw_y: int = 32768
    direction: str = "CENTRE"
    rssi: int = 0
    age_ms: int | None = None


@dataclass
class ArduinoStatus:
    serial_state: str = "STARTING"
    linked: bool = False
    device: str = ""
    capability: str = ""
    telemetry_received: bool = False
    state: str = "WAITING"
    applied_left: int = 0
    applied_right: int = 0
    driver_enable_mask: int = 0
    bumper_mask: int = 0
    fault_mask: int = 0


@dataclass(frozen=True)
class LogEntry:
    entry_id: int
    timestamp: str
    source: str
    text: str


class DevBotWebService:
    """Own the proven hardware workers and expose a thread-safe status snapshot."""

    def __init__(self) -> None:
        self.receiver_events: "queue.Queue[ReceiverEvent]" = queue.Queue(maxsize=100)
        self.serial_events: "queue.Queue[SerialEvent]" = queue.Queue(maxsize=500)
        self.receiver = RadioReceiver(self.receiver_events)
        self.serial_bridge = SerialControlBridge(self.serial_events)
        self.remote = RemoteStatus()
        self.arduino = ArduinoStatus()
        self.logs: deque[LogEntry] = deque(maxlen=MAX_LOG_ENTRIES)
        self.stop_requested = threading.Event()
        self.worker = threading.Thread(
            target=self._event_loop,
            name="devbot-web-events",
            daemon=True,
        )
        self.lock = threading.Lock()
        self.last_packet_at: float | None = None
        self.link_was_up = False
        self.next_log_id = 1

    def start(self) -> None:
        self._append_log("SYS", "Headless web dashboard started")
        self.receiver.start()
        self.serial_bridge.start()
        self.worker.start()

    def stop(self) -> None:
        self.stop_requested.set()
        self.receiver.stop()
        self.serial_bridge.stop()
        self.worker.join(timeout=1.0)
        self.receiver.join(timeout=1.0)
        self.serial_bridge.join(timeout=1.0)

    def snapshot(self, now: float | None = None) -> dict[str, object]:
        current_time = time.monotonic() if now is None else now
        with self.lock:
            if self.last_packet_at is None:
                self.remote.age_ms = None
            else:
                self.remote.age_ms = max(
                    0,
                    round((current_time - self.last_packet_at) * 1000),
                )
            return {
                "remote": asdict(self.remote),
                "arduino": asdict(self.arduino),
                "logs": [asdict(entry) for entry in self.logs],
            }

    def process_pending_events(self, now: float | None = None) -> None:
        """Drain queued hardware events and refresh the browser-facing state."""
        current_time = time.monotonic() if now is None else now
        self._drain_receiver_events()
        self._drain_serial_events()
        with self.lock:
            linked = (
                self.last_packet_at is not None
                and current_time - self.last_packet_at < LINK_TIMEOUT_SECONDS
            )
            self.remote.linked = linked
        if linked != self.link_was_up:
            self._append_log("RADIO", "linked" if linked else "link timed out")
            self.link_was_up = linked

    def _event_loop(self) -> None:
        while not self.stop_requested.wait(EVENT_INTERVAL_SECONDS):
            self.process_pending_events()

    def _drain_receiver_events(self) -> None:
        while True:
            try:
                event = self.receiver_events.get_nowait()
            except queue.Empty:
                return
            if event.kind == "status":
                with self.lock:
                    changed = event.detail != self.remote.radio_state
                    self.remote.radio_state = event.detail
                if changed:
                    self._append_log("RADIO", event.detail.lower())
            elif event.kind == "error":
                with self.lock:
                    self.remote.radio_state = "ERROR"
                self._append_log("RADIO", "error: {}".format(event.detail))
            elif event.telemetry is not None:
                self._accept_remote_telemetry(event.telemetry)

    def _accept_remote_telemetry(self, telemetry: Telemetry) -> None:
        self.serial_bridge.set_remote_telemetry(telemetry)
        with self.lock:
            self.last_packet_at = telemetry.received_at
            self.remote.packet_received = True
            self.remote.sequence = telemetry.sequence
            self.remote.raw_x = telemetry.raw_x
            self.remote.raw_y = telemetry.raw_y
            self.remote.direction = telemetry.direction
            self.remote.rssi = telemetry.rssi

    def _drain_serial_events(self) -> None:
        while True:
            try:
                event = self.serial_events.get_nowait()
            except queue.Empty:
                return
            if event.kind == "status":
                with self.lock:
                    changed = event.detail != self.arduino.serial_state
                    self.arduino.serial_state = event.detail
                    self.arduino.linked = event.detail == "READY"
                if changed:
                    self._append_log("USB", event.detail)
            elif event.kind == "error":
                with self.lock:
                    self.arduino.serial_state = "ERROR"
                    self.arduino.linked = False
                self._append_log("USB", "error: {}".format(event.detail))
            elif event.kind == "tx":
                self._append_log("TX >", event.raw)
            elif event.kind == "rx":
                self._append_log("RX <", event.raw)
            elif event.kind == "hello" and event.hello is not None:
                with self.lock:
                    self.arduino.device = event.hello.device
                    self.arduino.capability = event.hello.capability
            elif event.kind == "telemetry" and event.telemetry is not None:
                telemetry = event.telemetry
                with self.lock:
                    self.arduino.telemetry_received = True
                    self.arduino.state = telemetry.state
                    self.arduino.applied_left = telemetry.applied_left
                    self.arduino.applied_right = telemetry.applied_right
                    self.arduino.driver_enable_mask = telemetry.driver_enable_mask
                    self.arduino.bumper_mask = telemetry.bumper_mask
                    self.arduino.fault_mask = telemetry.fault_mask

    def _append_log(self, source: str, text: str) -> None:
        with self.lock:
            entry = LogEntry(
                entry_id=self.next_log_id,
                timestamp=time.strftime("%H:%M:%S"),
                source=source,
                text=text,
            )
            self.logs.append(entry)
            self.next_log_id += 1


class DashboardHttpServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class DashboardRequestHandler(BaseHTTPRequestHandler):
    dashboard: DevBotWebService
    index_path: Path
    server_version = "DevBotDashboard/1"

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path in ("/", "/index.html"):
            try:
                content = self.index_path.read_bytes()
            except OSError as error:
                self.send_error(500, "Dashboard file unavailable: {}".format(error))
                return
            self._send(content, "text/html; charset=utf-8")
            return
        if path == "/api/status":
            content = json.dumps(
                self.dashboard.snapshot(),
                separators=(",", ":"),
            ).encode("utf-8")
            self._send(content, "application/json; charset=utf-8")
            return
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        self.send_error(404)

    def _send(self, content: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, _format: str, *_args: object) -> None:
        # The browser polls frequently; access logs would bury hardware events.
        return


def main() -> int:
    import fcntl

    lock_path = "/tmp/devbot_receiver_{}.lock".format(os.getuid())
    lock_file = open(lock_path, "w", encoding="utf-8")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("Another DevBot dashboard already owns the radio or serial port.")
        return 1

    service = DevBotWebService()
    DashboardRequestHandler.dashboard = service
    DashboardRequestHandler.index_path = INDEX_PATH
    try:
        server = DashboardHttpServer((WEB_HOST, WEB_PORT), DashboardRequestHandler)
    except OSError as error:
        print("Could not listen on port {}: {}".format(WEB_PORT, error))
        return 1

    service.start()
    print("DevBot web dashboard: http://devbot.local:{}".format(WEB_PORT))
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        service.stop()
        lock_file.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
