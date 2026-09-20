# Simple Pico ↔ Pi 4 transceiver test

This directory now covers the Pico ↔ Pi radio test and the Pi 4 ↔ Mega USB
integration test. The Arduino sketch initializes the production motor-driver,
LED and bumper pins even when those components are physically disconnected, so
pin behavior can be verified during the test.

## Pico files

Save exactly these three Python files to the Pico root:

- `pico/main.py` as `main.py`
- `pico/PiicoDev_Unified.py` as `PiicoDev_Unified.py`
- `pico/PiicoDev_Transceiver.py` as `PiicoDev_Transceiver.py`

The OLED driver and font are built into `main.py` using MicroPython's standard
`framebuf` module. No `.dat`, calibration, watchdog, protocol or state-machine
files are used.

The screen gives the full left-hand height to the live joystick crosshair,
without raw X/Y numbers or joystick-derived direction text. Compact graphical
status indicators occupy the right side: radio bars show acknowledgement link
state, while the robot-and-arrow area is reserved exclusively for future
confirmed robot-motion feedback.

## Pi 4 files

Copy the complete `pi4` directory to the Pi. It contains the radio receiver,
PiicoDev drivers, CRC-framed Arduino serial bridge, requirements, tests, and
graphical dashboard packaging. The current dashboard and serial contract are
for the full-hardware commissioning build (protocol version 2).

The Pi applications run with Raspberry Pi OS's native Python installation. No
virtual environment is required. Install the native hardware packages and run
the tests with:

```bash
cd ~/DevBot/pi4
sudo apt install -y python3-serial python3-smbus2
python3 -B -m unittest discover -s tests -v
```

Run `./install_pi_app.sh --install` to install the desktop icon without changing
autostart. Use `--enable-autostart` or `--disable-autostart` to configure the
graphical desktop autostart entry. The existing icon then launches the updated
dashboard. It shows the remote link, live joystick position, requested
direction, radio RSSI, Mega connection, commanded wheel output, live left/right
driver-enable state, bumper mask and the LED mode commanded by the Arduino
state. The USB serial monitor displays every transmitted `TX >` command and
received `RX <` hello/telemetry frame so the complete path can be inspected on
the Pi screen.

For this commissioning build, non-neutral joystick movement acts as the remote
enable request and returning the stick to centre disables both drivers. The
Mega still applies its neutral-rearm requirement and independent USB/remote
watchdogs. Replace the joystick-derived enable with an explicit physical
dead-man field before mechanically loaded or floor operation.

The bridge prefers the stable `/dev/serial/by-id/` device name and falls back to
`/dev/ttyACM*` or `/dev/ttyUSB*`. Opening the port resets the Mega; the Pi waits
for its valid `HELLO` frame before sending commands. A process lock ensures only
one dashboard owns the radio and serial bridge.

## Headless browser dashboard

`pi4/web_dashboard.py` provides the same live receiver, Arduino and serial-log
information at `http://devbot.local:8080`, without an HDMI display or graphical
desktop session. It uses only Python's standard library and the existing
hardware modules. See `pi4/WEB_DASHBOARD.md` for manual testing and service
installation commands.

Only the Pi-to-Arduino steering value is reversed to match the assembled
DevBot's physical left/right response. The joystick marker and direction shown
on the Pico, desktop dashboard and browser dashboard retain their confirmed
orientation. Arduino firmware is unchanged.
