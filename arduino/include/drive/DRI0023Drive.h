#pragma once

#include <AccelStepper.h>

#include "drive/DriveController.h"

class DRI0023Drive final : public DriveController {
 public:
  DRI0023Drive();
  bool begin() override;
  void service() override;
  void command(const DriveCommand& command) override;
  void stop() override;

 private:
  void applyMotor(AccelStepper& motor, int16_t requested, bool& enabled);
  float toStepsPerSecond(int16_t requested) const;

  AccelStepper left_;
  AccelStepper right_;
  bool leftEnabled_ = false;
  bool rightEnabled_ = false;
};
