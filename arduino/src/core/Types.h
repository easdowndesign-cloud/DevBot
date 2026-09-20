#pragma once

#include <Arduino.h>

// High-level operating modes used by the state machine, LEDs, and telemetry.
enum class AppState : uint8_t {
  Boot = 0,            // Hardware initialization is still in progress.
  Disabled = 1,        // Run permission is released; outputs are immediately off.
  AwaitNeutral = 2,    // A neutral, disabled command is required before re-arming.
  Ready = 3,           // Run permission is active but wheel commands are neutral.
  DrivingForward = 4,  // Both-wheel average requests forward motion.
  DrivingReverse = 5,  // Both-wheel average requests reverse motion.
  TurningLeft = 6,     // Left/right wheel difference requests a left turn.
  TurningRight = 7,    // Left/right wheel difference requests a right turn.
  ObstacleStop = 8,    // A bumper event has latched an immediate safety stop.
  CommsLost = 9,       // USB or upstream remote data is no longer fresh.
  Fault = 10,          // Hardware initialization failed; motion is prohibited.
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

// Hardware-independent operator intent received over USB serial. Steering and
// throttle use the same normalized -1000..+1000 scale as local input.
struct ControlIntent {
  ControlIntent(int16_t steeringValue = 0, int16_t throttleValue = 0,
                bool enabledValue = false, uint16_t serialSequenceValue = 0,
                uint16_t remoteSequenceValue = 0, uint16_t remoteAgeValue = 0,
                bool validValue = false)
      : steering(steeringValue),
        throttle(throttleValue),
        enabled(enabledValue),
        serialSequence(serialSequenceValue),
        remoteSequence(remoteSequenceValue),
        remoteAgeMs(remoteAgeValue),
        valid(validValue) {}

  int16_t steering;
  int16_t throttle;
  bool enabled;
  uint16_t serialSequence;
  uint16_t remoteSequence;
  uint16_t remoteAgeMs;
  bool valid;
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
