#include "LedController.h"

#include "../config/HardwareConfig.h"

// NEO_GRB + NEO_KHZ800 matches the installed WS2812-compatible LED chain.
LedController::LedController()
    : pixels_(config::kLedCount, config::kLedPin, NEO_GRB + NEO_KHZ800) {}

void LedController::begin() {
  // Clear and transmit once so pixels cannot retain random power-up colours.
  pixels_.begin();
  pixels_.setBrightness(config::kLedBrightness);
  pixels_.clear();
  pixels_.show();
}

void LedController::showStartupSequence() {
  // Half the strip length is the number of mirrored steps needed to meet centre.
  const uint8_t frames = (config::kLedCount + 1) / 2;

  // Twin cyan comets with violet and blue tails converge on the centre.
  for (uint8_t step = 0; step < frames; ++step) {
    pixels_.clear();
    // Head positions advance inward from the two physical ends.
    const uint8_t left = step;
    const uint8_t right = config::kLedCount - 1 - step;
    pixels_.setPixelColor(left, pixelColour(StatusColour::Cyan));
    pixels_.setPixelColor(right, pixelColour(StatusColour::Cyan));
    if (step > 0) {
      pixels_.setPixelColor(left - 1, pixelColour(StatusColour::Purple));
      pixels_.setPixelColor(right + 1, pixelColour(StatusColour::Purple));
    }
    if (step > 1) {
      pixels_.setPixelColor(left - 2, pixelColour(StatusColour::Blue));
      pixels_.setPixelColor(right + 2, pixelColour(StatusColour::Blue));
    }
    pixels_.show();
    delay(45);
  }

  // A green ready wave expands from the centre, then gives one cyan heartbeat.
  pixels_.clear();
  // These are the two centre pixels for an even-length strip.
  const uint8_t leftCentre = (config::kLedCount - 1) / 2;
  const uint8_t rightCentre = config::kLedCount / 2;
  for (uint8_t step = 0; step < frames; ++step) {
    pixels_.setPixelColor(leftCentre - step, pixelColour(StatusColour::Green));
    pixels_.setPixelColor(rightCentre + step, pixelColour(StatusColour::Green));
    pixels_.show();
    delay(35);
  }
  fillRange(0, config::kLedCount, pixelColour(StatusColour::Cyan));
  pixels_.show();
  delay(90);
  fillRange(0, config::kLedCount, pixelColour(StatusColour::Green));
  pixels_.show();
  delay(160);
}

void LedController::showState(AppState state, const DriveCommand& command) {
  // Resolve semantic colours before touching the physical strip.
  const StatusColour leftColour = motorStatusColour(command.left, state);
  const StatusColour middleColour = modeStatusColour(state);
  const StatusColour rightColour = motorStatusColour(command.right, state);
  // NeoPixel transmission briefly masks interrupts. Only transmit when the
  // visible colours change, not for harmless joystick ADC/speed fluctuations.
  if (hasPreviousFrame_ && leftColour == previousLeftColour_ &&
      middleColour == previousMiddleColour_ && rightColour == previousRightColour_) {
    return;
  }

  pixels_.clear();
  // Logical left/right indices already account for the rear-mounted viewpoint.
  fillRange(config::kLeftLedFirst, config::kLeftLedCount,
            pixelColour(leftColour));
  fillRange(config::kMiddleLedFirst, config::kMiddleLedCount,
            pixelColour(middleColour));
  fillRange(config::kRightLedFirst, config::kRightLedCount,
            pixelColour(rightColour));
  pixels_.show();
  hasPreviousFrame_ = true;
  previousLeftColour_ = leftColour;
  previousMiddleColour_ = middleColour;
  previousRightColour_ = rightColour;
}

void LedController::fillRange(uint8_t first, uint8_t count, uint32_t colour) {
  // Pixel groups are contiguous, so an exclusive upper bound keeps this generic.
  for (uint8_t index = first; index < first + count; ++index) pixels_.setPixelColor(index, colour);
}

LedController::StatusColour LedController::motorStatusColour(int16_t speed, AppState state) {
  // Safety/application states take priority over the requested wheel direction.
  if (state == AppState::Fault) return StatusColour::Orange;
  if (state == AppState::ObstacleStop) return StatusColour::Magenta;
  if (state == AppState::Disabled || state == AppState::Boot) return StatusColour::Blue;
  if (speed > config::kDriveMotionThreshold) return StatusColour::Green;
  if (speed < -config::kDriveMotionThreshold) return StatusColour::Red;
  return StatusColour::Amber;
}

LedController::StatusColour LedController::modeStatusColour(AppState state) {
  // The centre group gives one colour for the robot's high-level operating mode.
  switch (state) {
    case AppState::Boot: return StatusColour::Purple;
    case AppState::Disabled: return StatusColour::Blue;
    case AppState::Ready: return StatusColour::Cyan;
    case AppState::DrivingForward: return StatusColour::Green;
    case AppState::DrivingReverse: return StatusColour::Red;
    case AppState::TurningLeft: return StatusColour::Amber;
    case AppState::TurningRight: return StatusColour::Amber;
    case AppState::ObstacleStop: return StatusColour::Magenta;
    case AppState::Fault: return StatusColour::Orange;
  }
  return StatusColour::Off;
}

const __FlashStringHelper* LedController::colourName(StatusColour colour) {
  // F() stores fixed labels in flash instead of consuming scarce Mega SRAM.
  switch (colour) {
    case StatusColour::Off: return F("OFF");
    case StatusColour::Green: return F("GREEN");
    case StatusColour::Red: return F("RED");
    case StatusColour::Amber: return F("AMBER");
    case StatusColour::Blue: return F("BLUE");
    case StatusColour::Cyan: return F("CYAN");
    case StatusColour::Purple: return F("PURPLE");
    case StatusColour::Magenta: return F("MAGENTA");
    case StatusColour::Orange: return F("ORANGE");
  }
  return F("UNKNOWN");
}

uint32_t LedController::pixelColour(StatusColour colour) {
  // Packed values are written as 0xRRGGBB; the NeoPixel object applies GRB order.
  switch (colour) {
    case StatusColour::Off: return 0x000000;
    case StatusColour::Green: return 0x00C020;
    case StatusColour::Red: return 0xD00000;
    case StatusColour::Amber: return 0xC06000;
    case StatusColour::Blue: return 0x0020C0;
    case StatusColour::Cyan: return 0x00A0A0;
    case StatusColour::Purple: return 0x7000A0;
    case StatusColour::Magenta: return 0xC00060;
    case StatusColour::Orange: return 0xD03000;
  }
  return 0x000000;
}
