"""Narrow PiicoDev Transceiver adapter used by the safety state machine."""

import config


class PiicoDevRadioLink:
    def __init__(self):
        self.radio = None
        self.operational = False
        self.last_rssi = None

    def initialize(self):
        # Pre-scan prevents the vendor constructor from waiting indefinitely
        # when the transceiver is physically absent. The watchdog remains the
        # final recovery mechanism for a driver call that stalls after scan.
        from machine import I2C, Pin
        from PiicoDev_Transceiver import PiicoDev_Transceiver

        bus = I2C(
            config.I2C_BUS,
            sda=Pin(config.I2C_SDA_PIN),
            scl=Pin(config.I2C_SCL_PIN),
            freq=config.I2C_FREQUENCY_HZ,
        )
        try:
            if config.TRANSCEIVER_I2C_ADDRESS not in bus.scan():
                raise OSError("PiicoDev transceiver 0x1A not found")
            device_id = int.from_bytes(
                bus.readfrom_mem(config.TRANSCEIVER_I2C_ADDRESS, 0x01, 2),
                "big",
            )
            ready = bus.readfrom_mem(
                config.TRANSCEIVER_I2C_ADDRESS, 0x25, 1
            )[0]
        finally:
            deinitialize = getattr(bus, "deinit", None)
            if deinitialize is not None:
                deinitialize()
        if device_id != config.TRANSCEIVER_DEVICE_ID:
            raise OSError(
                "PiicoDev transceiver identity {} != {}".format(
                    device_id, config.TRANSCEIVER_DEVICE_ID
                )
            )
        if ready != 1:
            raise OSError("PiicoDev transceiver present but not ready")
        self.radio = PiicoDev_Transceiver(
            bus=config.I2C_BUS,
            freq=config.I2C_FREQUENCY_HZ,
            sda=Pin(config.I2C_SDA_PIN),
            scl=Pin(config.I2C_SCL_PIN),
            i2c_address=config.TRANSCEIVER_I2C_ADDRESS,
            group=config.RADIO_GROUP,
            radio_address=config.REMOTE_RADIO_ADDRESS,
            speed=config.RADIO_SPEED,
            radio_frequency=config.RADIO_FREQUENCY,
            tx_power=config.RADIO_TX_POWER,
            suppress_warnings=True,
        )
        if self.radio.whoami != config.TRANSCEIVER_DEVICE_ID:
            raise OSError("PiicoDev transceiver identity check failed")
        self.operational = True

    def mark_failed(self):
        self.operational = False
        self.radio = None

    def send(self, payload):
        if not self.operational or self.radio is None:
            raise OSError("radio unavailable")
        self.radio.send_bytes(payload, address=config.ROBOT_RADIO_ADDRESS)

    def receive_pending(self, maximum):
        """Return bounded (payload, source address, RSSI) tuples."""
        if not self.operational or self.radio is None:
            return []
        received = []
        for _ in range(int(maximum)):
            if not self.radio.receive_bytes():
                break
            payload = bytes(self.radio.received_bytes)
            source = int(self.radio.source_radio_address)
            rssi = int(self.radio.rssi)
            self.last_rssi = rssi
            received.append((payload, source, rssi))
        return received
