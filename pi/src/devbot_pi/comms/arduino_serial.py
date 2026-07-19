from __future__ import annotations

import asyncio
import serial


class SerialArduinoLink:
    """Minimal serial boundary; finalize commands after the Arduino protocol is agreed."""

    def __init__(self, port: str, baudrate: int) -> None:
        self._port = port
        self._baudrate = baudrate
        self._serial: serial.Serial | None = None

    @property
    def connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    async def connect(self) -> None:
        self._serial = await asyncio.to_thread(
            serial.Serial, self._port, self._baudrate, timeout=0.2, write_timeout=0.2
        )

    async def heartbeat(self) -> bool:
        # Protocol placeholder: port health only. Replace with PING/PONG sequence numbers.
        return self.connected

    async def safe_stop(self) -> None:
        if self.connected:
            assert self._serial is not None
            await asyncio.to_thread(self._serial.write, b"STOP\n")

    async def close(self) -> None:
        if self._serial is not None:
            await asyncio.to_thread(self._serial.close)
            self._serial = None

