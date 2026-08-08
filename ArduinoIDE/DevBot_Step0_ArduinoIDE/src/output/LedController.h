#pragma once

#include <Adafruit_NeoPixel.h>
#include <Arduino.h>

#include "../core/Types.h"

// Maps application and per-motor states onto the rear-mounted addressable LED
// groups. It also owns the one-time successful-startup animation.
class LedController {
 public:
  // Semantic colours keep state logic independent of packed NeoPixel values.
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

  // Construct the NeoPixel object using the configured count, pin, and byte order.
  LedController();
  // Initialize the strip at limited brightness and start with every pixel off.
  void begin();
  // Display the blocking setup-only animation while motor outputs are disabled.
  void showStartupSequence();
  // Display current left/mode/right status, transmitting only visible changes.
  void showState(AppState state, const DriveCommand& command);
  // Select the semantic colour for one motor group.
  static StatusColour motorStatusColour(int16_t speed, AppState state);
  // Select the semantic colour for the centre application-mode group.
  static StatusColour modeStatusColour(AppState state);
  // Return a flash-resident colour label for serial bench telemetry.
  static const __FlashStringHelper* colourName(StatusColour colour);

 private:
  // Assign one packed colour to a contiguous physical pixel group.
  void fillRange(uint8_t first, uint8_t count, uint32_t colour);
  // Convert a semantic status colour into a packed 24-bit GRB value.
  static uint32_t pixelColour(StatusColour colour);

  Adafruit_NeoPixel pixels_;  // Driver for the complete 18-pixel chain.
  bool hasPreviousFrame_ = false;  // False until the first status frame is sent.
  StatusColour previousLeftColour_ = StatusColour::Off;    // Last left group value.
  StatusColour previousMiddleColour_ = StatusColour::Off;  // Last centre group value.
  StatusColour previousRightColour_ = StatusColour::Off;   // Last right group value.
};
