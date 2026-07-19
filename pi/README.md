# Raspberry Pi supervisor

This package supplies the Pi-side state machine and hardware boundaries. It starts in mock mode on any development computer, so orchestration logic can be tested before the Pi, joystick mapping, or Arduino serial protocol is finalized.

`devbot_pi/app.py` owns the supervisor state machine. `hardware/` contains protocols and mock adapters. `input/` and `comms/` contain optional Linux/serial adapters. Hardware modules are lazily imported so basic tests do not require GPIO libraries.

The intended safety split is:

- Arduino: bumpers, motor stop, joystick fallback, drive and LED real-time state.
- Pi: high-level modes, telemetry, autonomy, UI/network integration, and command supervision.

