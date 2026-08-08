#pragma once

#include "../core/Types.h"

// Hardware-independent motor-controller contract consumed by the application
// state machine. Future drive hardware can implement this interface without
// changing joystick, bumper, LED, or state logic.
class DriveController {
 public:
  virtual ~DriveController() = default;
  // Configure hardware and leave every motor output in a safe disabled state.
  virtual bool begin() = 0;
  // Generate due step pulses and advance any non-blocking motion profile.
  virtual void service() = 0;
  // Set the latest logical wheel-speed targets.
  virtual void command(const DriveCommand& command) = 0;
  // Stop immediately and disable the motor-driver outputs.
  virtual void stop() = 0;
};
