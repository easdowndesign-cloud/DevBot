DevBot Step 0 - Arduino IDE upload sketch

Open DevBot_Step0_ArduinoIDE.ino in Arduino IDE 2.

Board:
  Arduino AVR Boards > Arduino Mega or Mega 2560

Install these shared libraries using Arduino IDE Library Manager:
  AccelStepper 1.64 by Mike McCauley
  Adafruit NeoPixel 1.15.5 by Adafruit
  Bounce2 2.71 or newer by Thomas O Fredericks
  PinChangeInterrupt 1.2.9 by NicoHood

The libraries normally belong in the configured sketchbook libraries folder.
They do not need to be copied into this sketch.

The main program is the visible .ino file. Project support code is under src
and will compile recursively even though Arduino IDE does not show it as tabs.

Joystick position uses A4/A5. The activation outputs use analogue inputs A2/A3:
about 2.5 V (~512 ADC) at rest and 5 V (~1023 ADC) when active. Either channel
enables control at 800 ADC; both must fall to 700 ADC or lower to disable it.
Serial Monitor reports raw values as ACT=x,y and interpreted states as A=0/1,0/1.
Its S= field reports TURNING_LEFT or TURNING_RIGHT for turning commands instead
of READY. The rear-mounted strip maps pixels 8-12 to the right motor and 13-17
to the left motor.

After successful setup, the LEDs run a brief cyan/purple/blue comet animation,
a green centre-out wave, and a cyan/green confirmation pulse. The motor outputs
remain disabled throughout the startup sequence.

Motor smoothing:
  With USB, motor supply, and battery power ALL disconnected, set both DRI0023
  microstep switch banks to MS1=HIGH, MS2=HIGH, MS3=LOW (1/8 step). Do not move
  the switches while powered. The firmware then ramps motor speed at 5,000
  pulses/s^2 up to 4,000 pulses/s (about 150 RPM for a 1.8-degree motor), and
  ramps through zero for direction changes. Activation release and bumper
  events remain immediate safety stops.

Upload:
  1. Connect the Mega by USB with external 12 V power disconnected.
  2. Select the Mega board and its COM port.
  3. Click Verify, then Upload.
  4. Open Serial Monitor at 115200 baud.

This folder is an Arduino IDE upload copy. The canonical PlatformIO source is:
  D:\Documents\Easdown Design\DevBot\Scripts\arduino
