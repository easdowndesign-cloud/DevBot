#pragma once

#include "Types.h"

// Convert normalized steering/throttle into ratio-preserving left/right wheel
// demand. Positive steering requests a right turn; positive throttle is forward.
DriveCommand mixDifferential(int16_t steering, int16_t throttle);

// Proportionally constrain a wheel pair to a lower commissioning limit.
DriveCommand limitDriveCommand(const DriveCommand& command, int16_t limit);
