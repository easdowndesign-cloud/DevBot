from devbot_pi.app import DevBotSupervisor
from devbot_pi.config import AppConfig
from devbot_pi.hardware.mock import MockArduinoLink
from devbot_pi.states import SupervisorState


async def test_mock_supervisor_stops_cleanly() -> None:
    link = MockArduinoLink()
    supervisor = DevBotSupervisor(AppConfig(tick_hz=200), link)

    await supervisor.run(run_seconds=0.02)

    assert supervisor.state is SupervisorState.SHUTDOWN
    assert link.stopped is True
    assert link.connected is False

