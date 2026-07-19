# Arduino controller

The firmware is a PlatformIO Arduino project. `src/main.cpp` is the top-level state machine; vendor-specific or sizeable behavior lives under `src/` with public headers under `include/`.

## State flow

`BOOT -> DISABLED -> READY -> DRIVING_FORWARD/DRIVING_REVERSE`

Any bumper alert forces `OBSTACLE_STOP`. The stop remains latched until the minimum hold time has elapsed, all bumpers are released, and the joystick is neutral. Initialization errors enter `FAULT`.

The joystick push switch toggles enabled/disabled for this first scaffold. That mapping is intentionally easy to replace when the final joystick arrangement is known.

## LED layout

- 0-4: left motor group
- 5-11: middle mode group
- 12-16: right motor group

Motor groups use green for forward, red for reverse, amber for stationary, and blue for disabled. Middle LEDs identify overall state (boot purple, disabled blue, ready cyan, forward green, reverse red, obstacle magenta, fault orange).

