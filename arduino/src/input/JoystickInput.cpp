#include "input/JoystickInput.h"

#include "config/HardwareConfig.h"

void JoystickInput::begin() {
  enableButton_.attach(config::kJoystickButtonPin, INPUT_PULLUP);
  enableButton_.interval(config::kButtonDebounceMs);
  enableButton_.setPressedState(LOW);
}

JoystickSnapshot JoystickInput::read() {
  enableButton_.update();
  return {
      normalizeAxis(analogRead(config::kJoystickXPin), config::kJoystickCentreX,
                    config::kInvertJoystickX),
      normalizeAxis(analogRead(config::kJoystickYPin), config::kJoystickCentreY,
                    config::kInvertJoystickY),
      enableButton_.pressed(),
  };
}

DriveCommand JoystickInput::mix(const JoystickSnapshot& input) const {
  // Arcade mixing: Y is throttle and X is steering. Renormalize at the corners.
  long left = static_cast<long>(input.y) + input.x;
  long right = static_cast<long>(input.y) - input.x;
  const long peak = max(abs(left), abs(right));
  if (peak > config::kDriveScale) {
    left = left * config::kDriveScale / peak;
    right = right * config::kDriveScale / peak;
  }
  return {static_cast<int16_t>(left), static_cast<int16_t>(right)};
}

int16_t JoystickInput::normalizeAxis(int raw, int centre, bool inverted) const {
  int delta = raw - centre;
  if (abs(delta) <= config::kJoystickDeadband) return 0;

  const int span = delta > 0 ? (1023 - centre - config::kJoystickDeadband)
                             : (centre - config::kJoystickDeadband);
  const int beyondDeadband = abs(delta) - config::kJoystickDeadband;
  long normalized = static_cast<long>(beyondDeadband) * config::kDriveScale / max(span, 1);
  normalized = constrain(normalized, 0, config::kDriveScale);
  if (delta < 0) normalized = -normalized;
  if (inverted) normalized = -normalized;
  return static_cast<int16_t>(normalized);
}

