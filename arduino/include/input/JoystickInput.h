#pragma once

#include "core/Types.h"

// Reads the tethered analogue joystick, filters its activation channels, and
// converts X/Y position into normalized differential-drive wheel demands.
class JoystickInput {
 public:
  // Configure activation pins and reset their filtered states.
  void begin();
  // Capture one normalized position/activation snapshot.
  JoystickSnapshot read();
  // Perform arcade mixing: Y controls travel and X controls steering.
  DriveCommand mix(const JoystickSnapshot& input) const;

 private:
  // Remove centre deadband, scale to config::kDriveScale, and optionally invert.
  int16_t normalizeAxis(int raw, int centre, bool inverted) const;
  // Apply separate on/off thresholds so activation noise cannot chatter motion.
  bool updateActivation(uint16_t raw, bool currentState) const;

  bool xActive_ = false;  // Previous filtered X activation state for hysteresis.
  bool yActive_ = false;  // Previous filtered Y activation state for hysteresis.
};
