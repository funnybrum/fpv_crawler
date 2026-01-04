import asyncio
import logging
import time

from core import config
from core.mavlink.producer import MAVLinkProducer

logger = logging.getLogger(__name__)


class GpsProducer(MAVLinkProducer):
    """
    A MAVLink producers that generates mock GPS data and sends it
    as GLOBAL_POSITION_INT messages.
    """
    def __init__(self, event_bus):
        super().__init__(event_bus)
        self._boot_time = time.time()

    def _get_boot_time_ms(self):
        """Returns the time since producers start in milliseconds."""
        return int((time.time() - self._boot_time) * 1000)

    async def run(self):
        """
        The main loop that periodically generates mock GPS data and sends it.
        """
        while not self._shutdown_event.is_set():
            try:
                # Generate mock location from config
                location = {
                    "lat": config.MOCK_LAT,
                    "lon": config.MOCK_LON
                }
                logger.debug("Produced mock GPS location.")

                # Send the GLOBAL_POSITION_INT message
                self._connection.mav.global_position_int_send(
                    self._get_boot_time_ms(),
                    int(location['lat'] * 1e7),
                    int(location['lon'] * 1e7),
                    10000, 0, 0, 0, 0, 65535
                )
                logger.debug("Sent GLOBAL_POSITION_INT from mock GPS data.")

                await asyncio.sleep(config.GPS_LOOP_SLEEP)

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in GpsProducer loop:")
                await asyncio.sleep(config.ERROR_LOOP_SLEEP)
