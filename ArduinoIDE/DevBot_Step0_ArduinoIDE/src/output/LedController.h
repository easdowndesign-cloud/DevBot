#pragma once

#include <Adafruit_NeoPixel.h>
#include <Arduino.h>

#include "../core/Types.h"

class LedController {
 public:
  enum class StatusColour : uint8_t {
    Off,
    Green,
    Red,
    Amber,
    Blue,
    Cyan,
    Purple,
    Magenta,
    Orange,
  };

  LedController();
  void begin();
  void showStartupSequence();
  void showState(AppState state, const DriveCommand& command);
  static StatusColour motorStatusColour(int16_t speed, AppState state);
  static StatusColour modeStatusColour(AppState state);
  static const __FlashStringHelper* colourName(StatusColour colour);

 private:
  void fillRange(uint8_t first, uint8_t count, uint32_t colour);
  static uint32_t pixelColour(StatusColour colour);

  Adafruit_NeoPixel pixels_;
  bool hasPreviousFrame_ = false;
  StatusColour previousLeftColour_ = StatusColour::Off;
  StatusColour previousMiddleColour_ = StatusColour::Off;
  StatusColour previousRightColour_ = StatusColour::Off;
};
