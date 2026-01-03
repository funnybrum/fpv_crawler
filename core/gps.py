"""
GPS component for providing location data.
"""
import asyncio
import logging

logger = logging.getLogger(__name__)


class GPS:
    """
    In the future, this class will read from a real GPS device.
    For now, it produces mock GPS data and sends it to a queue.
    """

    def __init__(self, config, gps_queue: asyncio.Queue):
        """
        Initializes the GPS component.
        :param config: The application configuration.
        :param gps_queue: The queue to send GPS data to.
        """
        self._config = config
        self._gps_queue = gps_queue
        self._task = None

    async def run(self):
        """
        The main async loop for the GPS component.
        """
        logger.info("GPS component started.")
        while True:
            try:
                # In a real scenario, you would read from a serial/I2C GPS device here.
                # For now, we use the mock location from the config.
                location = {
                    "lat": self._config.MOCK_LAT,
                    "lon": self._config.MOCK_LON
                }

                await self._gps_queue.put(location)
                logger.debug("Produced mock GPS location.")

                # Send GPS data every 5 seconds
                await asyncio.sleep(self._config.GPS_LOOP_SLEEP)
            except asyncio.CancelledError:
                logger.info("GPS component stopping.")
                break
            except Exception:
                logger.exception("Error in GPS loop:")
                # Avoid rapid-fire errors
                await asyncio.sleep(self._config.ERROR_LOOP_SLEEP)
        logger.info("GPS component stopped.")

    def start(self):
        """Starts the GPS component's run loop as an asyncio task."""
        self._task = asyncio.create_task(self.run())
        return self._task
