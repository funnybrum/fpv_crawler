import pyfirmata2
import time

# 1. Setup connection
PORT = "/dev/ttyUSB0"
board = pyfirmata2.Arduino(PORT)

print(f"Connected to {PORT}!")

# 2. Setup Pins
# 'd' = digital, 3 = pin number, 'p' = PWM mode
pwm_pin = board.get_pin('d:3:p')

# 3. Setup Analog and Sampling
# The sampling rate in ms (10ms = 100Hz)
board.samplingOn(10)

# Define a callback function to handle incoming analog data
def analog_callback(value):
    # 'value' is 0.0 to 1.0
    voltage = value * 5.0
    print(f"A0 Reading: {value:.3f} | Voltage: {voltage:.2f}V")

# Assign the callback to A0
board.analog[0].register_callback(analog_callback)
board.analog[0].enable_reporting()

try:
    while True:
        # PWM Output: Cycle through brightness
        for i in range(0, 11):
            duty = i / 10.0
            pwm_pin.write(duty)
            print(f"Setting PWM to {duty*100}%")
            time.sleep(1)

except KeyboardInterrupt:
    board.exit()
    print("\nCommunication stopped.")