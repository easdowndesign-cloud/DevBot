from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JoystickEvent:
    code: int
    value: int


class EvdevJoystick:
    """Linux joystick discovery/stream adapter, isolated from supervisor policy."""

    def __init__(self, name_contains: str) -> None:
        self._name_contains = name_contains.casefold()
        self._device = None

    def connect(self) -> None:
        from evdev import InputDevice, list_devices

        devices = [InputDevice(path) for path in list_devices()]
        self._device = next(
            (device for device in devices if self._name_contains in device.name.casefold()), None
        )
        if self._device is None:
            raise RuntimeError(f"No input device contains {self._name_contains!r}")

    async def events(self):
        from evdev import ecodes

        if self._device is None:
            raise RuntimeError("Joystick is not connected")
        async for event in self._device.async_read_loop():
            if event.type in (ecodes.EV_ABS, ecodes.EV_KEY):
                yield JoystickEvent(code=event.code, value=event.value)

