#include "JoystickInput.h"

#include "../config/HardwareConfig.h"

void JoystickInput::begin() {
  pinMode(config::kJoystickXActivationPin, INPUT);
  pinMode(config::kJoystickYActivationPin, INPUT);
}

JoystickSnapshot JoystickInput::read() {
  const int16_t x = normalizeAxis(analogRead(config::kJoystickXPin),
                                  config::kJoystickCentreX, config::kInvertJoystickX);
  const int16_t y = normalizeAxis(analogRead(config::kJoystickYPin),
                                  config::kJoystickCentreY, config::kInvertJoystickY);
  const uint16_t xActivation = analogRead(config::kJoystickXActivationPin);
  const uint16_t yActivation = analogRead(config::kJoystickYActivationPin);
  xActive_ = updateActivation(xActivation, xActive_);
  yActive_ = updateActivation(yActivation, yActive_);
  return {x, y, xActivation, yActivation, xActive_, yActive_};
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

bool JoystickInput::updateActivation(uint16_t raw, bool currentState) const {
  if (currentState) return raw > config::kJoystickActivationOffThreshold;
  return raw >= config::kJoystickActivationOnThreshold;
}
