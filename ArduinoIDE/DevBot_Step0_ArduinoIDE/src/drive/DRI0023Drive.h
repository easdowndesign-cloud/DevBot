#pragma once

#include <AccelStepper.h>

#include "DriveController.h"

class DRI0023Drive final : public DriveController {
 public:
  DRI0023Drive();
  bool begin() override;
  void service() override;
  void command(const DriveCommand& command) override;
  void stop() override;

 private:
  void setMotorTarget(AccelStepper& motor, int16_t requested, float& targetSpeed,
                      float currentSpeed, bool& enabled);
  void serviceMotor(AccelStepper& motor, float targetSpeed, float& currentSpeed,
                    bool& enabled, float maximumSpeedChange);
  float toStepsPerSecond(int16_t requested) const;

  AccelStepper left_;
  AccelStepper right_;
  bool leftEnabled_ = false;
  bool rightEnabled_ = false;
  float leftTargetSpeed_ = 0.0F;
  float rightTargetSpeed_ = 0.0F;
  float leftCurrentSpeed_ = 0.0F;
  float rightCurrentSpeed_ = 0.0F;
  unsigned long lastRampUpdateUs_ = 0;
};
