#include "DifferentialMixer.h"

#include <Arduino.h>

#include "../config/HardwareConfig.h"

DriveCommand mixDifferential(int16_t steering, int16_t throttle) {
  long left = static_cast<long>(throttle) + steering;
  long right = static_cast<long>(throttle) - steering;
  const long peak = max(abs(left), abs(right));
  if (peak > config::kDriveScale) {
    left = left * config::kDriveScale / peak;
    right = right * config::kDriveScale / peak;
  }
  return {static_cast<int16_t>(left), static_cast<int16_t>(right)};
}

DriveCommand limitDriveCommand(const DriveCommand& command, int16_t limit) {
  const int16_t safeLimit = constrain(limit, 0, config::kDriveScale);
  const long peak = max(abs(static_cast<long>(command.left)),
                        abs(static_cast<long>(command.right)));
  if (peak <= safeLimit || peak == 0) return command;
  return {static_cast<int16_t>(static_cast<long>(command.left) * safeLimit / peak),
          static_cast<int16_t>(static_cast<long>(command.right) * safeLimit / peak)};
}
