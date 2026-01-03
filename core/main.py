import time
from pymavlink import mavutil

boot_time = time.time()

# 1. Setup connection (Replace with your laptop IP)
laptop_ip = "192.168.1.111"
connection = mavutil.mavlink_connection(
    f'udpout:{laptop_ip}:14550',
    source_system=1,
    source_component=1
)

# Mock location
LAT, LON = 42.645953, 23.361574

try:
    last_telemetry_time = 0
    while True:
        current_time = time.time()
        time_boot_ms = int((current_time - boot_time) * 1000)

        # 2. Send Heartbeat and GPS every 1 second
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

        # 3. Poll for Controller Input (MANUAL_CONTROL)
        # blocking=False ensures we don't hang if no input is sent
        msg = connection.recv_match(type='MANUAL_CONTROL', blocking=False)

        if msg:
            # x = Throttle (Trigger), y = Steering (Wheel)
            # Values range from -1000 to 1000
            throttle = msg.x
            steering = msg.y
            buttons = msg.buttons  # Bitmask of any buttons pressed

            # Print to console (using \r to keep the screen clean)
            print(f"MT12 -> Steering: {steering:>5} | Throttle: {throttle:>5} | BTN: {buttons}", end="\r")

        # High frequency loop for snappy controls
        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nShutting down receiver...")
