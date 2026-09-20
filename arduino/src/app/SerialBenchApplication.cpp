#include "SerialBenchApplication.h"

#include "../config/HardwareConfig.h"
#include "../core/DifferentialMixer.h"

void SerialBenchApplication::begin() {
  state_ = AppState::Boot;
  applied_ = {};
  neutralReleaseRequired_ = config::kRequireNeutralRearm;
  telemetrySent_ = false;
  link_.begin();
  enterState(neutralReleaseRequired_ ? AppState::AwaitNeutral
                                    : AppState::Disabled);
  sendTelemetryIfDue(true);
}

void SerialBenchApplication::update() {
  link_.poll();

  const unsigned long nowUs = micros();
  if (nowUs - lastControlUs_ < config::kDriveControlIntervalUs) return;
  lastControlUs_ = nowUs;

  const unsigned long nowMs = millis();
  const ControlIntent& intent = link_.latest();
  const bool controlFresh = link_.serialFresh(nowMs) && link_.remoteFresh(nowMs);
  const bool controlEnabled = controlFresh && intent.enabled;
  const DriveCommand requested =
      mixDifferential(intent.steering, intent.throttle);

  if (!controlFresh) {
    stopLogicalDrive();
    neutralReleaseRequired_ = true;
    enterState(AppState::CommsLost);
  } else {
    switch (state_) {
      case AppState::Boot:
      case AppState::CommsLost:
        stopLogicalDrive();
        enterState(AppState::AwaitNeutral);
        break;

      case AppState::AwaitNeutral:
        stopLogicalDrive();
        if (!controlEnabled &&
            requested.isNeutral(config::kDriveMotionThreshold)) {
          neutralReleaseRequired_ = false;
          enterState(AppState::Disabled);
        }
        break;

      case AppState::Disabled:
        stopLogicalDrive();
        if (neutralReleaseRequired_) {
          enterState(AppState::AwaitNeutral);
        } else if (controlEnabled) {
          applied_ = requested;
          enterState(drivingStateFor(applied_));
        }
        break;

      case AppState::Ready:
      case AppState::DrivingForward:
      case AppState::DrivingReverse:
      case AppState::TurningLeft:
      case AppState::TurningRight:
        if (!controlEnabled) {
          stopLogicalDrive();
          enterState(AppState::Disabled);
        } else {
          applied_ = requested;
          enterState(drivingStateFor(applied_));
        }
        break;

      case AppState::ObstacleStop:
        // No bumpers are initialized in this test mode; keep this state safe if
        // it is ever entered by a future diagnostic command.
        stopLogicalDrive();
        neutralReleaseRequired_ = true;
        enterState(AppState::AwaitNeutral);
        break;

      case AppState::Fault:
        stopLogicalDrive();
        break;
    }
  }

  sendTelemetryIfDue();
}

void SerialBenchApplication::enterState(AppState next) {
  state_ = next;
}

void SerialBenchApplication::stopLogicalDrive() {
  applied_ = {};
}

void SerialBenchApplication::sendTelemetryIfDue(bool force) {
  const unsigned long nowMs = millis();
  const bool changed = !telemetrySent_ || state_ != lastReportedState_ ||
                       applied_.left != lastReported_.left ||
                       applied_.right != lastReported_.right;
  if (!force && !changed &&
      nowMs - lastTelemetryMs_ < config::kSerialTelemetryIntervalMs) {
    return;
  }

  link_.sendTelemetry(state_, applied_, 0, 0,
                      state_ == AppState::Fault ? 1 : 0);
  telemetrySent_ = true;
  lastTelemetryMs_ = nowMs;
  lastReportedState_ = state_;
  lastReported_ = applied_;
}

AppState SerialBenchApplication::drivingStateFor(const DriveCommand& command) {
  const int32_t translation = static_cast<int32_t>(command.left) + command.right;
  const int32_t turn = static_cast<int32_t>(command.left) - command.right;
  if (turn > config::kDriveMotionThreshold * 2L) return AppState::TurningRight;
  if (turn < -config::kDriveMotionThreshold * 2L) return AppState::TurningLeft;
  if (translation > config::kDriveMotionThreshold * 2L) {
    return AppState::DrivingForward;
  }
  if (translation < -config::kDriveMotionThreshold * 2L) {
    return AppState::DrivingReverse;
  }
  return AppState::Ready;
}
