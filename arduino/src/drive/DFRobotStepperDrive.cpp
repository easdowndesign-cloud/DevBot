#include "drive/DFRobotStepperDrive.h"

#include <Wire.h>

#include "config/HardwareConfig.h"

bool DFRobotStepperDrive::begin() {
  Wire.begin();
  left_.init();
  right_.init();
  stop();
  return true;
}

void DFRobotStepperDrive::command(const DriveCommand& requested) {
  DriveCommand next = requested;
  if (config::kInvertLeftMotor) next.left = -next.left;
  if (config::kInvertRightMotor) next.right = -next.right;

  const unsigned long now = millis();
  const bool changed = next.left != previous_.left || next.right != previous_.right;
  if (!changed && now - lastWriteMs_ < config::kDriveCommandRefreshMs) return;

  applyMotor(left_, next.left, previous_.left);
  applyMotor(right_, next.right, previous_.right);
  previous_ = next;
  lastWriteMs_ = now;
  stopped_ = next.isNeutral();
}

void DFRobotStepperDrive::stop() {
  if (stopped_) return;
  left_.stop();
  right_.stop();
  previous_ = {};
  lastWriteMs_ = millis();
  stopped_ = true;
}

void DFRobotStepperDrive::applyMotor(DFRobot_Stepper& motor, int16_t requested, int16_t previous) {
  if (requested == 0) {
    if (previous != 0) motor.stop();
    return;
  }

  const uint8_t direction = requested > 0 ? CW : CCW;
  motor.start(0, toDriverSpeed(abs(requested)), direction);
}

uint16_t DFRobotStepperDrive::toDriverSpeed(int16_t magnitude) const {
  const long mapped = map(constrain(magnitude, 0, config::kDriveScale), 0,
                          config::kDriveScale, 0, config::kStepperMaximumRunSpeed);
  if (mapped == 0) return 0;
  return static_cast<uint16_t>(max(mapped, static_cast<long>(config::kStepperMinimumRunSpeed)));
}
