"""Graphical DevBot receiver dashboard for Raspberry Pi OS."""

from __future__ import annotations

import fcntl
import os
import queue
import time
import tkinter as tk
from tkinter import messagebox

from receiver_core import (
    LINK_TIMEOUT_SECONDS,
    RadioReceiver,
    ReceiverEvent,
    Telemetry,
    joystick_marker,
)
from serial_link import SerialControlBridge, SerialEvent
from serial_protocol import ArduinoTelemetry


BACKGROUND = "#0b1220"
PANEL = "#172033"
PANEL_ALT = "#101827"
TEXT = "#e5edf8"
MUTED = "#8fa3bd"
GRID = "#43526a"
BLUE = "#37a2ff"
GREEN = "#39d98a"
RED = "#ff5d73"
AMBER = "#ffbd4a"
CYAN = "#35d0d0"
PURPLE = "#a875ff"
MAGENTA = "#ff58b0"
ORANGE = "#ff8a3d"

LED_STATE_DISPLAY = {
    "BOOT": ("BOOT / PURPLE", PURPLE),
    "DISABLED": ("DISABLED / BLUE", BLUE),
    "AWAIT_NEUTRAL": ("AWAIT NEUTRAL / BLUE", BLUE),
    "READY": ("READY / CYAN", CYAN),
    "DRIVING_FORWARD": ("FORWARD / GREEN", GREEN),
    "DRIVING_REVERSE": ("REVERSE / RED", RED),
    "TURNING_LEFT": ("TURN LEFT / AMBER", AMBER),
    "TURNING_RIGHT": ("TURN RIGHT / AMBER", AMBER),
    "OBSTACLE_STOP": ("OBSTACLE / MAGENTA", MAGENTA),
    "COMMS_LOST": ("COMMS LOST / RED", RED),
    "FAULT": ("FAULT / ORANGE", ORANGE),
}


class Dashboard:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("DevBot Receiver")
        self.root.geometry("1180x760")
        self.root.minsize(950, 650)
        self.root.configure(bg=BACKGROUND)

        self.events: "queue.Queue[ReceiverEvent]" = queue.Queue(maxsize=100)
        self.serial_events: "queue.Queue[SerialEvent]" = queue.Queue(maxsize=500)
        self.receiver = RadioReceiver(self.events)
        self.serial_bridge = SerialControlBridge(self.serial_events)
        self.last_packet_at: float | None = None
        self.latest: Telemetry | None = None
        self.radio_state = "STARTING"
        self.serial_state = "STARTING"
        self.link_was_up = False

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Escape>", lambda _event: self.close())
        self.receiver.start()
        self.serial_bridge.start()
        self._append_log("SYS", "Dashboard started in full-hardware commissioning mode")
        self.root.after(50, self._tick)

    def _build_ui(self) -> None:
        header = tk.Frame(self.root, bg=BACKGROUND, padx=24, pady=18)
        header.pack(fill="x")
        tk.Label(
            header,
            text="DEVBOT RECEIVER",
            bg=BACKGROUND,
            fg=TEXT,
            font=("DejaVu Sans", 22, "bold"),
        ).pack(side="left")
        self.radio_label = tk.Label(
            header,
            text="RADIO STARTING",
            bg=PANEL,
            fg=AMBER,
            padx=14,
            pady=7,
            font=("DejaVu Sans", 10, "bold"),
        )
        self.radio_label.pack(side="right", padx=(10, 0))
        self.link_label = tk.Label(
            header,
            text="UNLINKED",
            bg=RED,
            fg="#ffffff",
            padx=18,
            pady=7,
            font=("DejaVu Sans", 12, "bold"),
        )
        self.link_label.pack(side="right")

        body = tk.Frame(self.root, bg=BACKGROUND, padx=24)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=4)
        body.grid_rowconfigure(0, weight=1)

        joystick_panel = self._panel(body, "REMOTE JOYSTICK")
        joystick_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        joystick_panel.grid_columnconfigure(0, weight=1)
        joystick_panel.grid_rowconfigure(1, weight=1)

        self.joystick_canvas = tk.Canvas(
            joystick_panel,
            width=330,
            height=330,
            bg=PANEL_ALT,
            highlightthickness=0,
        )
        self.joystick_canvas.grid(row=1, column=0, sticky="nsew", padx=16, pady=12)
        self.joystick_canvas.bind("<Configure>", lambda _event: self._draw_joystick())

        values = tk.Frame(joystick_panel, bg=PANEL)
        values.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))
        self.direction_var = tk.StringVar(value="CENTRE")
        self.raw_var = tk.StringVar(value="X -----    Y -----")
        tk.Label(
            values,
            textvariable=self.direction_var,
            bg=PANEL,
            fg=BLUE,
            font=("DejaVu Sans", 20, "bold"),
        ).pack()
        tk.Label(
            values,
            textvariable=self.raw_var,
            bg=PANEL,
            fg=MUTED,
            font=("DejaVu Sans Mono", 11),
        ).pack(pady=(4, 0))

        right = tk.Frame(body, bg=BACKGROUND)
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(2, weight=1)

        command_panel = self._panel(right, "COMMAND PATH")
        command_panel.grid(row=0, column=0, sticky="ew")
        self.request_var = tk.StringVar(value="Remote request: waiting")
        self.command_var = tk.StringVar(value="Arduino output: waiting for telemetry")
        self._value_label(command_panel, self.request_var, BLUE, row=1)
        self._value_label(command_panel, self.command_var, AMBER, row=2)

        indicators_panel = self._panel(right, "SYSTEM INDICATORS / FUTURE I/O")
        indicators_panel.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        self.indicators = {}
        indicator_defaults = (
            ("Remote link", "UNLINKED"),
            ("Robot link", "WAITING"),
            ("Control mode", "FULL HARDWARE TEST"),
            ("Arduino", "SEARCHING"),
            ("Motor drivers", "WAITING FOR TELEMETRY"),
            ("Bumpers / safety", "WAITING FOR TELEMETRY"),
            ("LED mode (commanded)", "WAITING FOR TELEMETRY"),
            ("Battery", "NOT AVAILABLE"),
        )
        for row, (name, value) in enumerate(indicator_defaults, start=1):
            indicators_panel.grid_columnconfigure(1, weight=1)
            tk.Label(
                indicators_panel,
                text=name,
                bg=PANEL,
                fg=MUTED,
                anchor="w",
                font=("DejaVu Sans", 10),
            ).grid(row=row, column=0, sticky="w", padx=16, pady=4)
            label = tk.Label(
                indicators_panel,
                text=value,
                bg=PANEL_ALT,
                fg=TEXT,
                anchor="e",
                padx=8,
                pady=3,
                font=("DejaVu Sans", 10, "bold"),
            )
            label.grid(row=row, column=1, sticky="ew", padx=16, pady=4)
            self.indicators[name] = label

        log_panel = self._panel(right, "USB SERIAL MONITOR — PI 4 ↔ ARDUINO")
        log_panel.grid(row=2, column=0, sticky="nsew", pady=(14, 0))
        log_panel.grid_columnconfigure(0, weight=1)
        log_panel.grid_rowconfigure(1, weight=1)
        self.log = tk.Text(
            log_panel,
            height=11,
            bg=PANEL_ALT,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            state="disabled",
            wrap="word",
            font=("DejaVu Sans Mono", 9),
            padx=8,
            pady=8,
        )
        self.log.grid(row=1, column=0, sticky="nsew", padx=16, pady=(8, 16))

        footer = tk.Frame(self.root, bg=BACKGROUND, padx=24, pady=12)
        footer.pack(fill="x")
        self.packet_var = tk.StringVar(value="No remote packets received")
        tk.Label(
            footer,
            textvariable=self.packet_var,
            bg=BACKGROUND,
            fg=MUTED,
            anchor="w",
            font=("DejaVu Sans", 9),
        ).pack(side="left")
        tk.Button(
            footer,
            text="QUIT RECEIVER",
            command=self.close,
            bg="#29364d",
            fg=TEXT,
            activebackground=RED,
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=6,
        ).pack(side="right")

    @staticmethod
    def _panel(parent: tk.Widget, title: str) -> tk.Frame:
        panel = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground="#26344a")
        tk.Label(
            panel,
            text=title,
            bg=PANEL,
            fg=MUTED,
            anchor="w",
            font=("DejaVu Sans", 10, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(13, 4))
        return panel

    @staticmethod
    def _value_label(parent: tk.Frame, variable: tk.StringVar, colour: str, row: int) -> None:
        tk.Label(
            parent,
            textvariable=variable,
            bg=PANEL_ALT,
            fg=colour,
            anchor="w",
            padx=12,
            pady=8,
            font=("DejaVu Sans Mono", 11, "bold"),
        ).grid(row=row, column=0, columnspan=2, sticky="ew", padx=16, pady=(4, 8))

    def _tick(self) -> None:
        self._drain_events()
        self._drain_serial_events()
        linked = (
            self.last_packet_at is not None
            and time.monotonic() - self.last_packet_at < LINK_TIMEOUT_SECONDS
        )
        self._set_link(linked)
        self._set_radio_state()
        self.root.after(50, self._tick)

    def _drain_events(self) -> None:
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                return
            if event.kind == "status":
                if event.detail != self.radio_state:
                    self.radio_state = event.detail
                    self._append_log("RADIO", event.detail.lower())
            elif event.kind == "error":
                self.radio_state = "ERROR"
                self._append_log("RADIO", "error: {}".format(event.detail))
            elif event.telemetry is not None:
                self._update_telemetry(event.telemetry)

    def _update_telemetry(self, telemetry: Telemetry) -> None:
        self.latest = telemetry
        self.serial_bridge.set_remote_telemetry(telemetry)
        self.last_packet_at = telemetry.received_at
        self.direction_var.set(telemetry.direction)
        self.raw_var.set("X {:5d}    Y {:5d}".format(telemetry.raw_x, telemetry.raw_y))
        self.request_var.set("Remote request: {}".format(telemetry.direction))
        self.packet_var.set(
            "Packet {:04d}   RSSI {} dBm   Group 73   Radio 1 -> 2".format(
                telemetry.sequence,
                telemetry.rssi,
            )
        )
        self._draw_joystick()

    def _set_link(self, linked: bool) -> None:
        if linked:
            self.link_label.configure(text="LINKED", bg=GREEN)
            self.indicators["Remote link"].configure(text="LINKED", fg=GREEN)
        else:
            self.link_label.configure(text="UNLINKED", bg=RED)
            self.indicators["Remote link"].configure(text="UNLINKED", fg=RED)
        if linked != self.link_was_up:
            self._append_log("RADIO", "linked" if linked else "link timed out")
            self.link_was_up = linked

    def _drain_serial_events(self) -> None:
        while True:
            try:
                event = self.serial_events.get_nowait()
            except queue.Empty:
                return

            if event.kind == "status":
                if event.detail != self.serial_state:
                    self.serial_state = event.detail
                    self._append_log("USB", event.detail)
                ready = event.detail == "READY"
                self.indicators["Arduino"].configure(
                    text=event.detail,
                    fg=GREEN if ready else AMBER,
                )
                self.indicators["Robot link"].configure(
                    text="SERIAL LINKED" if ready else "WAITING",
                    fg=GREEN if ready else AMBER,
                )
                if not ready:
                    self._mark_hardware_telemetry_unavailable()
            elif event.kind == "error":
                self.serial_state = "ERROR"
                self.indicators["Arduino"].configure(text="ERROR", fg=RED)
                self.indicators["Robot link"].configure(text="SERIAL LOST", fg=RED)
                self._mark_hardware_telemetry_unavailable()
                self._append_log("USB", "error: {}".format(event.detail))
            elif event.kind == "tx":
                self._append_log("TX >", event.raw)
            elif event.kind == "rx":
                self._append_log("RX <", event.raw)
            elif event.kind == "hello" and event.hello is not None:
                self.indicators["Arduino"].configure(
                    text="{} / {}".format(event.hello.device, event.hello.capability),
                    fg=GREEN,
                )
            elif event.kind == "telemetry" and event.telemetry is not None:
                self._update_arduino_telemetry(event.telemetry)

    def _update_arduino_telemetry(self, telemetry: ArduinoTelemetry) -> None:
        self.command_var.set(
            "Arduino output: {:<16} L {:+4d}  R {:+4d}".format(
                telemetry.state,
                telemetry.applied_left,
                telemetry.applied_right,
            )
        )
        driver_states = {
            0: "DISABLED",
            1: "LEFT ENABLED",
            2: "RIGHT ENABLED",
            3: "BOTH ENABLED",
        }
        self.indicators["Motor drivers"].configure(
            text=driver_states[telemetry.driver_enable_mask],
            fg=GREEN if telemetry.driver_enable_mask else TEXT,
        )

        bumper_names = [
            name
            for bit, name in ((1, "LEFT"), (2, "CENTRE"), (4, "RIGHT"))
            if telemetry.bumper_mask & bit
        ]
        if bumper_names:
            bumper_text = "ACTIVE: " + " + ".join(bumper_names)
            bumper_colour = RED
        elif telemetry.state == "OBSTACLE_STOP":
            bumper_text = "STOP LATCHED / RELEASED"
            bumper_colour = AMBER
        else:
            bumper_text = "RELEASED"
            bumper_colour = GREEN
        self.indicators["Bumpers / safety"].configure(
            text=bumper_text,
            fg=bumper_colour,
        )

        led_text, led_colour = LED_STATE_DISPLAY[telemetry.state]
        self.indicators["LED mode (commanded)"].configure(
            text=led_text,
            fg=led_colour,
        )
        if telemetry.fault_mask:
            self.indicators["Arduino"].configure(text="FAULT", fg=RED)

    def _mark_hardware_telemetry_unavailable(self) -> None:
        for name in ("Motor drivers", "Bumpers / safety", "LED mode (commanded)"):
            self.indicators[name].configure(text="NO TELEMETRY", fg=AMBER)

    def _set_radio_state(self) -> None:
        colours = {"READY": GREEN, "INITIALISING": AMBER, "ERROR": RED}
        self.radio_label.configure(
            text="RADIO {}".format(self.radio_state),
            fg=colours.get(self.radio_state, AMBER),
        )

    def _draw_joystick(self) -> None:
        canvas = self.joystick_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 100)
        height = max(canvas.winfo_height(), 100)
        cx = width // 2
        cy = height // 2
        radius = max(30, min(width, height) // 2 - 28)
        canvas.create_rectangle(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            outline=GRID,
            width=2,
        )
        canvas.create_line(cx - radius, cy, cx + radius, cy, fill=GRID)
        canvas.create_line(cx, cy - radius, cx, cy + radius, fill=GRID)
        canvas.create_text(cx, cy - radius - 13, text="FWD", fill=MUTED, font=("DejaVu Sans", 9))
        canvas.create_text(cx, cy + radius + 13, text="REV", fill=MUTED, font=("DejaVu Sans", 9))
        canvas.create_text(cx - radius - 18, cy, text="L", fill=MUTED, font=("DejaVu Sans", 9))
        canvas.create_text(cx + radius + 18, cy, text="R", fill=MUTED, font=("DejaVu Sans", 9))
        raw_x = 32768 if self.latest is None else self.latest.raw_x
        raw_y = 32768 if self.latest is None else self.latest.raw_y
        offset_x, offset_y = joystick_marker(raw_x, raw_y, radius)
        marker_x = cx + offset_x
        marker_y = cy + offset_y
        canvas.create_oval(
            marker_x - 9,
            marker_y - 9,
            marker_x + 9,
            marker_y + 9,
            fill=BLUE,
            outline="#b9e1ff",
            width=2,
        )

    def _append_log(self, source: str, text: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log.configure(state="normal")
        self.log.insert("end", "{}  {:<5} {}\n".format(timestamp, source, text))
        line_count = int(self.log.index("end-1c").split(".")[0])
        if line_count > 300:
            self.log.delete("1.0", "50.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def close(self) -> None:
        self.receiver.stop()
        self.serial_bridge.stop()
        self.receiver.join(timeout=1.0)
        self.serial_bridge.join(timeout=1.0)
        self.root.destroy()


def main() -> int:
    lock_path = "/tmp/devbot_receiver_{}.lock".format(os.getuid())
    lock_file = open(lock_path, "w", encoding="utf-8")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        duplicate = tk.Tk()
        duplicate.withdraw()
        messagebox.showinfo("DevBot Receiver", "The DevBot Receiver dashboard is already running.")
        duplicate.destroy()
        return 0

    root = tk.Tk()
    Dashboard(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
