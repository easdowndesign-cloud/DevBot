# Pi 4 motor-free transceiver validation responder

This standalone program turns the Raspberry Pi 4 and its PiicoDev 915 MHz
transceiver into a protocol-aware acknowledgement endpoint. It does not import
the main DevBot supervisor, open an Arduino serial port, mix wheel commands, or
control any GPIO/motor hardware.

It validates each 24-byte Pico control frame, requires a neutral frame when a
new Pico session appears, rejects corrupt/foreign/duplicate/out-of-order frames,
and returns the 22-byte acknowledgement required by the Pico remote. Bumper and
fault fields are always zero for this test.

Run from a Raspberry Pi terminal:

```bash
cd ~/DevBot/pi_transceiver_validation
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python responder.py
```

Expected startup text begins with `READY group=73 radio=2 destination=1`.
Once the Pico is transmitting, direction changes appear as lines such as:

```text
LINKED session=12345 seq=82 dir=FWD RIGHT steer=440 throttle=780 rssi=-51dBm
```

Press `Ctrl+C` to stop. See the deliverable validation guide for the complete
wiring, transfer, I2C enablement, Pico upload, and pass/fail procedure.

