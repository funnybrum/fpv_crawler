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
        logger.info(f"Connecting to Arduino on port {config.ARDUINO_PORT}...")
        try:
            self._board = pyfirmata2.Arduino(config.ARDUINO_PORT)
            logger.info(f"Connected to Arduino. Firmware: {self._board.firmata_version}")
        except Exception as e:
            logger.error(f"Error connecting to Arduino: {e}")
            # Non-production case, used during development when there is no Arduino connected.
            self._board = None
            return

        # Get pin objects
        self._steering_pin = self._board.get_pin(f'd:{config.STEERING_PIN}:s')
        self._throttle_pin = self._board.get_pin(f'd:{config.THROTTLE_PIN}:s')

        # Configure servo pulse widths
        self._board.servo_config(config.STEERING_PIN, min_pulse=config.SERVO_MIN_PULSE, max_pulse=config.SERVO_MAX_PULSE)
        self._board.servo_config(config.THROTTLE_PIN, min_pulse=config.SERVO_MIN_PULSE, max_pulse=config.SERVO_MAX_PULSE)
        logger.info(f"Servos on pins {config.STEERING_PIN} & {config.THROTTLE_PIN} configured for {config.SERVO_MIN_PULSE}-{config.SERVO_MAX_PULSE}us.")

    def _map_value(self, value, in_min, in_max, out_min, out_max):
        """Maps a value from one range to another."""
        return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

    async def set_steering(self, value):
        """
        Sets the steering servo based on a raw controller value. This is a non-blocking coroutine.
        :param value: The controller value to set (-1000 to 1000).
        """
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
        if not self._board:
            return

        angle = self._map_value(value, -1000, 1000, 0, 180)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._throttle_pin.write, angle)

    def close(self):
        """
        Closes the connection to the Arduino board.
        """
        logger.info("Closing Arduino connection.")
        if self._board:
            self._board.exit()
