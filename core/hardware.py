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

    def __init__(self, port, steering_pin_num, throttle_pin_num, min_pulse, max_pulse):
        """
        Initializes the connection to the Arduino and configures the servo pins.
        """
        logger.info(f"Connecting to Arduino on port {port}...")
        try:
            self._board = pyfirmata2.Arduino(port)
            logger.info(f"Connected to Arduino. Firmware: {self._board.firmata_version}")
        except Exception as e:
            logger.error(f"Error connecting to Arduino: {e}")
            raise

        # Get pin objects
        self._steering_pin = self._board.get_pin(f'd:{steering_pin_num}:s')
        self._throttle_pin = self._board.get_pin(f'd:{throttle_pin_num}:s')

        # Configure servo pulse widths
        self._board.servo_config(steering_pin_num, min_pulse=min_pulse, max_pulse=max_pulse)
        self._board.servo_config(throttle_pin_num, min_pulse=min_pulse, max_pulse=max_pulse)
        logger.info(f"Servos on pins {steering_pin_num} & {throttle_pin_num} configured for {min_pulse}-{max_pulse}us.")

    def _map_value(self, value, in_min, in_max, out_min, out_max):
        """Maps a value from one range to another."""
        return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

    def set_steering(self, value):
        """
        Sets the steering servo based on a raw controller value.
        :param value: The controller value to set (-1000 to 1000).
        """
        angle = self._map_value(value, -1000, 1000, 0, 180)
        self._steering_pin.write(angle)

    def set_throttle(self, value):
        """
        Sets the throttle servo based on a raw controller value.
        :param value: The controller value to set (-1000 to 1000).
        """
        angle = self._map_value(value, -1000, 1000, 0, 180)
        self._throttle_pin.write(angle)

    def close(self):
        """
        Closes the connection to the Arduino board.
        """
        logger.info("Closing Arduino connection.")
        self._board.exit()
