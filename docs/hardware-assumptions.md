# Hardware assumptions and confirmation checklist

The code is safe-by-default but not ready for loaded-wheel testing until these items are confirmed.

## Assumed for the scaffold

- Arduino Mega 2560, using D2/D3 external interrupts plus D10's pin-change interrupt for the three bumpers.
- DFRobot DRI0023 Dual Bipolar Stepper Motor Shield (two DRV8825 channels).
- Two two-phase, four-wire bipolar stepper motors on shield channels M1 and M2.
- One joystick with analogue position on A4/A5 and analogue activation signals on A2/A3. The activation readings are approximately 512 inactive and 1023 active; 800/700 ADC hysteresis gates both motor enables.
- Three normally-open bumpers wired from D2/D3/D10 to ground, using internal pull-ups. D2/D3 use standard external interrupts and D10 uses the Mega's PCINT4 pin-change interrupt.
- DRI0023 fixed pins: M1 DIR D7, STEP D6, ENABLE D8; M2 DIR D4, STEP D5, ENABLE D12.
- Both DRI0023 microstep banks are set to MS1 HIGH, MS2 HIGH, MS3 LOW (1/8 step), only while power is removed.
- Each SY42STH38-1684A motor is assumed to be 1.8 degrees/200 full steps per revolution: 1,600 pulses/revolution at 1/8 step.
- Firmware ramps at 5,000 pulses/s^2 to a 4,000 pulses/s ceiling (approximately 150 shaft RPM).
- One 18-pixel, 5 V, GRB, 800 kHz addressable chain on D9. D6 cannot be used because it is M1 STEP.
- Rear-view logical pixel groups: middle 0-7, right motor 8-12, left motor 13-17.

All values are centralized in `arduino/include/config/HardwareConfig.h`.

## Required confirmations

- [ ] Motor type, rated voltage/current, coil pairs, steps/revolution, and desired maximum RPM
- [ ] DRV8825 current limit adjusted for the motors before connecting them
- [ ] Both physical microstep DIP banks confirmed at 1/8 step before power-up
- [x] Rear-mounted LED motor groups swapped so physical left/right matches the robot
- [ ] Confirm both activation channels remain below 700 ADC at rest and rise above 800 ADC when active
- [ ] Bumper physical positions (left/centre/right) and D10 PCINT response on the physical robot
- [ ] LED chipset, RGB byte order, physical chain order, and acceptable brightness/current budget
- [ ] Independent motor/LED power supplies, common ground, fuse/kill switch, bulk capacitor, and data-line resistor/level shifting as appropriate
- [ ] Pi model, OS version, Arduino serial device path, and planned responsibility split

## First bench sequence

1. Disconnect motor power and verify A4/A5 position plus A2/A3 activation readings, disabled state at rest, and LED telemetry.
2. With all power removed, set both microstep banks to 1/8 and verify the DRV8825 current limit; then keep wheels raised and test each motor independently at conservative speed.
3. Confirm forward direction and correct any inversion flags in configuration.
4. Press every bumper while driving slowly and verify an immediate latched stop.
5. Measure LED and motor supply current before increasing brightness or speed.
