from __future__ import annotations


class MockArduinoLink:
    def __init__(self) -> None:
        self._connected = False
        self.stopped = False

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        self._connected = True

    async def heartbeat(self) -> bool:
        return self._connected

    async def safe_stop(self) -> None:
        self.stopped = True

    async def close(self) -> None:
        self._connected = False

