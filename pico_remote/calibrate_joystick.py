"""USB/REPL maintenance utility; upload temporarily as main.py to calibrate."""

import time
from machine import ADC

import config


def sample_for(adc_x, adc_y, duration_ms, prompt):
    print(prompt)
    minimum_x = minimum_y = 65535
    maximum_x = maximum_y = 0
    total_x = total_y = count = 0
    deadline = time.ticks_add(time.ticks_ms(), duration_ms)
    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        x = adc_x.read_u16()
        y = adc_y.read_u16()
        minimum_x = min(minimum_x, x)
        maximum_x = max(maximum_x, x)
        minimum_y = min(minimum_y, y)
        maximum_y = max(maximum_y, y)
        total_x += x
        total_y += y
        count += 1
        time.sleep_ms(10)
    return minimum_x, maximum_x, minimum_y, maximum_y, total_x // count, total_y // count


adc_x = ADC(config.JOYSTICK_X_PIN)
adc_y = ADC(config.JOYSTICK_Y_PIN)

centre = sample_for(adc_x, adc_y, 3000, "Release joystick; sampling centre for 3 seconds...")
print("Centre complete. Move the stick repeatedly to every edge/corner for 10 seconds.")
travel = sample_for(adc_x, adc_y, 10000, "Sampling full travel...")

print("\nCopy these values into config.py:")
print("JOYSTICK_X_MIN = {}".format(travel[0]))
print("JOYSTICK_X_CENTRE = {}".format(centre[4]))
print("JOYSTICK_X_MAX = {}".format(travel[1]))
print("JOYSTICK_Y_MIN = {}".format(travel[2]))
print("JOYSTICK_Y_CENTRE = {}".format(centre[5]))
print("JOYSTICK_Y_MAX = {}".format(travel[3]))

