# Architecture analysis and implementation notes

The supplied Step 1 architecture was treated as a technical specification, not
as executable instructions. Its requested responsibilities were separated into
small hardware adapters, pure logic modules, and a single safety state-machine
coordinator so most behavior can be tested on a desktop without a Pico.

## Requirement mapping

| Architecture requirement | Implementation |
|---|---|
| MicroPython on Raspberry Pi Pico | `main.py` uses `machine.ADC`, `machine.WDT`, `time.ticks_*` |
| GP26/GP27 analogue joystick | Centralised in `config.py`; sampled every 10 ms by `joystick.py` |
| No XACT/YACT digital activation | `ActivationLatch` derives active state from filtered axis magnitude |
| Median, EMA, deadband, asymmetric calibration | `AxisProcessor` in `joystick.py` |
| Neutral startup and link-recovery interlock | `NeutralHold` plus `WAIT NEUTRAL` state |
| GP8/GP9 shared I2C0 | `radio_link.py` and `oled_view.py` use the central configuration |
| PiicoDev radio and SSD1306 drivers | Exact driver files are bundled at the project root |
| Fixed 20 ms radio transmission | Cooperative scheduler in `remote_controller.py` |
| Receive on every loop, bounded work | Up to four queued packets are processed per cycle |
| Fixed binary protocol and CRC | `protocol.py`; documented for the Pi 4 in `PROTOCOL.md` |
| Stale at 250 ms, lost at 500 ms | OLED warning at stale threshold; neutral/link-loss transition at lost threshold |
| OLED isolated from critical control | Display errors set a degraded flag and retry every five seconds |
| Radio/ADC failures fail safe | Non-active frames, `FAULT`, retry where possible, watchdog reset on fatal escape |
| Two-second watchdog | Constructed in `main.py`; deliberately not fed after an unhandled exception |
| Desktop testability | Injected clocks and hardware adapters; tests under `tests/` |

## Deliberate safety behavior

- A non-active control packet is structurally required to carry zero for both
  axes. The encoder and decoder both enforce this invariant.
- The remote does not become `READY` from joystick centring alone. A valid
  acknowledgement for this boot's session and a sequence actually transmitted
  by this remote is also required.
- A duplicate acknowledgement is counted but cannot refresh link age, avoiding
  an indefinitely healthy-looking link from a replayed packet.
- Link recovery always returns through the neutral-hold interlock.
- A missing OLED does not block safe radio operation. A missing radio does.
- The radio receive loop is bounded so a packet flood cannot starve input,
  transmit, display, or watchdog service indefinitely.

## Known integration boundary

This deliverable is the handheld endpoint only. It cannot enter `READY` until a
matching receiver is implemented on the Raspberry Pi 4 and returns the 22-byte
acknowledgement defined in `PROTOCOL.md`. The Pi 4 must independently validate
packets, stop motors on timeout, integrate bumper state, and send acknowledgements.

No live-on-hardware test has been performed in this workspace. The desktop
tests validate logic and framing; joystick endpoints, radio operation, OLED
addressing, RF range, and end-to-end motor safety still require the staged bench
checks in `UPLOAD_GUIDE.md`.

During first hardware commissioning, the shared I2C frequency was raised from
the architecture's conservative 100 kHz starting value to 400 kHz because the
bundled Core Electronics SSD1306 driver explicitly recommends a minimum 400 kHz
and the display failed to initialise at 100 kHz. The transceiver supports the
same shared-bus rate.
