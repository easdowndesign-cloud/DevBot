#include "output/LedController.h"

#include "config/HardwareConfig.h"

namespace {
constexpr uint32_t kOff = 0x000000;
constexpr uint32_t kGreen = 0x00C020;
constexpr uint32_t kRed = 0xD00000;
constexpr uint32_t kAmber = 0xC06000;
constexpr uint32_t kBlue = 0x0020C0;
constexpr uint32_t kCyan = 0x00A0A0;
constexpr uint32_t kPurple = 0x7000A0;
constexpr uint32_t kMagenta = 0xC00060;
constexpr uint32_t kOrange = 0xD03000;
}  // namespace

LedController::LedController()
    : pixels_(config::kLedCount, config::kLedPin, NEO_GRB + NEO_KHZ800) {}

void LedController::begin() {
  pixels_.begin();
  pixels_.setBrightness(config::kLedBrightness);
  pixels_.clear();
  pixels_.show();
}

void LedController::showState(AppState state, const DriveCommand& command) {
  if (state == previousState_ && command.left == previousCommand_.left &&
      command.right == previousCommand_.right) {
    return;
  }

  pixels_.clear();
  fillRange(config::kLeftLedFirst, config::kLeftLedCount, motorColour(command.left, state));
  fillRange(config::kMiddleLedFirst, config::kMiddleLedCount, modeColour(state));
  fillRange(config::kRightLedFirst, config::kRightLedCount, motorColour(command.right, state));
  pixels_.show();
  previousState_ = state;
  previousCommand_ = command;
}

void LedController::fillRange(uint8_t first, uint8_t count, uint32_t colour) {
  for (uint8_t index = first; index < first + count; ++index) pixels_.setPixelColor(index, colour);
}

uint32_t LedController::motorColour(int16_t speed, AppState state) const {
  if (state == AppState::Fault) return kOrange;
  if (state == AppState::ObstacleStop) return kMagenta;
  if (state == AppState::Disabled || state == AppState::Boot) return kBlue;
  if (speed > config::kDriveMotionThreshold) return kGreen;
  if (speed < -config::kDriveMotionThreshold) return kRed;
  return kAmber;
}

uint32_t LedController::modeColour(AppState state) const {
  switch (state) {
    case AppState::Boot: return kPurple;
    case AppState::Disabled: return kBlue;
    case AppState::Ready: return kCyan;
    case AppState::DrivingForward: return kGreen;
    case AppState::DrivingReverse: return kRed;
    case AppState::ObstacleStop: return kMagenta;
    case AppState::Fault: return kOrange;
  }
  return kOff;
}
