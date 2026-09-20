# DevBot local web dashboard

The web dashboard runs the same `RadioReceiver` and `SerialControlBridge` used
by the proven desktop dashboard. It changes only the presentation layer and is
available to devices on the same local network at:

```text
http://devbot.local:8080
```

The service is intentionally read-only. Robot commands still originate only
from the Pico remote. The browser polls local status every 150 ms and cannot
send drive commands.

The application uses Raspberry Pi OS's native `python3`; no virtual environment
is required. Install the native hardware packages once if they are not already
available:

```bash
sudo apt install -y python3-serial python3-smbus2
```

## Manual test

Close the graphical dashboard first because only one process can own the radio
and Arduino serial port. Then run on the Pi:

```bash
cd /home/service/DevBot/pi4
chmod +x run_web_dashboard.sh install_web_app.sh
python3 -B -m unittest discover -s tests -v
./run_web_dashboard.sh
```

Open `http://devbot.local:8080` from another device on the same Wi-Fi network.
Press `Ctrl+C` in the Pi terminal to stop the manual test.

## Install for headless startup

```bash
cd /home/service/DevBot/pi4
sudo ./install_web_app.sh --install
```

The installer disables the old graphical-dashboard autostart entry and enables
the headless `devbot-web.service` system service. Useful service commands are:

```bash
sudo ./install_web_app.sh --status
sudo ./install_web_app.sh --restart
sudo journalctl -u devbot-web.service -n 100 --no-pager
```

The server has no login page and must remain restricted to the trusted local
network. Do not forward TCP port 8080 from the internet-facing router.
