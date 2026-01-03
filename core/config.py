"""
Configuration settings for the FPV Crawler.
"""

import os

# -- Arduino/Firmata Settings
ARDUINO_PORT = "/dev/serial0"

# -- Servo Settings
STEERING_PIN = 5
THROTTLE_PIN = 6
SERVO_MIN_PULSE = 1000  # in microseconds
SERVO_MAX_PULSE = 2000  # in microseconds

# -- MAVLink Settings
GROUND_CONTROL_STATION_IP = os.getenv("CRAWLER_GCS_IP", "192.168.1.111")
MAVLINK_PORT = 14550
MAVLINK_SOURCE_SYSTEM = 1
MAVLINK_SOURCE_COMPONENT = 1

# -- Mock GPS Location
MOCK_LAT = 42.645953
MOCK_LON = 23.361574

# -- Loop Timings
# Polling intervals in seconds for the main async loops
MAVLINK_RECV_LOOP_SLEEP = 0.01
MAVLINK_SEND_LOOP_SLEEP = 0.1
MAVLINK_MONITOR_LOOP_SLEEP = 1.0
GPS_LOOP_SLEEP = 5.0
VIDEO_MANAGER_LOOP_SLEEP = 0.25
ERROR_LOOP_SLEEP = 1.0 # Sleep duration after an error in a component loop

# -- Logging Settings
LOG_LEVEL = "INFO" # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# -- Video Service Settings
VIDEO_SERVICE_NAME = "crawler-video.service"
GCS_HEARTBEAT_TIMEOUT = 5.0 # Seconds before GCS is considered disconnected
