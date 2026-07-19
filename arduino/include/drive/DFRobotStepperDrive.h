#pragma once

#include <DFRobot_MotorStepper.h>

#include "drive/DriveController.h"

class DFRobotStepperDrive final : public DriveController {
 public:
  bool begin() override;
  void command(const DriveCommand& command) override;
  void stop() override;

 private:
  void applyMotor(DFRobot_Stepper& motor, int16_t requested, int16_t previous);
  uint16_t toDriverSpeed(int16_t magnitude) const;

  DFRobot_Stepper left_{SA, A0};
  DFRobot_Stepper right_{SB, A0};
  DriveCommand previous_{};
  unsigned long lastWriteMs_ = 0;
  bool stopped_ = false;
};
