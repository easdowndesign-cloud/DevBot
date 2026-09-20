"""Single source of truth for DevBot Pico remote configuration."""

FIRMWARE_VERSION = "1.0.0"
PROTOCOL_VERSION = 1

# PiicoDev shared I2C bus on the Pico expansion board.
I2C_BUS = 0
I2C_SDA_PIN = 8
I2C_SCL_PIN = 9
# The Core Electronics SSD1306 driver recommends a minimum 400 kHz bus.
# The PiicoDev transceiver shares this bus and supports the same rate.
I2C_FREQUENCY_HZ = 400_000
OLED_I2C_ADDRESS = 0x3C
TRANSCEIVER_I2C_ADDRESS = 0x1A
TRANSCEIVER_DEVICE_ID = 495

# Joystick: physical pins 31/32, powered only from Pico 3V3(OUT).
JOYSTICK_X_PIN = 26
JOYSTICK_Y_PIN = 27
COMMAND_SCALE = 1000
DEADBAND = 70
EMA_ALPHA = 0.25
INVERT_X = False
INVERT_Y = True

# Replace these values with results from calibrate_joystick.py.
JOYSTICK_X_MIN = 0
JOYSTICK_X_CENTRE = 32768
JOYSTICK_X_MAX = 65535
JOYSTICK_Y_MIN = 0
JOYSTICK_Y_CENTRE = 32768
JOYSTICK_Y_MAX = 65535

# Raw ADC criteria for safe startup/re-arm centre validation.
BOOT_CENTRE_WINDOW_RAW = 3500
BOOT_STABILITY_SPREAD_RAW = 1400
BOOT_NEUTRAL_HOLD_MS = 500

# Movement-derived activation hysteresis.
ACTIVE_ON = 60
ACTIVE_OFF = 40
ACTIVE_OFF_HOLD_MS = 100

# Cooperative scheduler periods.
INPUT_PERIOD_MS = 10
TX_PERIOD_MS = 20
DISPLAY_PERIOD_MS = 100
STARTUP_DISPLAY_MS = 600
DIAGNOSTIC_PERIOD_MS = 500
PERIPHERAL_RETRY_MS = 5000
ACK_STALE_MS = 250
LINK_LOST_MS = 500
WATCHDOG_TIMEOUT_MS = 2000
# Leave True for deployed operation. Temporarily set False while commissioning
# through Thonny so stopping main.py does not start a watchdog reset loop.
WATCHDOG_ENABLED = False
LOOP_YIELD_MS = 1
MAX_RX_PER_CYCLE = 4
MAX_CONSECUTIVE_ADC_ERRORS = 3
MAX_CONSECUTIVE_TX_ERRORS = 3

# Both ends must use exactly these radio settings.
RADIO_GROUP = 73
REMOTE_RADIO_ADDRESS = 1
ROBOT_RADIO_ADDRESS = 2
RADIO_SPEED = 2
RADIO_FREQUENCY = 922
RADIO_TX_POWER = 20

# ASCII "DBV1" as a stable 32-bit project identifier. This is pairing, not
# encryption or authentication. Copy the same value to the Pi 4 receiver.
PAIR_ID = 0x44425631

# Development logging. State/fault changes are always concise; health lines
# can be disabled for the deployed remote.
USB_LOGGING = True
PERIODIC_HEALTH_LOGGING = True
