#include <Arduino.h>

#include "src/config/HardwareConfig.h"
#include "src/core/Types.h"
#include "src/drive/DRI0023Drive.h"
#include "src/input/BumperInput.h"
#include "src/input/JoystickInput.h"
#include "src/output/LedController.h"

namespace {
DRI0023Drive drive;
JoystickInput joystick;
BumperInput bumpers;
LedController leds;

AppState state = AppState::Boot;
unsigned long stateEnteredMs = 0;
unsigned long lastTelemetryMs = 0;
unsigned long lastDriveControlUs = 0;
DriveCommand appliedCommand{};
constexpr int16_t kTelemetryAxisStep = 100;
constexpr uint16_t kTelemetryActivationStep = 50;
bool telemetryPrinted = false;
AppState lastTelemetryState = AppState::Boot;
JoystickSnapshot lastTelemetryInput{};
uint8_t lastTelemetryBumperMask = 0xFF;
int8_t lastTelemetryLeftDirection = 2;
int8_t lastTelemetryRightDirection = 2;

const __FlashStringHelper* stateName(AppState value) {
  switch (value) {
    case AppState::Boot: return F("BOOT");
    case AppState::Disabled: return F("DISABLED");
    case AppState::Ready: return F("READY");
    case AppState::DrivingForward: return F("DRIVING_FORWARD");
    case AppState::DrivingReverse: return F("DRIVING_REVERSE");
    case AppState::TurningLeft: return F("TURNING_LEFT");
    case AppState::TurningRight: return F("TURNING_RIGHT");
    case AppState::ObstacleStop: return F("OBSTACLE_STOP");
    case AppState::Fault: return F("FAULT");
  }
  return F("UNKNOWN");
}

const __FlashStringHelper* directionName(int16_t command) {
  if (command > config::kDriveMotionThreshold) return F("FWD");
  if (command < -config::kDriveMotionThreshold) return F("REV");
  return F("STOP");
}

int8_t directionCode(int16_t command) {
  if (command > config::kDriveMotionThreshold) return 1;
  if (command < -config::kDriveMotionThreshold) return -1;
  return 0;
}

void printBenchTelemetry(const JoystickSnapshot& input, const DriveCommand& requested,
                         uint8_t bumperMask) {
  if (!config::kBenchTelemetryEnabled) return;

  const int8_t leftDirection = directionCode(appliedCommand.left);
  const int8_t rightDirection = directionCode(appliedCommand.right);
  const bool statusChanged =
      !telemetryPrinted || state != lastTelemetryState || bumperMask != lastTelemetryBumperMask ||
      input.xActive != lastTelemetryInput.xActive ||
      input.yActive != lastTelemetryInput.yActive ||
      leftDirection != lastTelemetryLeftDirection || rightDirection != lastTelemetryRightDirection;
  const bool axesChanged = !telemetryPrinted ||
                           abs(input.x - lastTelemetryInput.x) >= kTelemetryAxisStep ||
                           abs(input.y - lastTelemetryInput.y) >= kTelemetryAxisStep ||
                           abs(static_cast<int>(input.xActivationRaw) -
                               static_cast<int>(lastTelemetryInput.xActivationRaw)) >=
                               kTelemetryActivationStep ||
                           abs(static_cast<int>(input.yActivationRaw) -
                               static_cast<int>(lastTelemetryInput.yActivationRaw)) >=
                               kTelemetryActivationStep;
  if ((!statusChanged && !axesChanged) ||
      millis() - lastTelemetryMs < config::kBenchTelemetryIntervalMs) {
    return;
  }
  lastTelemetryMs = millis();

  Serial.print(F("S="));
  Serial.print(stateName(state));
  Serial.print(F(" J="));
  Serial.print(input.x);
  Serial.print(',');
  Serial.print(input.y);
  Serial.print(F(" ACT="));
  Serial.print(input.xActivationRaw);
  Serial.print(',');
  Serial.print(input.yActivationRaw);
  Serial.print(F(" A="));
  Serial.print(input.xActive ? 1 : 0);
  Serial.print(',');
  Serial.print(input.yActive ? 1 : 0);
  Serial.print(F(" REQ="));
  Serial.print(requested.left);
  Serial.print(',');
  Serial.print(requested.right);
  Serial.print(F(" OUT="));
  Serial.print(appliedCommand.left);
  Serial.print(',');
  Serial.print(appliedCommand.right);
  Serial.print(F(" DIR="));
  Serial.print(directionName(appliedCommand.left));
  Serial.print(',');
  Serial.print(directionName(appliedCommand.right));
  Serial.print(F(" B="));
  Serial.print(bumperMask);
  Serial.print(F(" LED="));
  Serial.print(LedController::colourName(
      LedController::motorStatusColour(appliedCommand.left, state)));
  Serial.print('/');
  Serial.print(LedController::colourName(LedController::modeStatusColour(state)));
  Serial.print('/');
  Serial.println(LedController::colourName(
      LedController::motorStatusColour(appliedCommand.right, state)));

  telemetryPrinted = true;
  lastTelemetryState = state;
  lastTelemetryInput = input;
  lastTelemetryBumperMask = bumperMask;
  lastTelemetryLeftDirection = leftDirection;
  lastTelemetryRightDirection = rightDirection;
}

void enterState(AppState next) {
  if (next == state) return;
  state = next;
  stateEnteredMs = millis();
  if (!config::kBenchTelemetryEnabled) {
    Serial.print(F("STATE="));
    Serial.print(stateName(state));
    Serial.print(F(" STATE_ID="));
    Serial.println(static_cast<uint8_t>(state));
  }
}

AppState drivingStateFor(const DriveCommand& command) {
  const int32_t average = static_cast<int32_t>(command.left) + command.right;
  const int32_t turn = static_cast<int32_t>(command.left) - command.right;
  if (turn > config::kDriveMotionThreshold * 2L) return AppState::TurningRight;
  if (turn < -config::kDriveMotionThreshold * 2L) return AppState::TurningLeft;
  if (average > config::kDriveMotionThreshold * 2L) return AppState::DrivingForward;
  if (average < -config::kDriveMotionThreshold * 2L) return AppState::DrivingReverse;
  return AppState::Ready;
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
  leds.showStartupSequence();
  enterState(AppState::Disabled);
  leds.showState(state, appliedCommand);
}

void loop() {
  // AccelStepper is cooperative: service both STEP channels on every pass.
  drive.service();

  // Analogue reads and state/LED work run at a fixed 200 Hz. Most loop passes
  // return here, leaving enough service calls for smooth high-rate pulses.
  const unsigned long nowUs = micros();
  if (nowUs - lastDriveControlUs < config::kDriveControlIntervalUs) return;
  lastDriveControlUs = nowUs;

  bumpers.update();
  const JoystickSnapshot joystickInput = joystick.read();
  drive.service();  // Reduce the step gap caused by four sequential ADC reads.
  const DriveCommand requestedCommand = joystick.mix(joystickInput);
  const bool joystickActive = joystickInput.isActive();
  const uint8_t bumperAlerts = bumpers.consumeAlertMask();

  // A bumper alert preempts every non-fault state before the normal state machine runs.
  if (bumperAlerts != 0 && state != AppState::Fault) {
    drive.stop();
    appliedCommand = {};
    enterState(AppState::ObstacleStop);
    if (!config::kBenchTelemetryEnabled) {
      Serial.print(F("BUMPER_MASK="));
      Serial.println(bumperAlerts);
    }
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
      if (joystickActive) {
        enterState(AppState::Ready);
      }
      break;

    case AppState::Ready:
    case AppState::DrivingForward:
    case AppState::DrivingReverse:
    case AppState::TurningLeft:
    case AppState::TurningRight:
      // Either analogue activation channel is the dead-man control.
      if (!joystickActive) {
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
          !joystickActive &&
          requestedCommand.isNeutral(config::kDriveMotionThreshold)) {
        // Require activation-signal release so an obstacle can never cause
        // automatic motion resumption.
        enterState(AppState::Disabled);
      }
      break;

    case AppState::Fault:
      drive.stop();
      appliedCommand = {};
      break;
  }

  leds.showState(state, appliedCommand);
  printBenchTelemetry(joystickInput, requestedCommand, bumpers.pressedMask());
}
