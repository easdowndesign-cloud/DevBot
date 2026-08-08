#pragma once

#include "../core/Types.h"

class JoystickInput {
 public:
  void begin();
  JoystickSnapshot read();
  DriveCommand mix(const JoystickSnapshot& input) const;

 private:
  int16_t normalizeAxis(int raw, int centre, bool inverted) const;
  bool updateActivation(uint16_t raw, bool currentState) const;

  bool xActive_ = false;
  bool yActive_ = false;
};
