#pragma once

#include <Bounce2.h>

// Owns the three normally-open obstacle bumpers. Hardware interrupts provide
// immediate event latching while Bounce2 supplies stable live pressed states.
class BumperInput {
 public:
  // Individual bits allow several simultaneous bumper events in one byte.
  enum Mask : uint8_t { Left = 1, Centre = 2, Right = 4 };

  // Configure pull-ups, debounce filters, and interrupt handlers.
  bool begin();
  // Refresh each debounced button; call once per control update.
  void update();
  // Atomically return and clear events latched by interrupt handlers.
  uint8_t consumeAlertMask();
  // Return the currently debounced set of physically pressed bumpers.
  uint8_t pressedMask() const;
  // Convenience guard used before releasing an obstacle-stop latch.
  bool allReleased() const { return pressedMask() == 0; }

 private:
  // Minimal interrupt handlers only set their corresponding alert bit.
  static void onLeftInterrupt();
  static void onCentreInterrupt();
  static void onRightInterrupt();
  // Shared volatile event bits written in interrupt context and consumed in loop().
  static volatile uint8_t interruptMask_;

  Bounce2::Button left_;    // Debounced state for the left bumper.
  Bounce2::Button centre_;  // Debounced state for the centre bumper.
  Bounce2::Button right_;   // Debounced state for the right bumper.
};
