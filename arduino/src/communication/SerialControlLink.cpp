#include "SerialControlLink.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

namespace {

bool parseLong(const char* text, long minimum, long maximum, long& result) {
  if (text == nullptr || *text == '\0') return false;
  char* end = nullptr;
  const long value = strtol(text, &end, 10);
  if (*end != '\0' || value < minimum || value > maximum) return false;
  result = value;
  return true;
}

bool parseHex16(const char* text, uint16_t& result) {
  if (text == nullptr || strlen(text) != 4) return false;
  char* end = nullptr;
  const unsigned long value = strtoul(text, &end, 16);
  if (*end != '\0' || value > 0xFFFFUL) return false;
  result = static_cast<uint16_t>(value);
  return true;
}

}  // namespace

void SerialControlLink::begin() {
  lineLength_ = 0;
  overflowed_ = false;
  hasCommand_ = false;
  hasRemoteSequence_ = false;
  acceptedCount_ = 0;
  rejectedCount_ = 0;
  latest_ = {};
  sendHello();
}

void SerialControlLink::poll() {
  uint8_t processed = 0;
  while (Serial.available() > 0 && processed < config::kSerialMaximumBytesPerLoop) {
    ++processed;
    const int incoming = Serial.read();
    if (incoming < 0) break;
    const char character = static_cast<char>(incoming);
    if (character == '\r') continue;
    if (character == '\n') {
      if (overflowed_) {
        ++rejectedCount_;
      } else if (lineLength_ > 0) {
        line_[lineLength_] = '\0';
        processLine();
      }
      lineLength_ = 0;
      overflowed_ = false;
      continue;
    }
    if (overflowed_) continue;
    if (lineLength_ >= config::kSerialMaximumLineLength) {
      overflowed_ = true;
      continue;
    }
    line_[lineLength_++] = character;
  }
}

bool SerialControlLink::serialFresh(unsigned long nowMs) const {
  return hasCommand_ && nowMs - lastCommandMs_ <= config::kSerialCommandTimeoutMs;
}

bool SerialControlLink::remoteFresh(unsigned long nowMs) const {
  if (!hasCommand_ || !hasRemoteSequence_) return false;
  const unsigned long transportAge = nowMs - lastCommandMs_;
  const unsigned long effectiveAge = static_cast<unsigned long>(latest_.remoteAgeMs) + transportAge;
  return effectiveAge <= config::kRemoteCommandTimeoutMs &&
         nowMs - lastRemoteAdvanceMs_ <= config::kRemoteCommandTimeoutMs;
}

void SerialControlLink::sendHello() const {
  char body[56];
  const char* capability =
      config::kDriveHardwareEnabled ? "DRIVE_HW" : "TEST_NO_IO";
  snprintf(body, sizeof(body), "H,%u,DEVBOT_MEGA,%s",
           config::kSerialProtocolVersion, capability);
  printFrame(body);
}

void SerialControlLink::sendTelemetry(AppState state, const DriveCommand& applied,
                                      uint8_t driverEnableMask,
                                      uint8_t bumperMask, uint8_t faultMask) const {
  char body[80];
  const uint16_t acknowledged = hasCommand_ ? latest_.serialSequence : 0;
  snprintf(body, sizeof(body), "T,%u,%u,%u,%d,%d,%u,%u,%u",
           config::kSerialProtocolVersion, acknowledged,
           static_cast<uint8_t>(state), applied.left, applied.right,
           driverEnableMask, bumperMask, faultMask);
  printFrame(body);
}

void SerialControlLink::processLine() {
  char* separator = strrchr(line_, '*');
  if (separator == nullptr) {
    ++rejectedCount_;
    return;
  }
  *separator = '\0';
  uint16_t receivedCrc = 0;
  if (!parseHex16(separator + 1, receivedCrc) ||
      receivedCrc != crc16(line_, strlen(line_)) || !parseCommand(line_)) {
    ++rejectedCount_;
  }
}

bool SerialControlLink::parseCommand(char* body) {
  char* fields[8]{};
  char* context = nullptr;
  uint8_t count = 0;
  for (char* token = strtok_r(body, ",", &context); token != nullptr;
       token = strtok_r(nullptr, ",", &context)) {
    if (count >= 8) return false;
    fields[count++] = token;
  }
  if (count != 8 || strcmp(fields[0], "C") != 0) return false;

  long version = 0;
  long serialSequence = 0;
  long remoteSequence = 0;
  long remoteAge = 0;
  long enabled = 0;
  long steering = 0;
  long throttle = 0;
  if (!parseLong(fields[1], config::kSerialProtocolVersion,
                 config::kSerialProtocolVersion, version) ||
      !parseLong(fields[2], 0, 65535, serialSequence) ||
      !parseLong(fields[3], 0, 9999, remoteSequence) ||
      !parseLong(fields[4], 0, 60000, remoteAge) ||
      !parseLong(fields[5], 0, 1, enabled) ||
      !parseLong(fields[6], -config::kDriveScale, config::kDriveScale, steering) ||
      !parseLong(fields[7], -config::kDriveScale, config::kDriveScale, throttle)) {
    return false;
  }

  const uint16_t nextSerialSequence = static_cast<uint16_t>(serialSequence);
  if (hasCommand_ && !sequenceIsNewer(nextSerialSequence, lastSerialSequence_)) {
    return false;
  }

  const unsigned long nowMs = millis();
  const uint16_t nextRemoteSequence = static_cast<uint16_t>(remoteSequence);
  if (!hasRemoteSequence_ || nextRemoteSequence != lastRemoteSequence_) {
    hasRemoteSequence_ = true;
    lastRemoteSequence_ = nextRemoteSequence;
    lastRemoteAdvanceMs_ = nowMs;
  }
  lastSerialSequence_ = nextSerialSequence;
  lastCommandMs_ = nowMs;
  latest_ = {static_cast<int16_t>(steering), static_cast<int16_t>(throttle),
             enabled != 0, nextSerialSequence, nextRemoteSequence,
             static_cast<uint16_t>(remoteAge), true};
  hasCommand_ = true;
  ++acceptedCount_;
  return true;
}

void SerialControlLink::printFrame(const char* body) const {
  const uint16_t checksum = crc16(body, strlen(body));
  Serial.print(body);
  Serial.print('*');
  if (checksum < 0x1000) Serial.print('0');
  if (checksum < 0x0100) Serial.print('0');
  if (checksum < 0x0010) Serial.print('0');
  Serial.println(checksum, HEX);
}

uint16_t SerialControlLink::crc16(const char* data, size_t length) {
  uint16_t crc = 0xFFFF;
  for (size_t index = 0; index < length; ++index) {
    crc ^= static_cast<uint16_t>(static_cast<uint8_t>(data[index])) << 8;
    for (uint8_t bit = 0; bit < 8; ++bit) {
      crc = (crc & 0x8000U) != 0 ? static_cast<uint16_t>((crc << 1) ^ 0x1021U)
                                : static_cast<uint16_t>(crc << 1);
    }
  }
  return crc;
}

bool SerialControlLink::sequenceIsNewer(uint16_t candidate, uint16_t previous) {
  return static_cast<int16_t>(candidate - previous) > 0;
}
