import asyncio
import logging

from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class MAVLinkConsumer(ABC):
    """
    An abstract base class for components that consume messages from the MAVLink event bus.
    This class implements the Template Method pattern, handling the boilerplate of
    queue creation, subscription, and the message processing loop.
    """
    def __init__(self, event_bus, msg_types: list[str]):
        self._event_bus = event_bus
        self._shutdown_event = event_bus.get_shutdown_event()
        self._internal_queue = asyncio.Queue()
        self._task = None

        # The base class handles its own subscription
        for msg_type in msg_types:
            self._event_bus.subscribe(msg_type, self._internal_queue)

        logger.debug(f"'{self.__class__.__name__}' subscribed to: {msg_types}")

    @abstractmethod
    async def process_message(self, msg):
        """
        The specific logic for processing a received message.
        This is the "template method" to be implemented by subclasses.
        """
        pass

    async def run(self):
        """
        The main processing loop, implemented in the base class.
        It waits for messages on the internal queue and delegates processing
        to the 'process_message' template method.
        """
        logger.info(f"{self.__class__.__name__} is running.")
        while not self._shutdown_event.is_set():
            try:
                msg = await self._internal_queue.get()
                await self.process_message(msg)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception(f"Error in {self.__class__.__name__} loop:")

        logger.info(f"{self.__class__.__name__} stopped.")

    def start(self):
        """
        Starts the consumer's run loop as an asyncio task.
        """
        logger.info(f"Starting {self.__class__.__name__}...")
        self._task = asyncio.create_task(self.run())
        return self._task
