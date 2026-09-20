#include "src/communication/SerialControlLink.h"
#include "src/config/HardwareConfig.h"
#include "src/core/DifferentialMixer.h"
#include "src/core/Types.h"
#include "src/drive/DRI0023Drive.h"
#include "src/input/BumperInput.h"
#include "src/output/LedController.h"

// Main DevBot controller. This is the canonical Arduino IDE entry point.
// Hardware adapters initialize exactly as they will on the assembled robot;
// disconnected shields, LEDs, and normally-open bumpers require no substitutes.

DRI0023Drive drive;
BumperInput bumpers;
LedController leds;
SerialControlLink serialLink;

AppState state = AppState::Boot;
unsigned long stateEnteredMs = 0;
unsigned long lastControlUs = 0;
unsigned long lastTelemetryMs = 0;
DriveCommand appliedCommand{};
bool neutralReleaseRequired = true;

AppState lastReportedState = AppState::Boot;
DriveCommand lastReportedCommand{};
uint8_t lastReportedBumpers = 0xFF;
uint8_t lastReportedDriverMask = 0xFF;
bool telemetrySent = false;

void stopDrive() {
  drive.stop();
  appliedCommand = {};
}

void applyDrive(const DriveCommand& command) {
  appliedCommand = command;
  drive.command(command);
}

void enterState(AppState next) {
  if (state == next) return;
  state = next;
  stateEnteredMs = millis();
}

AppState drivingStateFor(const DriveCommand& command) {
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

void sendTelemetryIfDue(uint8_t bumperMask, bool force = false) {
  const unsigned long nowMs = millis();
  const uint8_t driverEnableMask = drive.enabledMask();
  const bool changed = !telemetrySent || state != lastReportedState ||
                       appliedCommand.left != lastReportedCommand.left ||
                       appliedCommand.right != lastReportedCommand.right ||
                       driverEnableMask != lastReportedDriverMask ||
                       bumperMask != lastReportedBumpers;
  if (!force && !changed &&
      nowMs - lastTelemetryMs < config::kSerialTelemetryIntervalMs) {
    return;
  }

  const uint8_t faultMask = state == AppState::Fault ? 1 : 0;
  serialLink.sendTelemetry(state, appliedCommand, driverEnableMask, bumperMask,
                           faultMask);
  telemetrySent = true;
  lastTelemetryMs = nowMs;
  lastReportedState = state;
  lastReportedCommand = appliedCommand;
  lastReportedDriverMask = driverEnableMask;
  lastReportedBumpers = bumperMask;
}

void setup() {
  Serial.begin(config::kSerialBaud);

  // Initialize the real robot I/O. With components disconnected these calls
  // still configure the exact production pins for meter/scope verification.
  leds.begin();
  const bool bumpersReady = bumpers.begin();
  const bool driveReady = drive.begin();

  if (!bumpersReady || !driveReady) {
    serialLink.begin();
    stopDrive();
    enterState(AppState::Fault);
    sendTelemetryIfDue(0, true);
    return;
  }

  // The driver outputs remain disabled throughout the startup animation.
  leds.showStartupSequence();
  serialLink.begin();
  stopDrive();
  neutralReleaseRequired = config::kRequireNeutralRearm;
  enterState(neutralReleaseRequired ? AppState::AwaitNeutral
                                    : AppState::Disabled);
  leds.showState(state, appliedCommand);
  sendTelemetryIfDue(0, true);
}

void loop() {
  // Neither serial parsing nor control work is allowed to starve STEP pulses.
  serialLink.poll();
  drive.service();

  const unsigned long nowUs = micros();
  if (nowUs - lastControlUs < config::kDriveControlIntervalUs) return;
  lastControlUs = nowUs;

  bumpers.update();
  const uint8_t bumperAlerts = bumpers.consumeAlertMask();
  const uint8_t bumperMask = bumpers.pressedMask();

  const unsigned long nowMs = millis();
  const ControlIntent& intent = serialLink.latest();
  const bool controlFresh =
      serialLink.serialFresh(nowMs) && serialLink.remoteFresh(nowMs);
  const bool controlEnabled = controlFresh && intent.enabled;
  const DriveCommand requestedCommand =
      mixDifferential(intent.steering, intent.throttle);

  // Physical bumper alerts always take priority over communications state.
  if (bumperAlerts != 0 && state != AppState::Fault) {
    stopDrive();
    neutralReleaseRequired = true;
    enterState(AppState::ObstacleStop);
  }

  if (state != AppState::Fault && state != AppState::ObstacleStop &&
      !controlFresh) {
    stopDrive();
    neutralReleaseRequired = true;
    enterState(AppState::CommsLost);
  } else {
    switch (state) {
      case AppState::Boot:
        stopDrive();
        break;

      case AppState::CommsLost:
        stopDrive();
        if (controlFresh) enterState(AppState::AwaitNeutral);
        break;

      case AppState::AwaitNeutral:
        stopDrive();
        if (controlFresh && !controlEnabled &&
            requestedCommand.isNeutral(config::kDriveMotionThreshold)) {
          neutralReleaseRequired = false;
          enterState(AppState::Disabled);
        }
        break;

      case AppState::Disabled:
        stopDrive();
        if (neutralReleaseRequired) {
          enterState(AppState::AwaitNeutral);
        } else if (controlEnabled) {
          applyDrive(requestedCommand);
          enterState(drivingStateFor(appliedCommand));
        }
        break;

      case AppState::Ready:
      case AppState::DrivingForward:
      case AppState::DrivingReverse:
      case AppState::TurningLeft:
      case AppState::TurningRight:
        if (!controlEnabled) {
          stopDrive();
          enterState(AppState::Disabled);
        } else {
          applyDrive(requestedCommand);
          enterState(drivingStateFor(appliedCommand));
        }
        break;

      case AppState::ObstacleStop:
        stopDrive();
        if (millis() - stateEnteredMs >= config::kObstacleMinimumHoldMs &&
            bumpers.allReleased() && controlFresh && !controlEnabled &&
            requestedCommand.isNeutral(config::kDriveMotionThreshold)) {
          neutralReleaseRequired = false;
          enterState(AppState::Disabled);
        }
        break;

      case AppState::Fault:
        stopDrive();
        break;
    }
  }

  leds.showState(state, appliedCommand);
  sendTelemetryIfDue(bumperMask);
}
