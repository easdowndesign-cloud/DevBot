from __future__ import annotations

import asyncio
import logging
from time import monotonic

from devbot_pi.config import AppConfig
from devbot_pi.hardware.interfaces import ArduinoLink
from devbot_pi.states import SupervisorState

LOGGER = logging.getLogger(__name__)


class DevBotSupervisor:
    def __init__(self, config: AppConfig, arduino: ArduinoLink) -> None:
        self.config = config
        self.arduino = arduino
        self.state = SupervisorState.BOOT
        self._running = False
        self._last_heartbeat = 0.0

    def transition(self, next_state: SupervisorState) -> None:
        if next_state is self.state:
            return
        LOGGER.info("state %s -> %s", self.state.name, next_state.name)
        self.state = next_state

    async def run(self, run_seconds: float | None = None) -> None:
        self._running = True
        started = monotonic()
        tick_seconds = 1.0 / self.config.tick_hz

        try:
            while self._running:
                if run_seconds is not None and monotonic() - started >= run_seconds:
                    self.transition(SupervisorState.SHUTDOWN)

                # Top-level Pi state machine. Hardware operations stay behind ArduinoLink.
                if self.state is SupervisorState.BOOT:
                    self.transition(SupervisorState.CONNECTING)

                elif self.state is SupervisorState.CONNECTING:
                    try:
                        await self.arduino.connect()
                    except (OSError, RuntimeError):
                        LOGGER.exception("Arduino connection failed")
                        self.transition(SupervisorState.DEGRADED)
                    else:
                        self._last_heartbeat = monotonic()
                        self.transition(SupervisorState.ACTIVE)

                elif self.state is SupervisorState.ACTIVE:
                    if await self.arduino.heartbeat():
                        self._last_heartbeat = monotonic()
                    elif monotonic() - self._last_heartbeat > self.config.heartbeat_timeout_s:
                        await self.arduino.safe_stop()
                        self.transition(SupervisorState.DEGRADED)

                elif self.state is SupervisorState.DEGRADED:
                    await self.arduino.safe_stop()
                    await self.arduino.close()
                    self.transition(SupervisorState.CONNECTING)

                elif self.state is SupervisorState.SHUTDOWN:
                    self._running = False

                await asyncio.sleep(tick_seconds)
        finally:
            await self.arduino.safe_stop()
            await self.arduino.close()
            self.transition(SupervisorState.SHUTDOWN)

    def request_shutdown(self) -> None:
        self.transition(SupervisorState.SHUTDOWN)

