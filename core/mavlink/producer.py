import asyncio
import logging

from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class MAVLinkProducer(ABC):
    """
    Abstract base class for MAVLink producers.
    """

    def __init__(self, event_bus):
        self._event_bus = event_bus
        self._connection = event_bus.get_connection()
        self._shutdown_event = event_bus.get_shutdown_event()
        self._task = None

    @abstractmethod
    async def run(self):
        """
        The main loop for the producers. This method should be overridden by subclasses.
        """
        raise NotImplementedError

    def start(self):
        """Starts the producers's run loop as an asyncio task."""
        logger.info(f"{self.__class__.__name__} producers started.")
        self._task = asyncio.create_task(self.run())
        return self._task

    def stop(self):
        """Stops the producers's run loop."""
        if self._task:
            self._task.cancel()
        logger.info(f"{self.__class__.__name__} producers stopped.")
