#pragma once

#include <Arduino.h>

enum class AppState : uint8_t {
  Boot,
  Disabled,
  Ready,
  DrivingForward,
  DrivingReverse,
  TurningLeft,
  TurningRight,
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
  JoystickSnapshot(int16_t xValue = 0, int16_t yValue = 0,
                   uint16_t xActivationValue = 0, uint16_t yActivationValue = 0,
                   bool xActivationState = false, bool yActivationState = false)
      : x(xValue),
        y(yValue),
        xActivationRaw(xActivationValue),
        yActivationRaw(yActivationValue),
        xActive(xActivationState),
        yActive(yActivationState) {}

  int16_t x;
  int16_t y;
  uint16_t xActivationRaw;
  uint16_t yActivationRaw;
  bool xActive;
  bool yActive;

  bool isActive() const { return xActive || yActive; }
};
