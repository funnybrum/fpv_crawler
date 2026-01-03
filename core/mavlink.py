"""
Handles all MAVLink communication, acting as a central hub.
"""
import asyncio
import time
import logging
from pymavlink import mavutil

logger = logging.getLogger(__name__)


class MAVLinkInterface:
    """
    Manages MAVLink connection, message sending, and receiving.
    Dispatches events to and from other components via async queues.
    """

    def __init__(self, config, manual_control_queue: asyncio.Queue, gps_queue: asyncio.Queue, shutdown_event: asyncio.Event):
        self._config = config
        self._manual_control_queue = manual_control_queue
        self._gps_queue = gps_queue
        self._shutdown_event = shutdown_event
        self._task = None
        self._boot_time = time.time()

        connection_string = f'udpout:{self._config.GROUND_CONTROL_STATION_IP}:{self._config.MAVLINK_PORT}'
        logger.info(f"Opening MAVLink connection to {connection_string}...")
        self._connection = mavutil.mavlink_connection(
            connection_string,
            source_system=self._config.MAVLINK_SOURCE_SYSTEM,
            source_component=self._config.MAVLINK_SOURCE_COMPONENT
        )
        logger.info("MAVLink connection established.")

    def _get_time_boot_ms(self):
        return int((time.time() - self._boot_time) * 1000)

    async def _receive_loop(self):
        """Continuously polls for incoming MAVLink messages."""
        while not self._shutdown_event.is_set():
            try:
                # Use non-blocking recv_match. Returns None immediately if no message.
                msg = self._connection.recv_match(blocking=False)

                if msg: # Only process if a message was actually received
                    msg_type = msg.get_type()
                    if msg_type == 'MANUAL_CONTROL':
                        await self._manual_control_queue.put(msg)

                    elif msg_type == 'COMMAND_LONG' and msg.command == mavutil.mavlink.MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN:
                        logger.warning("Shutdown command received from GCS.")
                        self._shutdown_event.set()
                
                await asyncio.sleep(self._config.MAVLINK_RECV_LOOP_SLEEP)
            except Exception:
                logger.exception("Error in MAVLink receive loop:")
                await asyncio.sleep(self._config.ERROR_LOOP_SLEEP)

    async def _send_loop(self):
        """Continuously sends heartbeats and processes outbound message queues."""
        last_heartbeat_time = 0
        while not self._shutdown_event.is_set():
            try:
                # Send heartbeat every second
                if time.time() - last_heartbeat_time > 1.0:
                    self._connection.mav.heartbeat_send(
                        mavutil.mavlink.MAV_TYPE_GROUND_ROVER,
                        mavutil.mavlink.MAV_AUTOPILOT_GENERIC,
                        mavutil.mavlink.MAV_MODE_FLAG_MANUAL_INPUT_ENABLED, 0, 0)
                    last_heartbeat_time = time.time()
                    logger.info("Hearbeat sent")

                # Check for and process GPS data from the queue
                try:
                    location = self._gps_queue.get_nowait()
                    self._connection.mav.global_position_int_send(
                        self._get_time_boot_ms(),
                        int(location['lat'] * 1e7),
                        int(location['lon'] * 1e7),
                        10000, 0, 0, 0, 0, 65535
                    )
                except asyncio.QueueEmpty:
                    pass  # No GPS data in the queue

                await asyncio.sleep(self._config.MAVLINK_SEND_LOOP_SLEEP)
            except Exception:
                logger.exception("Error in MAVLink send loop:")
                await asyncio.sleep(self._config.ERROR_LOOP_SLEEP)

    async def run(self):
        """The main async loop for the MAVLink interface."""
        logger.info("MAVLink interface started.")
        receive_task = asyncio.create_task(self._receive_loop())
        send_task = asyncio.create_task(self._send_loop())

        try:
            await asyncio.gather(receive_task, send_task)
        except asyncio.CancelledError:
            pass
        finally:
            logger.info("MAVLink interface stopped.")

    def start(self):
        """Starts the MAVLink interface's run loop as an asyncio task."""
        self._task = asyncio.create_task(self.run())
        return self._task

    def close(self):
        """
        Closes the underlying MAVLink connection.
        """
        logger.info("Closing MAVLink connection.")
        self._connection.close()
