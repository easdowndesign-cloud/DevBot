#pragma once

#include <Arduino.h>

namespace config {

constexpr unsigned long kSerialBaud = 115200;

// Arduino Mega defaults. Confirm against the hardware checklist before use.
constexpr uint8_t kJoystickXPin = A8;
constexpr uint8_t kJoystickYPin = A9;
constexpr uint8_t kJoystickButtonPin = 22;
constexpr int16_t kJoystickCentreX = 512;
constexpr int16_t kJoystickCentreY = 512;
constexpr int16_t kJoystickDeadband = 70;
constexpr bool kInvertJoystickX = false;
constexpr bool kInvertJoystickY = true;

constexpr uint8_t kBumperLeftPin = 2;
constexpr uint8_t kBumperCentrePin = 3;
constexpr uint8_t kBumperRightPin = 18;
constexpr uint16_t kButtonDebounceMs = 8;
constexpr uint16_t kObstacleMinimumHoldMs = 750;

constexpr uint8_t kLedPin = 6;
constexpr uint8_t kLedCount = 17;
constexpr uint8_t kLedBrightness = 48;  // Current-limited until power design is confirmed.
constexpr uint8_t kLeftLedFirst = 0;
constexpr uint8_t kLeftLedCount = 5;
constexpr uint8_t kMiddleLedFirst = 5;
constexpr uint8_t kMiddleLedCount = 7;
constexpr uint8_t kRightLedFirst = 12;
constexpr uint8_t kRightLedCount = 5;

constexpr int16_t kDriveScale = 1000;
constexpr int16_t kDriveMotionThreshold = 80;
constexpr uint16_t kStepperMinimumRunSpeed = 8;
constexpr uint16_t kStepperMaximumRunSpeed = 350;  // Conservative first-test value; DFR0508 API max is 1023.
constexpr bool kInvertLeftMotor = false;
constexpr bool kInvertRightMotor = true;
constexpr uint16_t kDriveCommandRefreshMs = 250;

}  // namespace config

