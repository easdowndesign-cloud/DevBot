"""Cooperative DevBot remote scheduler and safety state machine."""

import config
import protocol


BOOT = "BOOT"
SELF_TEST = "SELF TEST"
WAIT_NEUTRAL = "WAIT NEUTRAL"
UNLINKED = "UNLINKED"
READY = "READY"
ACTIVE = "ACTIVE"
LINK_LOST = "LINK LOST"
FAULT = "FAULT"


class RemoteController:
    def __init__(self, joystick, neutral_hold, activation, radio, oled,
                 diagnostics, session_id, ticks_diff, ticks_add):
        self.joystick = joystick
        self.neutral_hold = neutral_hold
        self.activation = activation
        self.radio = radio
        self.oled = oled
        self.diagnostics = diagnostics
        self.session_id = int(session_id) & 0xFFFF or 1
        self.ticks_diff = ticks_diff
        self.ticks_add = ticks_add

        self.state = BOOT
        self.sample = None
        self.centred_once = False
        self.link_recovery = False
        self.display_degraded = False
        self.last_valid_ack_ms = None
        self.last_ack_sequence = None
        self.last_tx_sequence = None
        self.next_sequence = 0
        self.robot_state = 0
        self.bumper_mask = 0
        self.fault_flags = 0
        self.consecutive_adc_errors = 0
        self.consecutive_tx_errors = 0
        self._immediate_tx = False
        self._next_input = None
        self._next_tx = None
        self._next_display = None
        self._next_diagnostic = None
        self._next_radio_retry = None
        self._next_oled_retry = None
        self._startup_started_ms = None
        self._self_test_complete_ms = None

    def _transition(self, state, detail=""):
        if self.state != state:
            self.state = state
            self.diagnostics.event(state, detail)

    def start(self, now_ms):
        self._transition(SELF_TEST)
        self._startup_started_ms = now_ms
        self._self_test_complete_ms = self.ticks_add(
            now_ms, config.STARTUP_DISPLAY_MS
        )
        try:
            self.oled.initialize()
        except Exception as exc:
            self.oled.mark_failed()
            self.display_degraded = True
            self.diagnostics.increment("oled_exceptions")
            self.diagnostics.event("OLED DEGRADED", repr(exc))
        try:
            self.radio.initialize()
        except Exception as exc:
            self.radio.mark_failed()
            self.link_recovery = True
            self._transition(FAULT, "radio init: " + repr(exc))
        self._next_input = now_ms
        self._next_tx = now_ms
        self._next_display = now_ms
        self._next_diagnostic = self.ticks_add(now_ms, config.DIAGNOSTIC_PERIOD_MS)
        self._next_radio_retry = self.ticks_add(now_ms, config.PERIPHERAL_RETRY_MS)
        self._next_oled_retry = self.ticks_add(now_ms, config.PERIPHERAL_RETRY_MS)

    def _due(self, now_ms, deadline):
        return deadline is not None and self.ticks_diff(now_ms, deadline) >= 0

    def _advance(self, deadline, period, now_ms):
        advanced = self.ticks_add(deadline, period)
        while self.ticks_diff(now_ms, advanced) >= 0:
            advanced = self.ticks_add(advanced, period)
        return advanced

    def _sample_joystick(self, now_ms):
        try:
            self.sample = self.joystick.sample()
            self.consecutive_adc_errors = 0
            self.diagnostics.increment("adc_samples")
        except Exception as exc:
            self.consecutive_adc_errors += 1
            if self.consecutive_adc_errors >= config.MAX_CONSECUTIVE_ADC_ERRORS:
                self.activation.reset()
                self.centred_once = False
                self._transition(FAULT, "ADC: " + repr(exc))
                self._immediate_tx = True
            return

        if self.state == WAIT_NEUTRAL:
            centre = self.neutral_hold.update(
                self.sample.raw_x, self.sample.raw_y, now_ms
            )
            if centre is not None:
                self.joystick.x_axis.set_session_centre(centre[0])
                self.joystick.y_axis.set_session_centre(centre[1])
                self.centred_once = True
                self.activation.reset()
                if self._link_is_valid(now_ms):
                    self.link_recovery = False
                    self._transition(READY)
                else:
                    self._transition(UNLINKED)
            return

        if self.state in (READY, ACTIVE):
            is_active = self.activation.update(
                self.sample.steer, self.sample.throttle, now_ms
            )
            self._transition(ACTIVE if is_active else READY)

    def _accept_ack(self, payload, source, now_ms):
        if source != config.ROBOT_RADIO_ADDRESS:
            self.diagnostics.count_rejection("pairing")
            return
        try:
            ack = protocol.unpack_ack(
                payload, config.PROTOCOL_VERSION, config.PAIR_ID, self.session_id
            )
        except protocol.ProtocolError as exc:
            self.diagnostics.count_rejection(exc.reason)
            return
        ack_sequence = ack["ack_sequence"]
        if (self.last_tx_sequence is None or
                not protocol.sequence_was_transmitted(ack_sequence, self.last_tx_sequence)):
            self.diagnostics.count_rejection("sequence")
            return
        if self.last_ack_sequence is not None:
            if ack_sequence == self.last_ack_sequence:
                # Count duplicates without allowing replayed packets to keep
                # the link alive indefinitely.
                self.diagnostics.count_rejection("sequence")
                return
            if not protocol.sequence_is_newer(ack_sequence, self.last_ack_sequence):
                self.diagnostics.count_rejection("sequence")
                return
        self.last_ack_sequence = ack_sequence
        self.last_valid_ack_ms = now_ms
        self.robot_state = ack["robot_state"]
        self.bumper_mask = ack["bumper_mask"]
        self.fault_flags = ack["fault_flags"]
        self.diagnostics.increment("valid_acks")

        if self.state == UNLINKED and self.centred_once:
            self._transition(READY)
        elif self.state == LINK_LOST:
            self.neutral_hold.reset()
            self._transition(WAIT_NEUTRAL)

    def _poll_radio(self, now_ms):
        if not self.radio.operational:
            return
        try:
            packets = self.radio.receive_pending(config.MAX_RX_PER_CYCLE)
        except Exception as exc:
            self.diagnostics.increment("radio_exceptions")
            self._radio_failed("receive: " + repr(exc))
            return
        for payload, source, _rssi in packets:
            self._accept_ack(payload, source, now_ms)

    def _link_age(self, now_ms):
        if self.last_valid_ack_ms is None:
            return None
        return max(0, self.ticks_diff(now_ms, self.last_valid_ack_ms))

    def _link_is_valid(self, now_ms):
        age = self._link_age(now_ms)
        return age is not None and age <= config.LINK_LOST_MS

    def _evaluate_link(self, now_ms):
        if self.state not in (READY, ACTIVE):
            return
        age = self._link_age(now_ms)
        if age is None or age > config.LINK_LOST_MS:
            self.activation.reset()
            self.centred_once = False
            self.link_recovery = True
            self.neutral_hold.reset()
            self.diagnostics.increment("link_loss_events")
            self._transition(LINK_LOST)
            self._immediate_tx = True

    def _safe_axes_and_flags(self):
        flags = 0
        if self.centred_once:
            flags |= protocol.FLAG_CENTRED_ONCE
        if self.display_degraded:
            flags |= protocol.FLAG_DISPLAY_DEGRADED
        if self.link_recovery:
            flags |= protocol.FLAG_LINK_RECOVERY
        if self.state == FAULT:
            flags |= protocol.FLAG_REMOTE_FAULT
        if (self.state == ACTIVE and self.activation.active and self.centred_once and
                self.last_valid_ack_ms is not None and self.sample is not None):
            flags |= protocol.FLAG_ACTIVE
            return self.sample.steer, self.sample.throttle, flags
        return 0, 0, flags

    def _transmit(self, now_ms):
        if not self.radio.operational:
            return
        steer, throttle, flags = self._safe_axes_and_flags()
        frame = protocol.pack_control(
            config.PROTOCOL_VERSION, config.PAIR_ID, self.session_id,
            self.next_sequence, now_ms, steer, throttle, flags,
        )
        self.diagnostics.increment("tx_attempted")
        try:
            self.radio.send(frame)
        except Exception as exc:
            self.consecutive_tx_errors += 1
            self.diagnostics.increment("radio_exceptions")
            if self.consecutive_tx_errors >= config.MAX_CONSECUTIVE_TX_ERRORS:
                self._radio_failed("transmit: " + repr(exc))
            return
        self.consecutive_tx_errors = 0
        self.last_tx_sequence = self.next_sequence
        self.next_sequence = (self.next_sequence + 1) & 0xFFFF
        self.diagnostics.increment("tx_success")

    def _radio_failed(self, detail):
        self.radio.mark_failed()
        self.activation.reset()
        self.centred_once = False
        self.link_recovery = True
        self.last_valid_ack_ms = None
        self.last_ack_sequence = None
        self.diagnostics.event("RADIO FAULT", detail)
        self._transition(FAULT)

    def _retry_peripherals(self, now_ms):
        if not self.radio.operational and self._due(now_ms, self._next_radio_retry):
            self._next_radio_retry = self._advance(
                self._next_radio_retry, config.PERIPHERAL_RETRY_MS, now_ms
            )
            try:
                self.radio.initialize()
            except Exception as exc:
                self.diagnostics.increment("radio_exceptions")
                self.diagnostics.event("RADIO RETRY", repr(exc))
            else:
                self.diagnostics.increment("radio_reinitialisations")
                self.neutral_hold.reset()
                self._transition(WAIT_NEUTRAL, "radio restored")
                self._immediate_tx = True
        if not self.oled.operational and self._due(now_ms, self._next_oled_retry):
            self._next_oled_retry = self._advance(
                self._next_oled_retry, config.PERIPHERAL_RETRY_MS, now_ms
            )
            try:
                self.oled.initialize()
            except Exception as exc:
                self.diagnostics.increment("oled_exceptions")
                self.diagnostics.event("OLED RETRY", repr(exc))
            else:
                self.display_degraded = False
                self.diagnostics.increment("oled_reinitialisations")

    def _advance_self_test(self, now_ms):
        # Keep the startup presentation scheduler-driven: radio polling,
        # neutral transmission, ADC sampling and watchdog service all continue.
        if (self.state == SELF_TEST and
                self._due(now_ms, self._self_test_complete_ms)):
            self.neutral_hold.reset()
            self._transition(WAIT_NEUTRAL)

    def _display_snapshot(self, now_ms):
        age = self._link_age(now_ms)
        if age is None:
            link = "NONE"
        elif age > config.ACK_STALE_MS:
            link = "STALE"
        else:
            link = "OK"
        steer = self.sample.steer if self.sample is not None else 0
        throttle = self.sample.throttle if self.sample is not None else 0
        return {
            "state": self.state,
            "link": link,
            "robot_state": self.robot_state,
            "steer": steer,
            "throttle": throttle,
            "active": self.state == ACTIVE and self.activation.active,
            "bumper_mask": self.bumper_mask,
            "fault_flags": self.fault_flags,
            "startup_step": min(
                6,
                max(0, self.ticks_diff(now_ms, self._startup_started_ms)) // 100
            ) if self._startup_started_ms is not None else 6,
            "adc_ok": self.consecutive_adc_errors == 0 and self.sample is not None,
            "oled_ok": self.oled.operational,
            "radio_ok": self.radio.operational,
        }

    def _refresh_display(self, now_ms):
        if not self.oled.operational:
            return
        try:
            self.oled.render(self._display_snapshot(now_ms))
        except Exception as exc:
            self.oled.mark_failed()
            self.display_degraded = True
            self.diagnostics.increment("oled_exceptions")
            self.diagnostics.event("OLED DEGRADED", repr(exc))

    def cycle(self, now_ms):
        self._poll_radio(now_ms)
        self._evaluate_link(now_ms)
        self._retry_peripherals(now_ms)
        self._advance_self_test(now_ms)

        if self._due(now_ms, self._next_input):
            self._next_input = self._advance(
                self._next_input, config.INPUT_PERIOD_MS, now_ms
            )
            self._sample_joystick(now_ms)

        if self._immediate_tx or self._due(now_ms, self._next_tx):
            if self._due(now_ms, self._next_tx):
                self._next_tx = self._advance(
                    self._next_tx, config.TX_PERIOD_MS, now_ms
                )
            self._immediate_tx = False
            self._transmit(now_ms)

        if self._due(now_ms, self._next_display):
            self._next_display = self._advance(
                self._next_display, config.DISPLAY_PERIOD_MS, now_ms
            )
            self._refresh_display(now_ms)

        if (config.PERIODIC_HEALTH_LOGGING and
                self._due(now_ms, self._next_diagnostic)):
            self._next_diagnostic = self._advance(
                self._next_diagnostic, config.DIAGNOSTIC_PERIOD_MS, now_ms
            )
            try:
                import gc
                free_memory = gc.mem_free()
            except (ImportError, AttributeError):
                free_memory = None
            self.diagnostics.health_line(self.state, self._link_age(now_ms), free_memory)

    def emergency_neutral(self, now_ms):
        """Best-effort neutral frame for the top-level exception handler."""
        self.activation.reset()
        self.centred_once = False
        self.link_recovery = True
        self.state = FAULT
        if self.radio.operational:
            try:
                self._transmit(now_ms)
            except Exception:
                pass
