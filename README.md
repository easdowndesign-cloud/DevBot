# DevBot software

This repository contains the two programs used by DevBot:

- `arduino/` contains the real-time motor, bumper, joystick, and status-light controller.
- `pi/` contains the Raspberry Pi supervisor and the boundary for higher-level behaviours.
- `docs/` records library choices, hardware assumptions, and wiring/configuration decisions.

The whole `Scripts` tree is intentionally one Git repository. Arduino and Pi changes can therefore be reviewed and versioned together without fragile nested repositories.

## Current milestone

The Arduino program implements a non-blocking state machine, one-stick differential drive, three normally-open momentary bumper alerts, and a 17-pixel status layout. The default motor adapter targets the DFRobot DFR0508 FireBeetle DC Motor & Stepper Driver and its `DFRobot_MotorStepper` library.

The Pi program is a runnable, hardware-independent supervisor scaffold. Its serial and Linux joystick adapters are deliberately small so actual hardware details can be added without rewriting the state machine.

## Before powering motors

Review [`docs/hardware-assumptions.md`](docs/hardware-assumptions.md). The exact Arduino model, DFRobot SKU, stepper wiring/order, joystick axes, LED chipset/order, power design, and bumper placement must be confirmed on the bench. Wheels should be raised for the first motor-direction test.

## Quick start

Arduino (PlatformIO):

```text
cd arduino
pio run
pio run --target upload
pio device monitor
```

Raspberry Pi:

```text
cd pi
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev,hardware]"
python -m devbot_pi --config config/devbot.example.toml
```

Run the Pi scaffold without hardware:

```text
python -m devbot_pi --mock --run-seconds 2
```

## GitHub connection

Git is initialized at this repository root. Once the GitHub repository name/owner and visibility are known, add the remote and push:

```text
git remote add origin https://github.com/OWNER/REPOSITORY.git
git push -u origin main
```

The included GitHub Actions workflow builds the Arduino firmware and checks/tests the Pi package.

