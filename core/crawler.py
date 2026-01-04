"""
The hardware controller for the crawler.
"""
import asyncio
import logging
from .hardware import ArduinoController

logger = logging.getLogger(__name__)


class Crawler:
    """
    Listens for control messages on a queue and commands the hardware accordingly.
    """

    def __init__(self, config, manual_control_queue: asyncio.Queue):
        """
        Initializes the hardware controller.
        :param config: The application configuration.
        :param manual_control_queue: The queue to listen on for control messages.
        """
        self._config = config
        self._manual_control_queue = manual_control_queue
        self._arduino = ArduinoController(config)
        self._task = None

    async def run(self):
        """
        The main async loop for the hardware controller.
        """
        logger.info("Crawler hardware controller started.")
        while True:
            try:
                # Wait for a message from the MAVLink interface
                msg = await self._manual_control_queue.get()

                # msg.x = Throttle, msg.y = Steering. Values range from -1000 to 1000.
                logger.debug(f"RC -> {msg.to_json()}")

                self._arduino.set_steering(msg.r)
                self._arduino.set_throttle(msg.z)

            except asyncio.CancelledError:
                logger.info("Crawler hardware controller stopping.")
                break
            except Exception:
                logger.exception("Error in Crawler loop:")
                # Avoid rapid-fire errors in case of a persistent issue
                await asyncio.sleep(self._config.ERROR_LOOP_SLEEP)

        logger.info("Crawler hardware controller stopped.")

    def start(self):
        """Starts the crawler's run loop as an asyncio task."""
        self._task = asyncio.create_task(self.run())
        return self._task

    def close(self):
        """Safely shuts down the hardware."""
        self._arduino.close()
