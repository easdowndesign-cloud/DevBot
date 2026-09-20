# Exact upload steps for the simple transceiver test

## Pico stage

Only three files are used by the Pico program. Existing extra files can remain;
the new `main.py` does not import them.

1. In Thonny, select the Pico interpreter and click Stop.
2. Choose **File > Open**, select local `pico/PiicoDev_Unified.py`, then choose
   **File > Save As > Raspberry Pi Pico** and save as `PiicoDev_Unified.py`.
3. Repeat for `pico/PiicoDev_Transceiver.py`, saving it as
   `PiicoDev_Transceiver.py`.
4. Open local `pico/main.py`, choose **File > Save As > Raspberry Pi Pico**,
   save it as `main.py`, and confirm replacement of the previous file.
5. Click in the Shell and press Ctrl+D. MicroPython reboots and automatically
   runs `/main.py`.

No font, OLED library, config, calibration, protocol or watchdog files are
needed. The OLED implementation and font are provided by `main.py` and
MicroPython's built-in `framebuf` module.

The screen must show a full-height moving joystick crosshair on the left and a
compact graphical status strip on the right. Radio bars plus an X mean
unlinked; filled bars mean linked. The lower robot-and-glyph area is reserved
for future confirmed movement feedback. Raw X/Y values and joystick-derived
direction words are intentionally not displayed.

## Pi 4 stage

Copy the complete local `pi4` folder to the Pi from Windows PowerShell:

```powershell
ssh service@devbot.local "mkdir -p ~/DevBot"
scp -r "D:\Documents\Easdown Design\DevBot\Scripts\simple_transceiver_test\pi4" service@devbot.local:~/DevBot/
```

Then, in the Pi terminal:

```bash
cd ~/DevBot/pi4
sudo apt install -y python3-tk
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
chmod +x install_pi_app.sh run_dashboard.sh
./install_pi_app.sh --install
```

Double-click **DevBot Receiver** on the Pi desktop to start the receiver and
open its graphical dashboard. The Pico and Pi dashboard both change from
`UNLINKED` to `LINKED` when acknowledgements arrive.

Configure autostart from `~/DevBot/pi4`:

```bash
./install_pi_app.sh --enable-autostart
./install_pi_app.sh --disable-autostart
./install_pi_app.sh --status
```
