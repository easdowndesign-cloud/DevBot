#pragma once

#include <Arduino.h>

// High-level operating modes used by the state machine, LEDs, and telemetry.
enum class AppState : uint8_t {
  Boot,            // Hardware initialization is still in progress.
  Disabled,        // Dead-man input is released; drivers are immediately off.
  Ready,           // Dead-man input is active but wheel commands are neutral.
  DrivingForward,  // Both-wheel average requests forward motion.
  DrivingReverse,  // Both-wheel average requests reverse motion.
  TurningLeft,     // Left/right wheel difference requests a left turn.
  TurningRight,    // Left/right wheel difference requests a right turn.
  ObstacleStop,    // A bumper event has latched an immediate safety stop.
  Fault,           // Hardware initialization failed; motion is prohibited.
};

// Logical left/right wheel demand. Values use config::kDriveScale rather than
// hardware pulse units so the state machine remains independent of the driver.
struct DriveCommand {
  // Zero defaults represent a stopped robot.
  DriveCommand(int16_t leftValue = 0, int16_t rightValue = 0)
      : left(leftValue), right(rightValue) {}

  int16_t left;   // Signed logical demand for the left wheel.
  int16_t right;  // Signed logical demand for the right wheel.

  // True when both wheel demands fall inside the supplied stop threshold.
  bool isNeutral(int16_t threshold = 0) const {
    return abs(left) <= threshold && abs(right) <= threshold;
  }
};

// One complete joystick sample, including normalized position and the raw plus
// hysteresis-filtered states of both analogue activation channels.
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

  int16_t x;                  // Normalized steering demand (-1000 to +1000).
  int16_t y;                  // Normalized throttle demand (-1000 to +1000).
  uint16_t xActivationRaw;    // Unfiltered A2 ADC reading for diagnostics.
  uint16_t yActivationRaw;    // Unfiltered A3 ADC reading for diagnostics.
  bool xActive;               // Hysteresis-filtered X activation state.
  bool yActive;               // Hysteresis-filtered Y activation state.

  // Either active channel authorizes the normal drive state machine.
  bool isActive() const { return xActive || yActive; }
};
