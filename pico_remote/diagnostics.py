"""Bounded diagnostic counters and optional USB logging."""

COUNTER_NAMES = (
    "adc_samples", "tx_attempted", "tx_success", "valid_acks",
    "reject_crc", "reject_length", "reject_pairing", "reject_version",
    "reject_sequence", "reject_other", "radio_exceptions",
    "radio_reinitialisations", "oled_exceptions", "oled_reinitialisations",
    "link_loss_events",
    "watchdog_resets",
)


class Diagnostics:
    def __init__(self, logging=True):
        self.logging = bool(logging)
        self.counters = {name: 0 for name in COUNTER_NAMES}
        self.last_event = "BOOT"

    def increment(self, name, amount=1):
        self.counters[name] = self.counters.get(name, 0) + amount

    def event(self, name, detail=""):
        self.last_event = name if not detail else name + ":" + str(detail)
        if self.logging:
            print("EVENT state={} detail={}".format(name, detail or "-"))

    def health_line(self, state, link_age_ms, free_memory=None):
        if not self.logging:
            return
        memory = "-" if free_memory is None else str(free_memory)
        print(
            "HEALTH state={} link_ms={} adc={} tx={}/{} ack={} radio_err={} mem={}".format(
                state, "none" if link_age_ms is None else link_age_ms,
                self.counters["adc_samples"], self.counters["tx_success"],
                self.counters["tx_attempted"], self.counters["valid_acks"],
                self.counters["radio_exceptions"], memory,
            )
        )

    def count_rejection(self, reason):
        key = "reject_" + str(reason)
        if key not in self.counters:
            key = "reject_other"
        self.increment(key)
