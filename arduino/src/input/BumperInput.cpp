#include "input/BumperInput.h"

#include <Arduino.h>

#include "config/HardwareConfig.h"

volatile uint8_t BumperInput::interruptMask_ = 0;

bool BumperInput::begin() {
  left_.attach(config::kBumperLeftPin, INPUT_PULLUP);
  centre_.attach(config::kBumperCentrePin, INPUT_PULLUP);
  right_.attach(config::kBumperRightPin, INPUT_PULLUP);
  left_.interval(config::kButtonDebounceMs);
  centre_.interval(config::kButtonDebounceMs);
  right_.interval(config::kButtonDebounceMs);
  left_.setPressedState(LOW);
  centre_.setPressedState(LOW);
  right_.setPressedState(LOW);

  const int leftInterrupt = digitalPinToInterrupt(config::kBumperLeftPin);
  const int centreInterrupt = digitalPinToInterrupt(config::kBumperCentrePin);
  const int rightInterrupt = digitalPinToInterrupt(config::kBumperRightPin);
  if (leftInterrupt == NOT_AN_INTERRUPT || centreInterrupt == NOT_AN_INTERRUPT ||
      rightInterrupt == NOT_AN_INTERRUPT) {
    return false;
  }

  attachInterrupt(leftInterrupt, onLeftInterrupt, FALLING);
  attachInterrupt(centreInterrupt, onCentreInterrupt, FALLING);
  attachInterrupt(rightInterrupt, onRightInterrupt, FALLING);
  return true;
}

void BumperInput::update() {
  left_.update();
  centre_.update();
  right_.update();
}

uint8_t BumperInput::consumeAlertMask() {
  noInterrupts();
  const uint8_t result = interruptMask_;
  interruptMask_ = 0;
  interrupts();
  return result;
}

uint8_t BumperInput::pressedMask() const {
  uint8_t result = 0;
  if (left_.isPressed()) result |= Left;
  if (centre_.isPressed()) result |= Centre;
  if (right_.isPressed()) result |= Right;
  return result;
}

void BumperInput::onLeftInterrupt() { interruptMask_ |= Left; }
void BumperInput::onCentreInterrupt() { interruptMask_ |= Centre; }
void BumperInput::onRightInterrupt() { interruptMask_ |= Right; }
