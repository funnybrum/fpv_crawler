import asyncio
import logging

from pymavlink import mavutil

from core.mavlink.producer import MAVLinkProducer

logger = logging.getLogger(__name__)


class HeartbeatProducer(MAVLinkProducer):
    """
    A generic MAVLink producers that sends a periodic HEARTBEAT message.
    """

    def __init__(self, event_bus):
        super().__init__(event_bus)

    async def run(self):
        """
        The main loop that sends a heartbeat every second.
        """
        while not self._shutdown_event.is_set():
            try:
                self._connection.mav.heartbeat_send(
                    mavutil.mavlink.MAV_TYPE_GROUND_ROVER,
                    mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
                    mavutil.mavlink.MAV_MODE_FLAG_MANUAL_INPUT_ENABLED,
                    custom_mode=1,
                    system_status=0,
                )
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in Heartbeat producers loop:")
                await asyncio.sleep(1)
