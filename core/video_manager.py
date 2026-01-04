"""
Component for managing the video stream service based on GCS connection status.
"""
import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class VideoStreamManager:
    """
    Monitors a queue for GCS heartbeats and manages the video stream service.
    If heartbeats stop for a configured timeout, it stops the service.
    If they resume, it starts the service.
    """

    def __init__(self, config, heartbeat_queue: asyncio.Queue):
        """
        Initializes the VideoStreamManager.
        :param config: The application configuration object.
        :param heartbeat_queue: The queue to receive GCS heartbeat notifications on.
        """
        self._config = config
        self._heartbeat_queue = heartbeat_queue
        self._service_name = config.VIDEO_SERVICE_NAME
        self._is_running = False
        self._task = None
        self._last_heartbeat_time = 0

    async def _run_systemctl(self, action: str):
        """
        Executes a systemctl command for the managed service.
        :param action: The action to perform ('start', 'stop').
        """
        cmd = f"systemctl --user {action} {self._service_name}"
        logger.info(f"Executing: '{cmd}'")
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)

            await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"Failed to {action} {self._service_name}.")
            else:
                logger.info(f"Successfully executed '{action}' on {self._service_name}.")

        except Exception:
            logger.exception(f"An exception occurred while trying to '{action}' {self._service_name}:")

    async def _start_service(self):
        await self._run_systemctl("start")
        self._is_running = True

    async def _stop_service(self):
        await self._run_systemctl("stop")
        self._is_running = False

    async def run(self):
        """
        The main async loop for the video stream manager.
        """
        logger.info("VideoStreamManager started, monitoring GCS heartbeats.")
        while True:
            try:
                # Purge the queue and update the last heartbeat time
                while not self._heartbeat_queue.empty():
                    self._heartbeat_queue.get_nowait()
                    self._last_heartbeat_time = time.time()

                # Check for connection timeout
                has_timed_out = (time.time() - self._last_heartbeat_time) > self._config.GCS_HEARTBEAT_TIMEOUT

                # If we've timed out and the service is running, stop it.
                if has_timed_out and self._is_running:
                    logger.warning("GCS connection timed out. Stopping video stream.")
                    await self._stop_service()
                # If we have a connection and the service is not running, start it.
                elif not has_timed_out and not self._is_running and self._last_heartbeat_time > 0:
                    logger.info("GCS connection active. Starting video stream.")
                    await self._start_service()

                await asyncio.sleep(self._config.VIDEO_MANAGER_LOOP_SLEEP)

            except asyncio.CancelledError:
                logger.info("VideoStreamManager stopping.")
                break
            except Exception:
                logger.exception("Error in VideoStreamManager loop:")
                await asyncio.sleep(self._config.ERROR_LOOP_SLEEP)

        logger.info("VideoStreamManager stopped.")

    def start(self):
        """Starts the VideoStreamManager's run loop as an asyncio task."""
        self._task = asyncio.create_task(self.run())
        return self._task

    async def close(self):
        """Ensures the managed service is stopped on application shutdown."""
        logger.info("Closing VideoStreamManager, ensuring video service is stopped.")
        if self._is_running:
            await self._stop_service()
