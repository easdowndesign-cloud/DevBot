#include <Arduino.h>

#include "config/HardwareConfig.h"
#include "core/Types.h"
#include "drive/DRI0023Drive.h"
#include "input/BumperInput.h"
#include "input/JoystickInput.h"
#include "output/LedController.h"

// Step 0 application coordinator. Hardware-specific work is delegated to the
// input, drive, and LED adapters so this file can focus on safety and state flow.
namespace {
DRI0023Drive drive;     // Converts logical wheel commands into shield pulses.
JoystickInput joystick; // Provides normalized position and dead-man state.
BumperInput bumpers;    // Latches obstacle events and debounces live switches.
LedController leds;     // Displays startup, motor, and application status.

AppState state = AppState::Boot;       // Current top-level application state.
unsigned long stateEnteredMs = 0;      // Time the current state was entered.
unsigned long lastTelemetryMs = 0;     // Rate-limit timestamp for serial output.
unsigned long lastDriveControlUs = 0;  // Scheduler timestamp for 200 Hz control.
DriveCommand appliedCommand{};         // Logical command currently sent to drive.

// Minimum changes required to emit new analogue telemetry. This avoids serial
// flooding from insignificant ADC noise while preserving useful bench feedback.
constexpr int16_t kTelemetryAxisStep = 100;
constexpr uint16_t kTelemetryActivationStep = 50;
bool telemetryPrinted = false;  // Ensures the first valid sample is always sent.
AppState lastTelemetryState = AppState::Boot;  // Last transmitted state.
JoystickSnapshot lastTelemetryInput{};         // Last transmitted joystick data.
uint8_t lastTelemetryBumperMask = 0xFF;         // Last transmitted live bumpers.
int8_t lastTelemetryLeftDirection = 2;          // Cached -1/0/+1 left direction.
int8_t lastTelemetryRightDirection = 2;         // Cached -1/0/+1 right direction.

// Convert an application state into a stable, human-readable serial label.
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

// Convert a logical wheel demand into its serial direction label.
const __FlashStringHelper* directionName(int16_t command) {
  if (command > config::kDriveMotionThreshold) return F("FWD");
  if (command < -config::kDriveMotionThreshold) return F("REV");
  return F("STOP");
}

// Compact numeric equivalent of directionName(), used for change detection.
int8_t directionCode(int16_t command) {
  if (command > config::kDriveMotionThreshold) return 1;
  if (command < -config::kDriveMotionThreshold) return -1;
  return 0;
}

// Emit one self-contained bench status line when a meaningful value changes.
void printBenchTelemetry(const JoystickSnapshot& input, const DriveCommand& requested,
                         uint8_t bumperMask) {
  if (!config::kBenchTelemetryEnabled) return;

  // Direction changes are more useful to trigger on than every speed increment.
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
  // Enforce both event-change and minimum-interval requirements.
  if ((!statusChanged && !axesChanged) ||
      millis() - lastTelemetryMs < config::kBenchTelemetryIntervalMs) {
    return;
  }
  lastTelemetryMs = millis();

  // Field order is intentionally stable for visual checks and future parsers:
  // state, joystick, raw activation, filtered activation, request, output,
  // direction, bumpers, and the expected left/middle/right LED colours.
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

  // Cache exactly what was represented by this line for the next comparison.
  telemetryPrinted = true;
  lastTelemetryState = state;
  lastTelemetryInput = input;
  lastTelemetryBumperMask = bumperMask;
  lastTelemetryLeftDirection = leftDirection;
  lastTelemetryRightDirection = rightDirection;
}

// Change state once, record entry time, and optionally emit compact production
// state telemetry when verbose bench telemetry has been disabled.
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

// Classify a logical wheel pair. Steering difference takes priority so both
// stationary rotations and moving arcs report their left/right turn direction.
AppState drivingStateFor(const DriveCommand& command) {
  // Sum represents translation; difference represents yaw/steering.
  const int32_t average = static_cast<int32_t>(command.left) + command.right;
  const int32_t turn = static_cast<int32_t>(command.left) - command.right;
  if (turn > config::kDriveMotionThreshold * 2L) return AppState::TurningRight;
  if (turn < -config::kDriveMotionThreshold * 2L) return AppState::TurningLeft;
  if (average > config::kDriveMotionThreshold * 2L) return AppState::DrivingForward;
  if (average < -config::kDriveMotionThreshold * 2L) return AppState::DrivingReverse;
  return AppState::Ready;
}

}  // namespace

// Initialize every subsystem in safe order. The drive adapter disables both
// channels before the success animation is allowed to run.
void setup() {
  Serial.begin(config::kSerialBaud);
  joystick.begin();
  leds.begin();
  const bool bumpersReady = bumpers.begin();
  const bool driveReady = drive.begin();
  // Any initialization failure permanently enters the safe fault state.
  if (!bumpersReady || !driveReady) {
    drive.stop();
    enterState(AppState::Fault);
    return;
  }
  leds.showStartupSequence();
  // Normal operation always begins disabled, requiring joystick activation.
  enterState(AppState::Disabled);
  leds.showState(state, appliedCommand);
}

// Cooperative real-time loop: pulse generation runs continuously while slower
// input, state, LED, and serial work executes at the configured control rate.
void loop() {
  // AccelStepper is cooperative: service both STEP channels on every pass.
  drive.service();

  // Analogue reads and state/LED work run at a fixed 200 Hz. Most loop passes
  // return here, leaving enough service calls for smooth high-rate pulses.
  const unsigned long nowUs = micros();
  if (nowUs - lastDriveControlUs < config::kDriveControlIntervalUs) return;
  lastDriveControlUs = nowUs;

  bumpers.update();
  // Capture all inputs before calculating a new command or state transition.
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
      // setup() normally leaves Boot; retain a safe fallback if it does not.
      drive.stop();
      appliedCommand = {};
      break;

    case AppState::Disabled:
      // Repeated stop() calls guarantee no output remains enabled at rest.
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
      // Normal command changes use the drive adapter's acceleration ramp.
      appliedCommand = requestedCommand;
      drive.command(appliedCommand);
      enterState(drivingStateFor(appliedCommand));
      break;

    case AppState::ObstacleStop:
      // The obstacle latch can clear only after time, bumpers, activation, and
      // joystick position all independently confirm a safe reset condition.
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
      // Fault is intentionally terminal until the controller is reset.
      drive.stop();
      appliedCommand = {};
      break;
  }

  // Both outputs are change-filtered: LEDs avoid redundant interrupt masking,
  // and telemetry avoids flooding the serial buffer.
  leds.showState(state, appliedCommand);
  printBenchTelemetry(joystickInput, requestedCommand, bumpers.pressedMask());
}
