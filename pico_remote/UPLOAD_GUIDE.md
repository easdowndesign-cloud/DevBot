# Uploading the DevBot remote firmware to a Raspberry Pi Pico

This guide assumes an original Raspberry Pi Pico (RP2040), Windows, and Thonny.
The first upload has two distinct parts: install MicroPython once, then copy the
DevBot `.py` files into the Pico's internal filesystem.

## 1. Prepare safely

1. Leave the robot motors unpowered for remote commissioning.
2. Power the Pico from USB only during programming.
3. Wire the joystick to Pico `3V3(OUT)` and `AGND`; never feed 5 V into GP26 or
   GP27.
4. Connect the PiicoDev OLED and transceiver to the shared I2C0 bus: GP8 SDA
   and GP9 SCL. Confirm their address switches are `0x3C` and `0x1A`.
5. Keep the remote's 915 MHz antenna connected whenever the transceiver is
   powered or transmitting.

## 2. Install MicroPython on a new Pico

1. Install [Thonny](https://thonny.org/) on the Windows computer.
2. Download the current stable **Raspberry Pi Pico** UF2 from the official
   [MicroPython Pico download page](https://micropython.org/download/RPI_PICO/).
   Do not choose Pico W, Pico 2, or a preview build for an original Pico.
3. Unplug the Pico. Hold its `BOOTSEL` button while reconnecting USB, then
   release the button when Windows mounts a drive named `RPI-RP2`.
4. Copy the downloaded `.uf2` file to `RPI-RP2`. The drive automatically
   disconnects and the Pico reboots when flashing finishes.

This is the standard UF2 process documented by
[Raspberry Pi](https://www.raspberrypi.com/documentation/microcontrollers/micropython.html).
It normally needs to be repeated only when upgrading or repairing MicroPython.

## 3. Connect Thonny

1. Open Thonny and connect the Pico by USB normally; do not hold `BOOTSEL`.
2. Select **Run > Configure interpreter** (or click the interpreter indicator
   at the lower right).
3. Choose **MicroPython (Raspberry Pi Pico)** and the detected Pico USB serial
   port. If several COM ports appear, unplug/replug the Pico to identify it.
4. Select **View > Files** and **View > Shell**.
5. Press the red **Stop/Restart backend** button if an existing `main.py` is
   running and preventing file operations.

## 4. Confirm the wiring before uploading the control program

At the Thonny Shell prompt, paste these lines one at a time:

```python
from machine import I2C, Pin
i2c = I2C(0, sda=Pin(8), scl=Pin(9), freq=400000)
[hex(address) for address in i2c.scan()]
```

With both modules connected, the expected result contains `0x1a` and `0x3c`.
Power off and correct the wiring/address switch if `0x1a` is missing. The OLED
is optional at runtime, but resolve a missing `0x3c` now if you expect a display.

## 5. Upload the runtime files

In Thonny's **This computer** file pane, open:

`D:\Documents\Easdown Design\DevBot\Scripts\pico_remote`

Select each file below, right-click, and choose **Upload to /**. The files must
be at the root of the Pico filesystem and retain these exact names:

```text
PiicoDev_SSD1306.py
PiicoDev_Transceiver.py
PiicoDev_Unified.py
font-pet-me-128.dat
config.py
diagnostics.py
joystick.py
oled_view.py
protocol.py
radio_link.py
remote_controller.py
main.py
```

The `.dat` file is required: the bundled SSD1306 driver opens it whenever text
is drawn. Do not upload `tests`, `vendor_licenses`, the Markdown documents, or
`calibrate_joystick.py` for normal operation.

If your Thonny version does not offer binary-file upload, open
`install_oled_font.py`, save it to the Pico with that same name, and run it.
It creates `/font-pet-me-128.dat` and verifies its 768-byte length. Delete the
installer from the Pico afterward; do not also try to save the binary `.dat`
through Thonny's text editor.

Upload `main.py` last. Press **Stop/Restart backend**, or power-cycle the Pico,
to start it. A successful boot shows the firmware/protocol banner followed by
`WAIT NEUTRAL`. Release the joystick and leave it untouched for at least 500 ms.

Until the matching Raspberry Pi 4 receiver is running and returning valid
acknowledgements, `UNLINKED` is the expected final state. In that state the
remote deliberately transmits only neutral commands; joystick movement cannot
arm it.

## 6. Calibrate the joystick

The default calibration spans the full 16-bit ADC range and is only a safe
placeholder. Calibrate before motor testing:

1. Stop the normal program in Thonny.
2. Upload `config.py` if it is not already on the Pico.
3. Open `calibrate_joystick.py` from **This computer**, then press the green
   **Run current script** button. It runs as a temporary script; do not save it
   over the deployed `main.py`.
4. Leave the stick released during the first three seconds.
5. During the next ten seconds, repeatedly move it to every edge and corner.
6. Copy the six printed `JOYSTICK_*` assignments into the local `config.py`.
7. Upload the edited `config.py` to `/`, replacing the old copy.
8. Restart the backend and verify that the released stick displays near X=0,
   Y=0 and reliably completes `WAIT NEUTRAL`.

If forward/backward or left/right is reversed, change `INVERT_Y` or `INVERT_X`
in `config.py`, upload that file again, and restart.

## 7. Expected USB log and first bench checks

With the Thonny Shell open, state transitions appear as `EVENT` lines and the
periodic status appears as `HEALTH` lines. Check in this order:

For interactive commissioning, you may temporarily set
`WATCHDOG_ENABLED = False` in `config.py`. This prevents Thonny's Stop command
from leaving the hardware watchdog running and causing repeated USB reconnects.
Restore it to `True` before deployed operation.

1. `SELF TEST` then `WAIT NEUTRAL` appears without a radio fault.
2. The released joystick produces values close to zero.
3. With no robot receiver, the state remains `UNLINKED` and outgoing axes are
   zero.
4. Once the future receiver acknowledges valid frames, the state becomes
   `READY`; moving the stick becomes `ACTIVE`.
5. Turn the receiver off. Within 500 ms the remote must show `LINK LOST`, send
   neutral, and refuse to re-arm until both the link and neutral hold recover.

For the first integrated motor test, raise the wheels, keep an accessible power
disconnect, and verify direction at low speed before placing the robot on the
floor.

## Troubleshooting

- **No RPI-RP2 drive:** use a known data-capable USB cable, try another USB
  port, and hold `BOOTSEL` before plugging in.
- **No interpreter/COM port:** close other serial programs, reconnect the Pico,
  then select the port again in Thonny.
- **`PiicoDev_*` import error:** upload all three vendor files to `/` with exact
  capitalisation.
- **Radio fault / no `0x1a`:** power off and inspect PiicoDev cable orientation,
  I2C address switch, common ground, and GP8/GP9 routing.
- **OLED missing / no `0x3c`:** the controller continues safely without the
  display; correct the OLED wiring/address and it will retry every five seconds.
- **Repeated watchdog resets:** stop the program in Thonny and inspect the last
  `FATAL` or peripheral error. The safety design intentionally does not feed the
  watchdog after an unhandled failure.
