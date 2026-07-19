from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 compatibility
    import tomli as tomllib


@dataclass(frozen=True)
class AppConfig:
    tick_hz: float = 20.0
    heartbeat_timeout_s: float = 1.0
    serial_port: str = "/dev/ttyACM0"
    serial_baudrate: int = 115200

    @classmethod
    def from_toml(cls, path: Path) -> "AppConfig":
        with path.open("rb") as config_file:
            raw = tomllib.load(config_file)
        application = raw.get("application", {})
        serial = raw.get("serial", {})
        return cls(
            tick_hz=float(application.get("tick_hz", cls.tick_hz)),
            heartbeat_timeout_s=float(
                application.get("heartbeat_timeout_s", cls.heartbeat_timeout_s)
            ),
            serial_port=str(serial.get("port", cls.serial_port)),
            serial_baudrate=int(serial.get("baudrate", cls.serial_baudrate)),
        )
