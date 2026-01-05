"""
Handles the core MAVLink connection and acts as a message bus.
"""
import asyncio
import logging

from collections import defaultdict
from pymavlink import mavutil

from core import config

logger = logging.getLogger(__name__)


class MAVLinkEventBus:
    """
    Manages the MAVLink connection, receives all messages, and publishes them
    as events to registered subscribers.
    """

    def __init__(self):
        self._task = None
        self._subscribers = defaultdict(list)
        self._shutdown_event = asyncio.Event()

        connection_string = f'udpout:{config.GROUND_CONTROL_STATION_IP}:{config.MAVLINK_PORT}'
        logger.info(f"Opening MAVLink connection to {connection_string}...")
        self._connection = mavutil.mavlink_connection(
            connection_string,
            source_system=config.MAVLINK_SOURCE_SYSTEM,
            source_component=config.MAVLINK_SOURCE_COMPONENT
        )
        logger.info("MAVLink Event Bus connection established.")

    def subscribe(self, msg_type: str, queue: asyncio.Queue):
        """
        Subscribes an asyncio.Queue to a specific MAVLink message type.
        :param msg_type: The MAVLink message type string (e.g., 'MANUAL_CONTROL').
        :param queue: The asyncio.Queue to which messages will be sent.
        """
        if not isinstance(queue, asyncio.Queue):
            raise ValueError("Subscriber must be an asyncio.Queue.")
        self._subscribers[msg_type].append(queue)
        logger.info(f"Queue subscribed to message type '{msg_type}'")

    def get_connection(self):
        """Provides direct access to the underlying pymavlink connection."""
        return self._connection

    def get_shutdown_event(self):
        """Returns the shutdown event object."""
        return self._shutdown_event

    # --- Main Loops ---

    async def run(self):
        """
        The main async loop for the MAVLink event bus.
        Continuously polls for and dispatches incoming MAVLink messages.
        """
        logger.info("MAVLink event bus started.")
        while not self._shutdown_event.is_set():
            try:
                msg = self._connection.recv_match(blocking=False)
                if msg:
                    msg_type = msg.get_type()
                    if msg_type in self._subscribers:
                        for queue in self._subscribers[msg_type]:
                            await queue.put(msg)

                await asyncio.sleep(config.MAVLINK_RECV_LOOP_SLEEP)
            except asyncio.CancelledError:
                break # Exit loop cleanly on cancellation
            except Exception:
                logger.exception("Error in MAVLink event bus loop:")
                await asyncio.sleep(config.ERROR_LOOP_SLEEP)

        logger.info("MAVLink event bus stopped.")

    def start(self):
        """Starts the MAVLink event bus run loop as an asyncio task."""
        self._task = asyncio.create_task(self.run())
        return self._task

    def close(self):
        """Closes the underlying MAVLink connection."""
        logger.info("Closing MAVLink connection.")
        self._connection.close()
