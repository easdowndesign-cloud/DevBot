"""Joystick filtering, calibration, normalization and activation logic."""


def clamp(value, minimum, maximum):
    return minimum if value < minimum else maximum if value > maximum else value


def median3(a, b, c):
    if a > b:
        a, b = b, a
    if b > c:
        b, c = c, b
    if a > b:
        b = a
    return b


class AxisProcessor:
    def __init__(self, minimum, centre, maximum, deadband, scale=1000,
                 invert=False, ema_alpha=0.25):
        if not minimum < centre < maximum:
            raise ValueError("axis calibration must satisfy minimum < centre < maximum")
        if not 0 < ema_alpha <= 1:
            raise ValueError("ema_alpha must be in (0, 1]")
        self.minimum = int(minimum)
        self.centre = int(centre)
        self.maximum = int(maximum)
        self.deadband = int(deadband)
        self.scale = int(scale)
        self.invert = bool(invert)
        self.ema_alpha = float(ema_alpha)
        self._history = [self.centre, self.centre, self.centre]
        self._history_index = 0
        self._filtered = float(self.centre)

    def set_session_centre(self, centre):
        centre = int(centre)
        if not self.minimum < centre < self.maximum:
            raise ValueError("session centre outside calibration range")
        self.centre = centre
        self._history = [centre, centre, centre]
        self._history_index = 0
        self._filtered = float(centre)

    def process(self, raw):
        raw = clamp(int(raw), 0, 65535)
        self._history[self._history_index] = raw
        self._history_index = (self._history_index + 1) % 3
        med = median3(self._history[0], self._history[1], self._history[2])
        self._filtered += self.ema_alpha * (med - self._filtered)
        return self.normalize(int(round(self._filtered)))

    def normalize(self, raw):
        delta = int(raw) - self.centre
        # DEADBAND is in command units. Convert it independently on each side
        # so asymmetric physical travel still reaches both full-scale values.
        span = self.maximum - self.centre if delta >= 0 else self.centre - self.minimum
        deadband_raw = max(1, (span * self.deadband) // self.scale)
        if abs(delta) <= deadband_raw:
            value = 0
        else:
            beyond = abs(delta) - deadband_raw
            available = max(1, span - deadband_raw)
            value = (beyond * self.scale) // available
            value = clamp(value, 0, self.scale)
            if delta < 0:
                value = -value
        if self.invert:
            value = -value
        return int(value)


class JoystickSample:
    __slots__ = ("raw_x", "raw_y", "steer", "throttle")

    def __init__(self, raw_x, raw_y, steer, throttle):
        self.raw_x = int(raw_x)
        self.raw_y = int(raw_y)
        self.steer = int(steer)
        self.throttle = int(throttle)


class Joystick:
    def __init__(self, read_x, read_y, x_axis, y_axis):
        self._read_x = read_x
        self._read_y = read_y
        self.x_axis = x_axis
        self.y_axis = y_axis

    def sample(self):
        raw_x = int(self._read_x())
        raw_y = int(self._read_y())
        return JoystickSample(
            raw_x, raw_y,
            self.x_axis.process(raw_x),
            self.y_axis.process(raw_y),
        )


class NeutralHold:
    """Validates nominal centre, stability spread and hold duration."""

    def __init__(self, centre_x, centre_y, centre_window_raw,
                 stability_spread_raw, hold_ms, ticks_diff):
        self.centre_x = int(centre_x)
        self.centre_y = int(centre_y)
        self.centre_window_raw = int(centre_window_raw)
        self.stability_spread_raw = int(stability_spread_raw)
        self.hold_ms = int(hold_ms)
        self.ticks_diff = ticks_diff
        self.reset()

    def reset(self):
        self.started_ms = None
        self.min_x = self.max_x = None
        self.min_y = self.max_y = None
        self.sum_x = self.sum_y = self.count = 0

    def update(self, raw_x, raw_y, now_ms):
        if (abs(int(raw_x) - self.centre_x) > self.centre_window_raw or
                abs(int(raw_y) - self.centre_y) > self.centre_window_raw):
            self.reset()
            return None
        if self.started_ms is None:
            self.started_ms = now_ms
            self.min_x = self.max_x = int(raw_x)
            self.min_y = self.max_y = int(raw_y)
        else:
            self.min_x = min(self.min_x, int(raw_x))
            self.max_x = max(self.max_x, int(raw_x))
            self.min_y = min(self.min_y, int(raw_y))
            self.max_y = max(self.max_y, int(raw_y))
        self.sum_x += int(raw_x)
        self.sum_y += int(raw_y)
        self.count += 1
        if (self.max_x - self.min_x > self.stability_spread_raw or
                self.max_y - self.min_y > self.stability_spread_raw):
            self.reset()
            return None
        if self.ticks_diff(now_ms, self.started_ms) >= self.hold_ms:
            result = (self.sum_x // self.count, self.sum_y // self.count)
            self.reset()
            return result
        return None


class ActivationLatch:
    def __init__(self, active_on, active_off, off_hold_ms, ticks_diff):
        if active_off >= active_on:
            raise ValueError("ACTIVE_OFF must be lower than ACTIVE_ON")
        self.active_on = int(active_on)
        self.active_off = int(active_off)
        self.off_hold_ms = int(off_hold_ms)
        self.ticks_diff = ticks_diff
        self.active = False
        self._below_since = None

    def reset(self):
        self.active = False
        self._below_since = None

    def update(self, steer, throttle, now_ms):
        magnitude = max(abs(int(steer)), abs(int(throttle)))
        if not self.active:
            if magnitude >= self.active_on:
                self.active = True
            return self.active
        if magnitude > self.active_off:
            self._below_since = None
        elif self._below_since is None:
            self._below_since = now_ms
        elif self.ticks_diff(now_ms, self._below_since) >= self.off_hold_ms:
            self.active = False
            self._below_since = None
        return self.active

