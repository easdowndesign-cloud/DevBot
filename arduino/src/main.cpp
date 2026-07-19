#include <Arduino.h>

#include "config/HardwareConfig.h"
#include "core/Types.h"
#include "drive/DRI0023Drive.h"
#include "input/BumperInput.h"
#include "input/JoystickInput.h"
#include "output/LedController.h"

namespace {
DRI0023Drive drive;
JoystickInput joystick;
BumperInput bumpers;
LedController leds;

AppState state = AppState::Boot;
bool enabled = false;
unsigned long stateEnteredMs = 0;
DriveCommand appliedCommand{};

void enterState(AppState next) {
  if (next == state) return;
  state = next;
  stateEnteredMs = millis();
  Serial.print(F("STATE="));
  Serial.println(static_cast<uint8_t>(state));
}

AppState drivingStateFor(const DriveCommand& command) {
  const int32_t average = static_cast<int32_t>(command.left) + command.right;
  if (average > config::kDriveMotionThreshold * 2L) return AppState::DrivingForward;
  if (average < -config::kDriveMotionThreshold * 2L) return AppState::DrivingReverse;
  return AppState::Ready;  // Includes stationary turns; per-motor LEDs still show direction.
}
}  // namespace

void setup() {
  Serial.begin(config::kSerialBaud);
  joystick.begin();
  leds.begin();
  const bool bumpersReady = bumpers.begin();
  const bool driveReady = drive.begin();
  if (!bumpersReady || !driveReady) {
    drive.stop();
    enterState(AppState::Fault);
    return;
  }
  enterState(AppState::Disabled);
}

void loop() {
  // AccelStepper is cooperative: service both STEP channels on every pass.
  drive.service();
  bumpers.update();
  const JoystickSnapshot joystickInput = joystick.read();
  const DriveCommand requestedCommand = joystick.mix(joystickInput);
  const uint8_t bumperAlerts = bumpers.consumeAlertMask();

  // A bumper alert preempts every non-fault state before the normal state machine runs.
  if (bumperAlerts != 0 && state != AppState::Fault) {
    drive.stop();
    appliedCommand = {};
    enterState(AppState::ObstacleStop);
    Serial.print(F("BUMPER_MASK="));
    Serial.println(bumperAlerts);
  }

  // Top-level, non-blocking application state machine.
  switch (state) {
    case AppState::Boot:
      drive.stop();
      appliedCommand = {};
      break;

    case AppState::Disabled:
      drive.stop();
      appliedCommand = {};
      if (joystickInput.enablePressed && requestedCommand.isNeutral(config::kDriveMotionThreshold)) {
        enabled = true;
        enterState(AppState::Ready);
      }
      break;

    case AppState::Ready:
    case AppState::DrivingForward:
    case AppState::DrivingReverse:
      if (joystickInput.enablePressed) {
        enabled = false;
        drive.stop();
        appliedCommand = {};
        enterState(AppState::Disabled);
        break;
      }
      if (!enabled) {
        drive.stop();
        appliedCommand = {};
        enterState(AppState::Disabled);
        break;
      }
      appliedCommand = requestedCommand;
      drive.command(appliedCommand);
      enterState(drivingStateFor(appliedCommand));
      break;

    case AppState::ObstacleStop:
      drive.stop();
      appliedCommand = {};
      if (millis() - stateEnteredMs >= config::kObstacleMinimumHoldMs && bumpers.allReleased() &&
          requestedCommand.isNeutral(config::kDriveMotionThreshold)) {
        // Return disabled so an obstacle can never cause automatic motion resumption.
        enabled = false;
        enterState(AppState::Disabled);
      }
      break;

    case AppState::Fault:
      enabled = false;
      drive.stop();
      appliedCommand = {};
      break;
  }

  leds.showState(state, appliedCommand);
}
