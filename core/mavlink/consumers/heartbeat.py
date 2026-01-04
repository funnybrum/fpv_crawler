import asyncio
import logging
import subprocess

from core import config
from core.mavlink.consumer import MAVLinkConsumer

logger = logging.getLogger(__name__)

class HeartbeatConsumer(MAVLinkConsumer):
    """
    Consumes HEARTBEAT messages to trigger actions, such as starting the video stream.
    Once started, the service is not stopped.
    """
    def __init__(self, event_bus):
        super().__init__(event_bus, ['HEARTBEAT'])
        self._service_active = False

    async def _start_service(self):
        """Starts the video stream service asynchronously."""
        logger.info(f"Starting video service: {config.VIDEO_SERVICE_NAME}")
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, 
                lambda: subprocess.run(["systemctl", "--user", "start", config.VIDEO_SERVICE_NAME], check=True)
            )
            self._service_active = True
            logger.info("Video service started successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start video service: {e}")
        except Exception:
            logger.exception("An unexpected error occurred while starting the video service.")

    async def process_message(self, msg):
        """
        Processes an incoming HEARTBEAT message.
        """
        # If the service is already active, do nothing.
        if self._service_active:
            return

        # Check if the heartbeat is from the GCS, not from ourself
        if msg.get_source_system() != config.MAVLINK_SOURCE_SYSTEM:
            logger.info("GCS heartbeat detected. Starting video stream.")
            await self._start_service()
