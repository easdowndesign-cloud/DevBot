#pragma once

#include <Arduino.h>

namespace config {

constexpr unsigned long kSerialBaud = 115200;
// Human-readable bench diagnostics. Disable this after commissioning because
// periodic Serial output can add small timing disturbances to step generation.
constexpr bool kBenchTelemetryEnabled = true;
constexpr unsigned long kBenchTelemetryIntervalMs = 500;

// Joystick position and activation outputs are all analogue signals.
constexpr uint8_t kJoystickXPin = A4;
constexpr uint8_t kJoystickYPin = A5;
constexpr uint8_t kJoystickXActivationPin = A2;
constexpr uint8_t kJoystickYActivationPin = A3;
// Measured activation outputs are about 2.5 V inactive (~512 ADC) and 5 V
// active (~1023 ADC). Separate thresholds prevent noise from chattering enable.
constexpr uint16_t kJoystickActivationOnThreshold = 800;
constexpr uint16_t kJoystickActivationOffThreshold = 700;
constexpr int16_t kJoystickCentreX = 512;
constexpr int16_t kJoystickCentreY = 512;
constexpr int16_t kJoystickDeadband = 70;
constexpr bool kInvertJoystickX = false;
constexpr bool kInvertJoystickY = true;

constexpr uint8_t kBumperLeftPin = 2;
constexpr uint8_t kBumperCentrePin = 3;
constexpr uint8_t kBumperRightPin = 10;
constexpr uint16_t kButtonDebounceMs = 8;
constexpr uint16_t kObstacleMinimumHoldMs = 750;

// D0/D1 remain UART0, D2/D3/D10 are bumpers, and D9 is the LED data pin.
// D4-D8 and D12 are reserved by the DRI0023 shield.
constexpr uint8_t kLedPin = 9;
constexpr uint8_t kLedCount = 18;
constexpr uint8_t kLedBrightness = 48;  // Current-limited until power design is confirmed.
// The strip is viewed from the rear of the chassis, so the two outer physical
// groups are opposite the original front-view assignment.
constexpr uint8_t kLeftLedFirst = 13;
constexpr uint8_t kLeftLedCount = 5;
constexpr uint8_t kMiddleLedFirst = 0;
constexpr uint8_t kMiddleLedCount = 8;
constexpr uint8_t kRightLedFirst = 8;
constexpr uint8_t kRightLedCount = 5;

constexpr int16_t kDriveScale = 1000;
// Command deadband used for motor direction and stopped-state reporting.
constexpr int16_t kDriveMotionThreshold = 50;
// Slow control/input work to 200 Hz so the remainder of loop() can service
// high-rate step pulses with minimal jitter.
constexpr unsigned long kDriveControlIntervalUs = 5000;
constexpr uint8_t kLeftStepPin = 6;
constexpr uint8_t kLeftDirectionPin = 7;
constexpr uint8_t kLeftEnablePin = 8;
constexpr uint8_t kRightStepPin = 5;
constexpr uint8_t kRightDirectionPin = 4;
constexpr uint8_t kRightEnablePin = 12;
// Set both DRI0023 microstep DIP banks to MS1=HIGH, MS2=HIGH, MS3=LOW.
// A 1.8-degree motor then uses 1,600 pulses/revolution. 4,000 pulses/s is
// approximately 150 shaft RPM and the documented 16 MHz AccelStepper ceiling.
constexpr uint16_t kMotorFullStepsPerRevolution = 200;
constexpr uint8_t kMotorMicrostepDivisor = 8;
constexpr float kStepperMaximumStepsPerSecond = 4000.0F;
constexpr float kStepperAccelerationStepsPerSecondSquared = 5000.0F;
constexpr unsigned long kStepperRampUpdateIntervalUs = 2000;
constexpr uint16_t kDrv8825MinimumPulseWidthUs = 3;
constexpr bool kInvertLeftMotor = false;
constexpr bool kInvertRightMotor = true;

}  // namespace config
