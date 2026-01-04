"""
Han dles all MAVLink communication, acting as a central hub.
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

    def __init__(self, config, manual_control_queue: asyncio.Queue, gps_queue: asyncio.Queue, shutdown_event: asyncio.Event, heartbeat_queue: asyncio.Queue):
        self._config = config
        self._manual_control_queue = manual_control_queue
        self._gps_queue = gps_queue
        self._shutdown_event = shutdown_event
        self._heartbeat_queue = heartbeat_queue
        self._task = None
        self._boot_time = time.time()

        # --- Parameter Store ---
        self._params = {
            # Dynamically set from config to ensure consistency
            "SYSID_THISMAV": float(config.MAVLINK_SOURCE_SYSTEM),
        }
        # Convert param names to bytes for efficient comparison
        self._params_bytes = {k.encode('utf-8'): v for k, v in self._params.items()}

        # --- Message Handler Dispatch Table ---
        self._message_handlers = {
            'HEARTBEAT': self._handle_heartbeat,
            'MANUAL_CONTROL': self._handle_manual_control,
            'COMMAND_LONG': self._handle_command_long,
            'PARAM_REQUEST_LIST': self._handle_param_request_list,
            'PARAM_SET': self._handle_param_set,
            'PARAM_REQUEST_READ': self._handle_param_request_read,
        }

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

    async def _handle_heartbeat(self, msg):
        # If we receive a heartbeat from the GCS, forward it to the video manager
        if msg.get_srcSystem != self._config.MAVLINK_SOURCE_SYSTEM:
            await self._heartbeat_queue.put("gcs_heartbeat")

    async def _handle_manual_control(self, msg):
        await self._manual_control_queue.put(msg)

    def _handle_command_long(self, msg):
        if msg.command == mavutil.mavlink.MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN:
            logger.warning("Shutdown command received from GCS.")
            self._shutdown_event.set()

    def _handle_param_request_list(self, msg):
        # GCS has requested the full parameter list
        asyncio.create_task(self._send_all_params())

    def _handle_param_set(self, msg):
        # GCS is setting a parameter value
        param_id_bytes = msg.param_id.strip(b'\x00')
        if param_id_bytes in self._params_bytes:
            param_id = param_id_bytes.decode('utf-8')
            self._params[param_id] = msg.param_value
            logger.info(f"Set param {param_id} to {msg.param_value}")
            # Respond with the updated parameter value to confirm
            self._send_param(param_id)

    def _handle_param_request_read(self, msg):
        # GCS is requesting a single parameter
        param_id_bytes = msg.param_id.strip(b'\x00')
        if param_id_bytes in self._params_bytes:
            self._send_param(param_id_bytes.decode('utf-8'))
        else:
            # Parameter not found, send a PARAM_VALUE with param_index = -1
            param_id = param_id_bytes.decode('utf-8')
            self._connection.mav.param_value_send(
                param_id_bytes,
                0.0, # Value is typically 0 for non-existent params
                mavutil.mavlink.MAV_PARAM_TYPE_REAL32,
                len(self._params),
                0xFFFF # param_index = -1 (0xFFFF) for non-existent parameter
            )
            logger.info(f"Responded to request for unknown param: {param_id}")

    # --- Main Loops ---

    async def _receive_loop(self):
        """Continuously polls for and dispatches incoming MAVLink messages."""
        while not self._shutdown_event.is_set():
            try:
                msg = self._connection.recv_match(blocking=False)
                if msg:
                    handler = self._message_handlers.get(msg.get_type())
                    if handler:
                        # Handle both sync and async handlers
                        if asyncio.iscoroutinefunction(handler):
                            await handler(msg)
                        else:
                            handler(msg)
                
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
                        mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
                        mavutil.mavlink.MAV_MODE_FLAG_MANUAL_INPUT_ENABLED,
                        custom_mode=1, # ArduRover Manual Mode
                        system_status=0)
                    last_heartbeat_time = time.time()

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

    def _send_param(self, param_name):
        """Sends a single parameter value to the GCS."""
        if param_name in self._params:
            param_value = self._params[param_name]
            param_name_bytes = param_name.encode('utf-8')
            param_count = len(self._params)
            param_index = list(self._params.keys()).index(param_name)

            self._connection.mav.param_value_send(
                param_name_bytes,
                param_value,
                mavutil.mavlink.MAV_PARAM_TYPE_REAL32,
                param_count,
                param_index
            )
            logger.debug(f"Sent param {param_name} ({param_index}/{param_count}) = {param_value}")

    async def _send_all_params(self):
        """Sends all parameters to the GCS, with a small delay between each."""
        logger.info(f"Sending all {len(self._params)} parameters to GCS.")
        for param_name in self._params:
            self._send_param(param_name)
            await asyncio.sleep(0.02) # Short delay to prevent flooding

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
