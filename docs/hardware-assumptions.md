# Hardware assumptions and confirmation checklist

The code is safe-by-default but not ready for loaded-wheel testing until these items are confirmed.

## Assumed for the scaffold

- Arduino Mega 2560 so three dedicated external interrupt pins are available.
- DFRobot DFR0508 FireBeetle DC Motor & Stepper Driver at its first address selection.
- Two two-phase, four-wire stepper motors on groups SA and SB.
- One analogue joystick on A8/A9 and an active-low push switch on D22.
- Three normally-open bumpers wired from D2/D3/D18 to ground, using internal pull-ups.
- One 17-pixel, 5 V, GRB, 800 kHz addressable chain on D6.
- Physical pixel order: left motor 0-4, middle 5-11, right motor 12-16.

All values are centralized in `arduino/include/config/HardwareConfig.h`.

## Required confirmations

- [ ] Exact Arduino board/model and logic voltage
- [ ] Exact DFRobot product name and SKU
- [ ] Motor type, rated voltage/current, coil pairs, steps/revolution, and desired maximum RPM
- [ ] Whether motor groups/directions need swapping or inversion
- [ ] Joystick product, resting ADC readings, axis travel, axis inversion, and switch behavior
- [ ] Bumper physical positions (left/centre/right), wiring, and interrupt-capable pin availability
- [ ] LED chipset, RGB byte order, physical chain order, and acceptable brightness/current budget
- [ ] Independent motor/LED power supplies, common ground, fuse/kill switch, bulk capacitor, and data-line resistor/level shifting as appropriate
- [ ] Pi model, OS version, Arduino serial device path, and planned responsibility split

## First bench sequence

1. Disconnect motor power and verify joystick/button/LED telemetry.
2. Keep wheels raised, apply a conservative current/speed limit, and test each motor independently.
3. Confirm forward direction and correct any inversion flags in configuration.
4. Press every bumper while driving slowly and verify an immediate latched stop.
5. Measure LED and motor supply current before increasing brightness or speed.

