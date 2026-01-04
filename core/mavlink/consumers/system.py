import logging

from pymavlink import mavutil

from core.mavlink.consumer import MAVLinkConsumer

logger = logging.getLogger(__name__)

class SystemConsumer(MAVLinkConsumer):
    """
    Consumes system-level MAVLink messages like COMMAND_LONG for shutdown.
    """
    def __init__(self, event_bus):
        # Call the superclass constructor to subscribe to the specified message types
        super().__init__(event_bus, ['COMMAND_LONG'])

    async def process_message(self, msg):
        """
        Processes an incoming MAVLink message.
        """
        if msg.command == mavutil.mavlink.MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN:
            logger.warning("Shutdown command received from GCS.")
            self._shutdown_event.set()
