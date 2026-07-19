#pragma once

#include <Arduino.h>

enum class AppState : uint8_t {
  Boot,
  Disabled,
  Ready,
  DrivingForward,
  DrivingReverse,
  ObstacleStop,
  Fault,
};

struct DriveCommand {
  DriveCommand(int16_t leftValue = 0, int16_t rightValue = 0)
      : left(leftValue), right(rightValue) {}

  int16_t left;
  int16_t right;

  bool isNeutral(int16_t threshold = 0) const {
    return abs(left) <= threshold && abs(right) <= threshold;
  }
};

struct JoystickSnapshot {
  JoystickSnapshot(int16_t xValue = 0, int16_t yValue = 0, bool pressed = false)
      : x(xValue), y(yValue), enablePressed(pressed) {}

  int16_t x;
  int16_t y;
  bool enablePressed;
};
