#include "input/BumperInput.h"

#include <Arduino.h>
#include <PinChangeInterrupt.h>

#include "config/HardwareConfig.h"

// Interrupt handlers OR bits into this shared byte until loop() consumes them.
volatile uint8_t BumperInput::interruptMask_ = 0;

bool BumperInput::begin() {
  // INPUT_PULLUP makes an open bumper HIGH and a pressed bumper LOW.
  left_.attach(config::kBumperLeftPin, INPUT_PULLUP);
  centre_.attach(config::kBumperCentrePin, INPUT_PULLUP);
  right_.attach(config::kBumperRightPin, INPUT_PULLUP);
  left_.interval(config::kButtonDebounceMs);
  centre_.interval(config::kButtonDebounceMs);
  right_.interval(config::kButtonDebounceMs);
  left_.setPressedState(LOW);
  centre_.setPressedState(LOW);
  right_.setPressedState(LOW);

  // Validate every interrupt mapping before attaching any handler.
  const int leftInterrupt = digitalPinToInterrupt(config::kBumperLeftPin);
  const int centreInterrupt = digitalPinToInterrupt(config::kBumperCentrePin);
  const int rightInterrupt = digitalPinToPinChangeInterrupt(config::kBumperRightPin);
  if (leftInterrupt == NOT_AN_INTERRUPT || centreInterrupt == NOT_AN_INTERRUPT ||
      rightInterrupt == NOT_AN_INTERRUPT) {
    return false;
  }

  attachInterrupt(leftInterrupt, onLeftInterrupt, FALLING);
  attachInterrupt(centreInterrupt, onCentreInterrupt, FALLING);
  // D10 is a Mega pin-change interrupt (PCINT4), allowing the third bumper to
  // remain interrupt-driven without using the shield-obstructed D18-D21 pins.
  attachPinChangeInterrupt(rightInterrupt, onRightInterrupt, FALLING);
  return true;
}

void BumperInput::update() {
  // Bounce2 requires regular polling to advance each debounce state machine.
  left_.update();
  centre_.update();
  right_.update();
}

uint8_t BumperInput::consumeAlertMask() {
  // Copy-and-clear atomically so an ISR cannot lose an event between operations.
  noInterrupts();
  const uint8_t result = interruptMask_;
  interruptMask_ = 0;
  interrupts();
  return result;
}

uint8_t BumperInput::pressedMask() const {
  // Build a live mask from debounced states rather than raw interrupt events.
  uint8_t result = 0;
  if (left_.isPressed()) result |= Left;
  if (centre_.isPressed()) result |= Centre;
  if (right_.isPressed()) result |= Right;
  return result;
}

// Keep ISRs minimal: no logging, LEDs, debounce work, or motor operations.
void BumperInput::onLeftInterrupt() { interruptMask_ |= Left; }
void BumperInput::onCentreInterrupt() { interruptMask_ |= Centre; }
void BumperInput::onRightInterrupt() { interruptMask_ |= Right; }
