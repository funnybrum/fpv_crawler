import asyncio
import logging
import psutil
import socket

from core import config

logger = logging.getLogger(__name__)


class NetworkManager:
    """
    Manages network interfaces to ensure connectivity with the Ground Control Station.
    """

    def __init__(self, event_bus):
        self._event_bus = event_bus
        self._shutdown_event = event_bus.get_shutdown_event()
        self._task = None
        self._wg_is_up = False

    async def _check_connectivity(self, ip):
        """Checks for connectivity to a given IP address."""
        try:
            proc = await asyncio.create_subprocess_shell(
                f"ping -c 1 {ip}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.wait(), timeout=1.0)
            return proc.returncode == 0
        except asyncio.TimeoutError:
            return False

    async def _get_interfaces(self):
        """Gets a dictionary of network interfaces and their IP addresses."""
        interfaces = {}
        for iface_name, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET: # IPv4 address
                    interfaces[iface_name] = addr.address
        return interfaces

    async def _manage_wireguard(self, up: bool):
        """Starts or stops the WireGuard tunnel."""
        if up and not self._wg_is_up:
            logger.info("Starting WireGuard tunnel...")
            proc = await asyncio.create_subprocess_shell(
                f"wg-quick up {config.WIREGUARD_CONNECTION}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                self._wg_is_up = True
                logger.info("WireGuard tunnel started.")
            else:
                logger.error(f"Failed to start WireGuard tunnel: {stderr.decode()}")
        elif not up and self._wg_is_up:
            logger.info("Stopping WireGuard tunnel...")
            proc = await asyncio.create_subprocess_shell(
                f"wg-quick down {config.WIREGUARD_CONNECTION}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                self._wg_is_up = False
                logger.info("WireGuard tunnel stopped.")
            else:
                logger.error(f"Failed to stop WireGuard tunnel: {stderr.decode()}")

    async def run(self):
        """
        The main loop that manages network interfaces.
        """
        while not self._shutdown_event.is_set():
            try:
                interfaces = await self._get_interfaces()
                home_network_active = any(
                    ip.startswith(config.HOME_NETWORK_INTERFACE_PREFIX) for ip in interfaces.values()
                )

                if home_network_active:
                    logger.debug("Home network is active.")
                    await self._manage_wireguard(up=False)
                else:
                    dongle_active = any(
                        ip == config.DONGLE_INTERFACE_ADDRESS for ip in interfaces.values()
                    )
                    if dongle_active:
                        logger.debug("4G dongle is active.")
                        if await self._check_connectivity(config.CONNECTIVITY_CHECK_IP):
                            await self._manage_wireguard(up=True)
                        else:
                            logger.warning(
                                "4G dongle is active, but no internet connectivity."
                            )
                            await self._manage_wireguard(up=False)
                            await asyncio.sleep(5)
                    else:
                        logger.info("4G dongle is not active. No internet connectivity.")
                        await self._manage_wireguard(up=False)
                        await asyncio.sleep(5)

            except Exception as e:
                logger.exception(f"Error in NetworkManager loop: {e}")

            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break

        await self._manage_wireguard(up=False)
        logger.info("NetworkManager stopped.")

    def start(self):
        """Starts the network manager's run loop as an asyncio task."""
        self._task = asyncio.create_task(self.run())
        return self._task
