#include "drive/DRI0023Drive.h"

#include "config/HardwareConfig.h"

DRI0023Drive::DRI0023Drive()
    : left_(AccelStepper::DRIVER, config::kLeftStepPin, config::kLeftDirectionPin),
      right_(AccelStepper::DRIVER, config::kRightStepPin, config::kRightDirectionPin) {}

bool DRI0023Drive::begin() {
  left_.setEnablePin(config::kLeftEnablePin);
  right_.setEnablePin(config::kRightEnablePin);

  // DRI0023 enable inputs are active-low; STEP and DIR are active-high/non-inverted.
  left_.setPinsInverted(false, false, true);
  right_.setPinsInverted(false, false, true);
  left_.setMinPulseWidth(config::kDrv8825MinimumPulseWidthUs);
  right_.setMinPulseWidth(config::kDrv8825MinimumPulseWidthUs);
  left_.setMaxSpeed(config::kStepperMaximumStepsPerSecond);
  right_.setMaxSpeed(config::kStepperMaximumStepsPerSecond);
  left_.setSpeed(0.0F);
  right_.setSpeed(0.0F);
  left_.disableOutputs();
  right_.disableOutputs();
  leftEnabled_ = false;
  rightEnabled_ = false;
  return true;
}

void DRI0023Drive::service() {
  left_.runSpeed();
  right_.runSpeed();
}

void DRI0023Drive::command(const DriveCommand& requested) {
  const int16_t leftRequest = config::kInvertLeftMotor ? -requested.left : requested.left;
  const int16_t rightRequest = config::kInvertRightMotor ? -requested.right : requested.right;
  applyMotor(left_, leftRequest, leftEnabled_);
  applyMotor(right_, rightRequest, rightEnabled_);
}

void DRI0023Drive::stop() {
  left_.setSpeed(0.0F);
  right_.setSpeed(0.0F);
  if (leftEnabled_) left_.disableOutputs();
  if (rightEnabled_) right_.disableOutputs();
  leftEnabled_ = false;
  rightEnabled_ = false;
}

void DRI0023Drive::applyMotor(AccelStepper& motor, int16_t requested, bool& enabled) {
  if (abs(requested) <= config::kDriveMotionThreshold) {
    motor.setSpeed(0.0F);
    if (enabled) motor.disableOutputs();
    enabled = false;
    return;
  }

  if (!enabled) {
    motor.enableOutputs();
    enabled = true;
  }
  motor.setSpeed(toStepsPerSecond(requested));
}

float DRI0023Drive::toStepsPerSecond(int16_t requested) const {
  return static_cast<float>(requested) * config::kStepperMaximumStepsPerSecond /
         config::kDriveScale;
}
