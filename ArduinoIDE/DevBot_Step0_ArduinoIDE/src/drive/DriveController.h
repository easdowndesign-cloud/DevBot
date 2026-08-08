#pragma once

#include "../core/Types.h"

class DriveController {
 public:
  virtual ~DriveController() = default;
  virtual bool begin() = 0;
  virtual void service() = 0;
  virtual void command(const DriveCommand& command) = 0;
  virtual void stop() = 0;
};
