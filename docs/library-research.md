# Library research and design decisions

Research performed 2026-07-19. Links point to primary project or vendor documentation.

## Arduino

### Motor/stepper control

| Option | Strengths | Constraints | Decision |
| --- | --- | --- | --- |
| [DFRobot DRI0023](https://wiki.dfrobot.com/dri0023/) | Confirmed shield; two DRV8825 STEP/DIR channels, per-channel active-low enable, DIP-selected microstepping | Fixed pins D4-D8/D12; current limit and microstep switches must be set physically | Selected hardware behind `DriveController` |
| [AccelStepper](https://www.airspayce.com/mikem/arduino/AccelStepper/) | Mature, non-blocking `runSpeed()`, independent simultaneous motors, direct STEP/DIR driver mode | Must be serviced every loop; keep Mega rates conservative and avoid blocking work | Selected for continuous joystick speed control on fixed STEP pins D5 and D6 |
| [FastAccelStepper](https://github.com/gin66/FastAccelStepper) | Timer-driven queued stepping and high rates on the Mega 2560 | Mega step outputs must share a supported timer pin group; the DRI0023's fixed D5/D6 pair is not in one group | Not selected for this shield |

The application depends only on `DriveController`. Replacing the shield means replacing one adapter, not the state machine. `service()` is called on every loop so step generation remains independent of state decisions.

### Joystick

The initial joystick is read using Arduino `analogRead()` and a digital push switch, following the shape of DFRobot's [Gravity Joystick DFR0061 example](https://wiki.dfrobot.com/dfr0061/docs/18455). A dedicated `JoystickInput` module owns centering, inversion, deadband, scaling, and differential-drive mixing. No external joystick library is needed for two analogue axes.

### Bumper buttons

[Bounce2](https://github.com/thomasfredericks/Bounce2) is selected for mechanical-switch debounce. Each normally-open bumper also uses Arduino `attachInterrupt()` through `digitalPinToInterrupt()`. The interrupt routines only set a volatile bit; stepper changes, LED updates, debounce, logging, and state transitions stay in the normal loop. This keeps the ISR safe and gives fast obstacle latching.

### Addressable LEDs

[Adafruit NeoPixel](https://github.com/adafruit/Adafruit_NeoPixel) is selected for a small 17-pixel WS2812/SK6812-style chain. It has a small direct API, wide Arduino support, brightness limiting, and no need for the larger animation surface of FastLED at this stage. Pixel layout and colours are isolated in `LedController`.

## Raspberry Pi

| Need | Choice | Reason |
| --- | --- | --- |
| USB/Bluetooth joystick | [python-evdev](https://python-evdev.readthedocs.io/en/stable/) | Direct Linux input events, device discovery, absolute-axis metadata, and async read support; lighter than a graphical Pygame loop |
| Arduino link | [pySerial](https://pyserial.readthedocs.io/en/latest/) | Stable cross-platform serial abstraction with timeouts |
| Pi GPIO buttons/indicators | [GPIO Zero](https://www.raspberrypi.com/documentation/computers/os.html#use-gpio-from-python) | Raspberry Pi's documented high-level GPIO interface and callback/debounce support |
| WS281x if LEDs later move to Pi | [rpi_ws281x](https://github.com/jgarff/rpi_ws281x) | Hardware-timed PWM/PCM/SPI implementation; requires careful GPIO, DMA, audio, voltage-level, and power choices |

For the current milestone, real-time drive safety remains on the Arduino. The Pi is the supervisor and communicates through a narrow serial adapter. This prevents Linux scheduling or a Pi process crash from being the sole stop mechanism.

## Modularity rules

1. State machines consume typed snapshots and commands, not library objects.
2. Hardware/vendor libraries appear only inside adapters.
3. Pins, inversions, thresholds, and timeouts live in configuration.
4. Every loop path is non-blocking; no `delay()` is used in Arduino runtime code.
5. Safety events are latched and require a deliberate neutral/release condition before drive resumes.
