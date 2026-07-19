from enum import Enum, auto


class SupervisorState(Enum):
    BOOT = auto()
    CONNECTING = auto()
    ACTIVE = auto()
    DEGRADED = auto()
    SHUTDOWN = auto()

