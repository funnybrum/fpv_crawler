"""
Handles hardware control for the crawler, specifically the Arduino connection
for controlling servos.
"""
import logging
import pyfirmata2

logger = logging.getLogger(__name__)


class ArduinoController:
    """
    Manages the connection and communication with the Arduino board via pyfirmata2.
    """

    def __init__(self, config):
        """
        Initializes the connection to the Arduino and configures the servo pins.
        :param config: The application configuration object.
        """
        self._config = config
        logger.info(f"Connecting to Arduino on port {self._config.ARDUINO_PORT}...")
        try:
            self._board = pyfirmata2.Arduino(self._config.ARDUINO_PORT)
            logger.info(f"Connected to Arduino. Firmware: {self._board.firmata_version}")
        except Exception as e:
            logger.error(f"Error connecting to Arduino: {e}")
            # Non-production case, used during development when there is no Arduino connected.
            self._board = None
            return

        # Get pin objects
        self._steering_pin = self._board.get_pin(f'd:{self._config.STEERING_PIN}:s')
        self._throttle_pin = self._board.get_pin(f'd:{self._config.THROTTLE_PIN}:s')

        # Configure servo pulse widths
        self._board.servo_config(self._config.STEERING_PIN, min_pulse=self._config.SERVO_MIN_PULSE, max_pulse=self._config.SERVO_MAX_PULSE)
        self._board.servo_config(self._config.THROTTLE_PIN, min_pulse=self._config.SERVO_MIN_PULSE, max_pulse=self._config.SERVO_MAX_PULSE)
        logger.info(f"Servos on pins {self._config.STEERING_PIN} & {self._config.THROTTLE_PIN} configured for {self._config.SERVO_MIN_PULSE}-{self._config.SERVO_MAX_PULSE}us.")

    def _map_value(self, value, in_min, in_max, out_min, out_max):
        """Maps a value from one range to another."""
        return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

    def set_steering(self, value):
        """
        Sets the steering servo based on a raw controller value.
        :param value: The controller value to set (-1000 to 1000).
        """
        if not self._board:
            return

        angle = self._map_value(value, -1000, 1000, 0, 180)
        self._steering_pin.write(angle)

    def set_throttle(self, value):
        """
        Sets the throttle servo based on a raw controller value.
        :param value: The controller value to set (-1000 to 1000).
        """
        if not self._board:
            return

        angle = self._map_value(value, -1000, 1000, 0, 180)
        self._throttle_pin.write(angle)

    def close(self):
        """
        Closes the connection to the Arduino board.
        """
        logger.info("Closing Arduino connection.")
        if self._board:
            self._board.exit()
