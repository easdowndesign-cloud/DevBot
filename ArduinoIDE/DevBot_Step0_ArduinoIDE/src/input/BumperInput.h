#pragma once

#include <Bounce2.h>

class BumperInput {
 public:
  enum Mask : uint8_t { Left = 1, Centre = 2, Right = 4 };

  bool begin();
  void update();
  uint8_t consumeAlertMask();
  uint8_t pressedMask() const;
  bool allReleased() const { return pressedMask() == 0; }

 private:
  static void onLeftInterrupt();
  static void onCentreInterrupt();
  static void onRightInterrupt();
  static volatile uint8_t interruptMask_;

  Bounce2::Button left_;
  Bounce2::Button centre_;
  Bounce2::Button right_;
};

