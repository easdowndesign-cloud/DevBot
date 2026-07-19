#pragma once

#include <Adafruit_NeoPixel.h>

#include "core/Types.h"

class LedController {
 public:
  LedController();
  void begin();
  void showState(AppState state, const DriveCommand& command);

 private:
  void fillRange(uint8_t first, uint8_t count, uint32_t colour);
  uint32_t motorColour(int16_t speed, AppState state) const;
  uint32_t modeColour(AppState state) const;

  Adafruit_NeoPixel pixels_;
  AppState previousState_ = AppState::Fault;
  DriveCommand previousCommand_{-32768, -32768};
};
