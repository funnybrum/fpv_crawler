import time
from pymavlink import mavutil
import pyfirmata2

# 1. Setup Arduino connection
PORT = "/dev/serial0"
board = pyfirmata2.Arduino(PORT)

print(f"Connected to {PORT}. Firmware: {board.firmata_version}")

# 2. Setup Pins
# 'd' = digital, 5/6 = pin number, 'p' = PWM mode
steering_pin = board.get_pin('d:5:p')
throttle_pin = board.get_pin('d:6:p')

boot_time = time.time()

# 3. Setup connection (Replace with your laptop IP)
laptop_ip = "192.168.1.111"
connection = mavutil.mavlink_connection(
    f'udpout:{laptop_ip}:14550',
    source_system=1,
    source_component=1
)

# Mock location
LAT, LON = 42.645953, 23.361574

print("Starting the main process...")

try:
    last_telemetry_time = 0
    while True:
        current_time = time.time()
        time_boot_ms = int((current_time - boot_time) * 1000)

        # 4. Send Heartbeat and GPS every 1 second
        if current_time - last_telemetry_time > 1.0:
            # Heartbeat
            connection.mav.heartbeat_send(
                mavutil.mavlink.MAV_TYPE_GROUND_ROVER,
                mavutil.mavlink.MAV_AUTOPILOT_GENERIC,
                mavutil.mavlink.MAV_MODE_FLAG_MANUAL_INPUT_ENABLED, 0, 0)

            # GPS Position
            connection.mav.global_position_int_send(
                time_boot_ms, int(LAT * 1e7), int(LON * 1e7),
                10000, 0, 0, 0, 0, 65535)

            last_telemetry_time = current_time

        # 5. Poll for Controller Input (MANUAL_CONTROL)
        # For testing purposes - purge all unused messages.
        msg = None
        while (m := connection.recv_match(type='MANUAL_CONTROL', blocking=False)) is not None:
            msg = m

        if msg:
            # x = Throttle (Trigger), y = Steering (Wheel)
            # Values range from -1000 to 1000
            throttle = msg.x
            steering = msg.y
            buttons = msg.buttons  # Bitmask of any buttons pressed

            # Print to console (using \r to keep the screen clean)
            print(f"MT12 -> Steering: {steering:>5} | Throttle: {throttle:>5} | BTN: {buttons}")

            # Map values from -1000-1000 to 0-1 for PWM
            steering_pwm = (steering + 1000) / 2000
            throttle_pwm = (throttle + 1000) / 2000

            steering_pin.write(steering_pwm)
            throttle_pin.write(throttle_pwm)

        # Low frequency loop for initial tests
        time.sleep(0.2)

except KeyboardInterrupt:
    print("\nShutting down receiver...")
finally:
    board.exit()
    print("\nCommunication stopped.")
