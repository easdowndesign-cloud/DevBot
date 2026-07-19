#pragma once

#include <Bounce2.h>

#include "core/Types.h"

class JoystickInput {
 public:
  void begin();
  JoystickSnapshot read();
  DriveCommand mix(const JoystickSnapshot& input) const;

 private:
  int16_t normalizeAxis(int raw, int centre, bool inverted) const;
  Bounce2::Button enableButton_;
};

