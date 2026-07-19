# Hardware assumptions and confirmation checklist

The code is safe-by-default but not ready for loaded-wheel testing until these items are confirmed.

## Assumed for the scaffold

- Arduino Mega 2560 so three dedicated external interrupt pins are available.
- DFRobot DRI0023 Dual Bipolar Stepper Motor Shield (two DRV8825 channels).
- Two two-phase, four-wire bipolar stepper motors on shield channels M1 and M2.
- One analogue joystick on A8/A9 and an active-low push switch on D22.
- Three normally-open bumpers wired from D2/D3/D18 to ground, using internal pull-ups.
- DRI0023 fixed pins: M1 DIR D7, STEP D6, ENABLE D8; M2 DIR D4, STEP D5, ENABLE D12.
- One 17-pixel, 5 V, GRB, 800 kHz addressable chain on D9. D6 cannot be used because it is M1 STEP.
- Physical pixel order: left motor 0-4, middle 5-11, right motor 12-16.

All values are centralized in `arduino/include/config/HardwareConfig.h`.

## Required confirmations

- [ ] Motor type, rated voltage/current, coil pairs, steps/revolution, and desired maximum RPM
- [ ] DRV8825 current limit adjusted for the motors before connecting them
- [ ] Physical microstep DIP-switch positions recorded; software speed is in emitted microsteps/second
- [ ] Whether motor groups/directions need swapping or inversion
- [ ] Joystick product, resting ADC readings, axis travel, axis inversion, and switch behavior
- [ ] Bumper physical positions (left/centre/right), wiring, and interrupt-capable pin availability
- [ ] LED chipset, RGB byte order, physical chain order, and acceptable brightness/current budget
- [ ] Independent motor/LED power supplies, common ground, fuse/kill switch, bulk capacitor, and data-line resistor/level shifting as appropriate
- [ ] Pi model, OS version, Arduino serial device path, and planned responsibility split

## First bench sequence

1. Disconnect motor power and verify joystick/button/LED telemetry.
2. Set the DRV8825 current limit with motor power off during wiring, then keep wheels raised and test each motor independently at conservative speed.
3. Confirm forward direction and correct any inversion flags in configuration.
4. Press every bumper while driving slowly and verify an immediate latched stop.
5. Measure LED and motor supply current before increasing brightness or speed.
