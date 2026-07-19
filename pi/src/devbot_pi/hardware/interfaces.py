from __future__ import annotations

from typing import Protocol


class ArduinoLink(Protocol):
    @property
    def connected(self) -> bool: ...

    async def connect(self) -> None: ...

    async def heartbeat(self) -> bool: ...

    async def safe_stop(self) -> None: ...

    async def close(self) -> None: ...

