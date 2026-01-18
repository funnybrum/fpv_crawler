import asyncio
import logging

from pymavlink import mavutil

from core import config
from core.mavlink.consumer import MAVLinkConsumer

logger = logging.getLogger(__name__)

class ParameterConsumer(MAVLinkConsumer):
    """
    Consumes and responds to MAVLink parameter protocol messages.
    """

    def __init__(self, event_bus):
        super().__init__(event_bus, ['PARAM_REQUEST_LIST', 'PARAM_SET', 'PARAM_REQUEST_READ'])
        self._connection = event_bus.get_connection()

        self._params = {
            "SYSID_THISMAV": float(config.MAVLINK_SOURCE_SYSTEM),
            "RC1_MIN": 1000.0, "RC1_MAX": 2000.0, "RC1_TRIM": 1500.0, "RC1_DZ": 20.0,
            "RC2_MIN": 1000.0, "RC2_MAX": 2000.0, "RC2_TRIM": 1500.0, "RC2_DZ": 20.0,
            "RC3_MIN": 1000.0, "RC3_MAX": 2000.0, "RC3_TRIM": 1500.0, "RC3_DZ": 20.0,
            "RC_MAP_ROLL": 1.0,
            "RC_MAP_PITCH": 2.0,
            "RC_MAP_THROTTLE": 3.0,
            "FLTMODE_CH": 0.0,
            "MODE1": 1.0,
        }
        self._params_bytes = {k.encode('utf-8'): v for k, v in self._params.items()}

    def _send_param(self, param_name):
        if param_name in self._params:
            param_value = self._params[param_name]
            param_name_bytes = param_name.encode('utf-8')
            self._connection.mav.param_value_send(
                param_name_bytes,
                param_value,
                mavutil.mavlink.MAV_PARAM_TYPE_REAL32,
                len(self._params),
                list(self._params.keys()).index(param_name)
            )

            logger.debug(f"Sent param {param_name} = {param_value}")

    async def _send_all_params(self):
        logger.info(f"Sending all {len(self._params)} parameters to GCS.")
        for param_name in self._params:
            self._send_param(param_name)
            await asyncio.sleep(0.02)

    async def process_message(self, msg):
        """
        Processes an incoming MAVLink parameter-related message.
        """
        if msg.get_type() == 'PARAM_REQUEST_LIST':
            asyncio.create_task(self._send_all_params())
        elif msg.get_type() == 'PARAM_SET':
            param_id_bytes = msg.param_id.strip(b'\x00')
            if param_id_bytes in self._params_bytes:
                param_id = param_id_bytes.decode('utf-8')
                self._params[param_id] = msg.param_value
                logger.info(f"Set param {param_id} to {msg.param_value}")
                self._send_param(param_id)
        elif msg.get_type() ==  'PARAM_REQUEST_READ':
            param_id_bytes = msg.param_id.strip(b'\x00')
            if param_id_bytes in self._params_bytes:
                self._send_param(param_id_bytes.decode('utf-8'))
            else:
                param_id = param_id_bytes.decode('utf-8')
                self._connection.mav.param_value_send(
                    param_id_bytes, 0.0, mavutil.mavlink.MAV_PARAM_TYPE_REAL32,
                    len(self._params), 0xFFFF
                )
                logger.info(f"Responded to request for unknown param: {param_id}")
