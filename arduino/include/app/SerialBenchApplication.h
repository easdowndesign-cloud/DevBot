#pragma once

#include <Arduino.h>

#include "communication/SerialControlLink.h"
#include "core/Types.h"

// Serial-only integration application used while no robot I/O is connected.
// It exercises the production protocol, watchdogs, state logic, mixing, and
// telemetry without initializing any motor, LED, bumper, or joystick pins.
class SerialBenchApplication {
 public:
  void begin();
  void update();

 private:
  void enterState(AppState next);
  void stopLogicalDrive();
  void sendTelemetryIfDue(bool force = false);
  static AppState drivingStateFor(const DriveCommand& command);

  SerialControlLink link_{};
  AppState state_ = AppState::Boot;
  AppState lastReportedState_ = AppState::Boot;
  DriveCommand applied_{};
  DriveCommand lastReported_{};
  unsigned long lastControlUs_ = 0;
  unsigned long lastTelemetryMs_ = 0;
  bool neutralReleaseRequired_ = true;
  bool telemetrySent_ = false;
};
