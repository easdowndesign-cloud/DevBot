#pragma once

#include <Arduino.h>

#include "../config/HardwareConfig.h"
#include "../core/Types.h"

// Owns the newline-framed USB serial contract between the Pi 4 and Mega.
// Parsing is bounded and non-blocking so future step generation can continue.
class SerialControlLink {
 public:
  void begin();
  void poll();

  const ControlIntent& latest() const { return latest_; }
  bool hasCommand() const { return hasCommand_; }
  bool serialFresh(unsigned long nowMs) const;
  bool remoteFresh(unsigned long nowMs) const;

  uint16_t acceptedCount() const { return acceptedCount_; }
  uint16_t rejectedCount() const { return rejectedCount_; }

  void sendHello() const;
  void sendTelemetry(AppState state, const DriveCommand& applied,
                     uint8_t driverEnableMask, uint8_t bumperMask,
                     uint8_t faultMask) const;

 private:
  void processLine();
  bool parseCommand(char* body);
  void printFrame(const char* body) const;
  static uint16_t crc16(const char* data, size_t length);
  static bool sequenceIsNewer(uint16_t candidate, uint16_t previous);

  char line_[config::kSerialMaximumLineLength + 1]{};
  uint8_t lineLength_ = 0;
  bool overflowed_ = false;
  bool hasCommand_ = false;
  bool hasRemoteSequence_ = false;
  uint16_t lastSerialSequence_ = 0;
  uint16_t lastRemoteSequence_ = 0;
  unsigned long lastCommandMs_ = 0;
  unsigned long lastRemoteAdvanceMs_ = 0;
  uint16_t acceptedCount_ = 0;
  uint16_t rejectedCount_ = 0;
  ControlIntent latest_{};
};
