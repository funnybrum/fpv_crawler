import logging

from core.crawler import CrawlerController
from core.mavlink.consumer import MAVLinkConsumer

logger = logging.getLogger(__name__)

class ManualControlConsumer(MAVLinkConsumer):
    """
    Consumes MANUAL_CONTROL messages and directly commands the crawler hardware controller.
    """
    def __init__(self, event_bus, hardware_controller: CrawlerController):
        super().__init__(event_bus, ['MANUAL_CONTROL'])
        self._hardware = hardware_controller

    async def process_message(self, msg):
        """
        Processes an incoming MANUAL_CONTROL message and commands the hardware.
        msg.r = Steering, msg.z = Throttle. Values range from -1000 to 1000.
        """
        logger.debug(f"RC -> {msg.to_json()}")
        await self._hardware.set_steering(msg.r)
        await self._hardware.set_throttle(msg.z)
