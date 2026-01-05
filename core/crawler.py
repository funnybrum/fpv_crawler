"""
Handles hardware control for the crawler, specifically the Arduino connection
for controlling servos.
"""
import asyncio
import logging
import pyfirmata2

from core import config

logger = logging.getLogger(__name__)


class CrawlerController:
    """
    Manages the connection and communication with the Arduino board for controlling
    the crawler's servos. This is the single point of contact for all hardware.
    """
    def __init__(self):
        """
        Initializes the connection to the Arduino and configures the servo pins.
        """
        self._last_command_time = -1
        self._task = None

        logger.info(f"Connecting to Arduino on port {config.ARDUINO_PORT}...")
        try:
            self._board = pyfirmata2.Arduino(config.ARDUINO_PORT)
            logger.info(f"Connected to Arduino. Firmware: {self._board.firmata_version}")
        except Exception as e:
            logger.error(f"Error connecting to Arduino: {e}")
            self._board = None
            return

        # Get pin objects
        self._steering_pin = self._board.get_pin(f'd:{config.STEERING_PIN}:s')
        self._throttle_pin = self._board.get_pin(f'd:{config.THROTTLE_PIN}:s')

        # Configure servo pulse widths
        self._board.servo_config(config.STEERING_PIN, min_pulse=config.STEERING_MIN_PULSE, max_pulse=config.STEERING_MAX_PULSE)
        self._board.servo_config(config.THROTTLE_PIN, min_pulse=config.THROTTLE_MIN_PULSE, max_pulse=config.THROTTLE_MAX_PULSE)
        logger.info(f"Steering servo on pin {config.STEERING_PIN} configured for {config.STEERING_MIN_PULSE}-{config.STEERING_MAX_PULSE}us.")
        logger.info(f"Throttle servo on pin {config.THROTTLE_PIN} configured for {config.THROTTLE_MIN_PULSE}-{config.THROTTLE_MAX_PULSE}us.")

        # Set initial failsafe state
        self._set_servos_failsafe()

    def _map_value(self, value, in_min, in_max, out_min, out_max):
        """Maps a value from one range to another."""
        return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

    def _set_servos_failsafe(self):
        """Writes the failsafe values to the servos."""
        if not self._board:
            return

        steering_failsafe_angle = self._map_value(
            config.STEERING_FAILSAFE_PULSE,
            config.STEERING_MIN_PULSE,
            config.STEERING_MAX_PULSE,
            0,
            180
        )
        throttle_failsafe_angle = self._map_value(
            config.THROTTLE_FAILSAFE_PULSE,
            config.THROTTLE_MIN_PULSE,
            config.THROTTLE_MAX_PULSE,
            0,
            180
        )
        self._steering_pin.write(steering_failsafe_angle)
        self._throttle_pin.write(throttle_failsafe_angle)

    async def run(self):
        """
        Monitors for command timeout and engages failsafe if necessary.
        """
        while True:
            now = asyncio.get_running_loop().time()

            # A real command time is > 0.
            # -1 is initial state.
            # 0 is failsafe active state.
            is_receiving_commands = self._last_command_time > 0 and (now - self._last_command_time) <= config.FAILSAFE_INTERVAL

            if not is_receiving_commands:
                # Failsafe condition is met.

                # Only log the message when we first enter the failsafe state.
                if self._last_command_time != 0:
                     logger.warning(f"Failsafe engaged: No command received for {config.FAILSAFE_INTERVAL}s or initial state.")

                # Apply failsafe and set the state to "failsafe active".
                self._set_servos_failsafe()
                self._last_command_time = 0

            await asyncio.sleep(config.FAILSAFE_LOOP_INTERVAL)

    async def set_steering(self, value):
        """
        Sets the steering servo based on a raw controller value. This is a non-blocking coroutine.
        :param value: The controller value to set (-1000 to 1000).
        """
        self._last_command_time = asyncio.get_running_loop().time()
        if not self._board:
            return

        angle = self._map_value(value, -1000, 1000, 0, 180)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._steering_pin.write, angle)

    async def set_throttle(self, value):
        """
        Sets the throttle servo based on a raw controller value. This is a non-blocking coroutine.
        :param value: The controller value to set (-1000 to 1000).
        """
        self._last_command_time = asyncio.get_running_loop().time()
        if not self._board:
            return

        angle = self._map_value(value, -1000, 1000, 0, 180)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._throttle_pin.write, angle)

    def start(self):
        """Starts the failsafe monitoring task."""
        if not self._task:
            self._task = asyncio.create_task(self.run())
            logger.info("Crawler controller loop started.")

    def close(self):
        """
        Cancels the failsafe task and closes the connection to the Arduino board.
        """
        if self._task:
            self._task.cancel()
            logger.info("Crawler controller loop stopped.")

        logger.info("Closing Arduino connection.")
        if self._board:
            self._board.exit()
