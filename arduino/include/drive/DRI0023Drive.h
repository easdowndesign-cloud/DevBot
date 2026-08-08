#pragma once

#include <AccelStepper.h>

#include "drive/DriveController.h"

// AccelStepper-backed adapter for the two DRV8825 channels on the DFRobot
// DRI0023 shield. It converts normalized demands into ramped STEP/DIR signals.
class DRI0023Drive final : public DriveController {
 public:
  // Bind both AccelStepper instances to the shield's fixed STEP/DIR pins.
  DRI0023Drive();
  // Configure pulse, direction, and active-low enable behaviour.
  bool begin() override;
  // Advance speed ramps and emit any due pulses; call as often as possible.
  void service() override;
  // Convert and store new left/right target speeds without blocking.
  void command(const DriveCommand& command) override;
  // Bypass the ramp for dead-man, bumper, fault, and disabled-state safety.
  void stop() override;

 private:
  // Apply one logical demand to a motor's target and enable it when required.
  void setMotorTarget(AccelStepper& motor, int16_t requested, float& targetSpeed,
                      float currentSpeed, bool& enabled);
  // Move one current speed toward its target by at most maximumSpeedChange.
  void serviceMotor(AccelStepper& motor, float targetSpeed, float& currentSpeed,
                    bool& enabled, float maximumSpeedChange);
  // Scale a normalized logical demand into emitted microsteps per second.
  float toStepsPerSecond(int16_t requested) const;

  AccelStepper left_;   // Pulse generator for the logical left motor.
  AccelStepper right_;  // Pulse generator for the logical right motor.
  bool leftEnabled_ = false;   // Cached state of the left active-low ENABLE.
  bool rightEnabled_ = false;  // Cached state of the right active-low ENABLE.
  float leftTargetSpeed_ = 0.0F;   // Requested left microsteps per second.
  float rightTargetSpeed_ = 0.0F;  // Requested right microsteps per second.
  float leftCurrentSpeed_ = 0.0F;   // Ramped left microsteps per second.
  float rightCurrentSpeed_ = 0.0F;  // Ramped right microsteps per second.
  unsigned long lastRampUpdateUs_ = 0;  // Timestamp of the last ramp calculation.
};
