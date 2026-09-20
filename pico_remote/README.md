# DevBot Pico handheld remote

This folder contains the MicroPython firmware for the Step 1 DevBot handheld
remote described by `DevBot_Step1_Pico_Remote_Program_Architecture.md`.

The remote reads one two-axis analogue joystick, sends a fixed-width binary
control frame through a PiicoDev 915 MHz transceiver, receives robot
acknowledgements, and reports state on a PiicoDev SSD1306 OLED. It will only
send non-zero drive commands after both a valid neutral hold and a current
acknowledgement from the robot.

## Hardware map

| Function | Pico GPIO | Physical pin | Notes |
|---|---:|---:|---|
| Joystick X | GP26 / ADC0 | 31 | Analogue input |
| Joystick Y | GP27 / ADC1 | 32 | Analogue input |
| Joystick supply | 3V3(OUT) | 36 | Do not power an analogue input module at 5 V |
| Joystick ground | AGND | 33 | Analogue ground |
| PiicoDev SDA | GP8 / I2C0 SDA | 11 | Shared OLED/radio bus |
| PiicoDev SCL | GP9 / I2C0 SCL | 12 | Shared OLED/radio bus |
| PiicoDev OLED | address `0x3C` | — | Degraded operation allowed if absent |
| PiicoDev transceiver | address `0x1A` | — | Required for operation |

Radio settings are group 73, remote address 1, robot address 2, speed 2,
frequency 922 MHz, and transmit power 20. Both endpoints must match.

## Program structure

| File | Responsibility |
|---|---|
| `main.py` | Hardware composition, watchdog, main loop and fatal fail-safe |
| `remote_controller.py` | Cooperative scheduler and safety state machine |
| `config.py` | Pins, calibration, timing, radio and protocol constants |
| `joystick.py` | Median/EMA filtering, asymmetric scaling, deadband, neutral hold and activation latch |
| `protocol.py` | 24-byte control and 22-byte acknowledgement frames, CRC and sequence rules |
| `radio_link.py` | Narrow adapter around the PiicoDev transceiver driver |
| `oled_view.py` | Dirty-refresh OLED status view with failure isolation |
| `diagnostics.py` | Bounded counters and concise USB serial diagnostics |
| `calibrate_joystick.py` | One-time maintenance utility for measuring ADC endpoints and centre |
| `PiicoDev_*.py` | Vendored Core Electronics device drivers required on the Pico |
| `font-pet-me-128.dat` | Font data required by the PiicoDev SSD1306 driver |
| `tests/` | CPython unit tests; these files are not uploaded to the Pico |

## Safety states

`BOOT -> SELF TEST -> WAIT NEUTRAL -> UNLINKED -> READY -> ACTIVE`

- `WAIT NEUTRAL` requires a stable, centred joystick for 500 ms.
- `UNLINKED` sends neutral control frames while waiting for a valid robot ack.
- `ACTIVE` is derived from joystick movement; there are no joystick-active
  digital pins.
- A link older than 500 ms enters `LINK LOST`, sends neutral immediately, and
  requires a fresh neutral hold before re-arming.
- A critical ADC/radio failure enters `FAULT`. OLED loss is non-critical and
  is retried every 5 seconds.
- The two-second hardware watchdog resets a stalled program, which returns to
  `WAIT NEUTRAL`.

See `UPLOAD_GUIDE.md` for first-time installation and `PROTOCOL.md` for the
Raspberry Pi 4 receiver contract. The motor-free responder used for initial
radio validation is in `../pi/transceiver_validation/`.

## Verification

Run the hardware-independent tests on a desktop:

```powershell
py -3 -B -m unittest discover -s tests -v
```

The suite covers CRC/frame validation, sequence wrap, malformed data,
joystick conditioning, activation hysteresis, startup interlock, link-loss
neutralisation, and duplicate-ack replay handling.
