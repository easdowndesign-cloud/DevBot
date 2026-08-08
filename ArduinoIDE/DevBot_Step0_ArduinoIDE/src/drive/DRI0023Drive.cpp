#include "DRI0023Drive.h"

#include "../config/HardwareConfig.h"

// DRIVER mode tells AccelStepper that each instance controls an external
// STEP/DIR driver rather than directly energizing motor windings.
DRI0023Drive::DRI0023Drive()
    : left_(AccelStepper::DRIVER, config::kLeftStepPin, config::kLeftDirectionPin),
      right_(AccelStepper::DRIVER, config::kRightStepPin, config::kRightDirectionPin) {}

bool DRI0023Drive::begin() {
  // Associate each AccelStepper channel with the shield's enable output.
  left_.setEnablePin(config::kLeftEnablePin);
  right_.setEnablePin(config::kRightEnablePin);

  // DRI0023 enable inputs are active-low; STEP and DIR are active-high/non-inverted.
  left_.setPinsInverted(false, false, true);
  right_.setPinsInverted(false, false, true);
  left_.setMinPulseWidth(config::kDrv8825MinimumPulseWidthUs);
  right_.setMinPulseWidth(config::kDrv8825MinimumPulseWidthUs);
  // setSpeed() will be clamped to these tested 16 MHz pulse-rate limits.
  left_.setMaxSpeed(config::kStepperMaximumStepsPerSecond);
  right_.setMaxSpeed(config::kStepperMaximumStepsPerSecond);
  left_.setSpeed(0.0F);
  right_.setSpeed(0.0F);
  left_.disableOutputs();
  right_.disableOutputs();
  // Keep software state synchronized with the deliberately disabled hardware.
  leftEnabled_ = false;
  rightEnabled_ = false;
  leftTargetSpeed_ = 0.0F;
  rightTargetSpeed_ = 0.0F;
  leftCurrentSpeed_ = 0.0F;
  rightCurrentSpeed_ = 0.0F;
  lastRampUpdateUs_ = micros();
  return true;
}

void DRI0023Drive::service() {
  // micros() subtraction remains valid when the unsigned timer wraps.
  const unsigned long nowUs = micros();
  const unsigned long elapsedUs = nowUs - lastRampUpdateUs_;
  if (elapsedUs >= config::kStepperRampUpdateIntervalUs) {
    // Cap a single ramp update so a long unrelated pause can never create an
    // instantaneous jump to full speed. Unsigned subtraction handles wraparound.
    const unsigned long cappedElapsedUs = min(elapsedUs, 20000UL);
    lastRampUpdateUs_ = nowUs;
    // Convert elapsed time into the largest permitted speed change this update.
    const float maximumSpeedChange =
        config::kStepperAccelerationStepsPerSecondSquared * cappedElapsedUs / 1000000.0F;
    serviceMotor(left_, leftTargetSpeed_, leftCurrentSpeed_, leftEnabled_, maximumSpeedChange);
    serviceMotor(right_, rightTargetSpeed_, rightCurrentSpeed_, rightEnabled_, maximumSpeedChange);
  }
  // runSpeed() emits at most one due pulse and must therefore run every pass.
  left_.runSpeed();
  right_.runSpeed();
}

void DRI0023Drive::command(const DriveCommand& requested) {
  // Logical wheel direction is corrected here for mirrored motor installation.
  const int16_t leftRequest = config::kInvertLeftMotor ? -requested.left : requested.left;
  const int16_t rightRequest = config::kInvertRightMotor ? -requested.right : requested.right;
  setMotorTarget(left_, leftRequest, leftTargetSpeed_, leftCurrentSpeed_, leftEnabled_);
  setMotorTarget(right_, rightRequest, rightTargetSpeed_, rightCurrentSpeed_, rightEnabled_);
}

void DRI0023Drive::stop() {
  // Safety stops intentionally bypass normal acceleration/deceleration ramps.
  leftTargetSpeed_ = 0.0F;
  rightTargetSpeed_ = 0.0F;
  leftCurrentSpeed_ = 0.0F;
  rightCurrentSpeed_ = 0.0F;
  left_.setSpeed(0.0F);
  right_.setSpeed(0.0F);
  if (leftEnabled_) left_.disableOutputs();
  if (rightEnabled_) right_.disableOutputs();
  leftEnabled_ = false;
  rightEnabled_ = false;
}

void DRI0023Drive::setMotorTarget(AccelStepper& motor, int16_t requested, float& targetSpeed,
                                 float currentSpeed, bool& enabled) {
  // A neutral request ramps toward zero; disable only after that ramp completes.
  if (abs(requested) <= config::kDriveMotionThreshold) {
    targetSpeed = 0.0F;
    if (currentSpeed == 0.0F && enabled) {
      motor.disableOutputs();
      enabled = false;
    }
    return;
  }

  // Energize a channel immediately before assigning its first non-zero target.
  if (!enabled) {
    motor.enableOutputs();
    enabled = true;
  }
  targetSpeed = toStepsPerSecond(requested);
}

void DRI0023Drive::serviceMotor(AccelStepper& motor, float targetSpeed, float& currentSpeed,
                                bool& enabled, float maximumSpeedChange) {
  // Approach the target without overshoot. Reversals naturally pass through zero.
  float nextSpeed = currentSpeed;
  if (currentSpeed < targetSpeed) {
    nextSpeed = min(currentSpeed + maximumSpeedChange, targetSpeed);
  } else if (currentSpeed > targetSpeed) {
    nextSpeed = max(currentSpeed - maximumSpeedChange, targetSpeed);
  }

  if (nextSpeed != currentSpeed) {
    currentSpeed = nextSpeed;
    motor.setSpeed(currentSpeed);
  }
  // Remove holding current once a commanded deceleration reaches a full stop.
  if (targetSpeed == 0.0F && currentSpeed == 0.0F && enabled) {
    motor.disableOutputs();
    enabled = false;
  }
}

float DRI0023Drive::toStepsPerSecond(int16_t requested) const {
  // Linear scaling preserves sign while mapping +/-1000 to the pulse-rate limit.
  return static_cast<float>(requested) * config::kStepperMaximumStepsPerSecond /
         config::kDriveScale;
}
