"""
Main entry point for the FPV Crawler application.
"""
import asyncio
import logging
import signal

from core import config
from core.crawler import CrawlerController
from core.mavlink.bus import MAVLinkEventBus
from core.mavlink.consumers.heartbeat import HeartbeatConsumer
from core.mavlink.consumers.manual_control import ManualControlConsumer
from core.mavlink.consumers.parameters import ParameterConsumer
from core.mavlink.consumers.system import SystemConsumer
from core.mavlink.producers.heartbeat import HeartbeatProducer
from core.mavlink.producers.gps import GpsProducer
from core.network import NetworkManager

logger = logging.getLogger(__name__)


async def main():
    """
    The main entry point of the crawler application.
    Initializes and orchestrates all the different components.
    """

    # --- Initialize Core Components & Bus ---
    mavlink_event_bus = MAVLinkEventBus()
    crawler_controller = CrawlerController()
    network_manager = NetworkManager(mavlink_event_bus)

    # --- Create MAVLink Consumers (Subscribers) ---
    mavlink_system_consumer = SystemConsumer(mavlink_event_bus)
    mavlink_manual_control = ManualControlConsumer(mavlink_event_bus, crawler_controller)
    mavlink_parameter_consumer = ParameterConsumer(mavlink_event_bus)
    mavlink_heartbeat_consumer = HeartbeatConsumer(mavlink_event_bus)

    # --- Create MAVLink Producers ---
    mavlink_heartbeat_producer = HeartbeatProducer(mavlink_event_bus)
    mavlink_gps_producer = GpsProducer(mavlink_event_bus)

    # --- Graceful Shutdown Setup ---
    shutdown_event = mavlink_event_bus.get_shutdown_event()
    loop = asyncio.get_running_loop()

    def signal_handler():
        logger.warning("Shutdown signal received.")
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    # --- Start All Components ---
    # Consumers and Producers are fully managed components with start() methods
    components_to_start = [
        crawler_controller,
        network_manager,
        mavlink_event_bus,
        mavlink_heartbeat_producer,
        mavlink_gps_producer,
        mavlink_system_consumer,
        mavlink_manual_control,
        mavlink_parameter_consumer,
        mavlink_heartbeat_consumer,
    ]

    # Components that need to be explicitly closed
    components_to_close = [mavlink_event_bus, crawler_controller]

    tasks = [comp.start() for comp in components_to_start]
    logger.info("All components started.")

    # --- Wait for Shutdown ---
    await shutdown_event.wait()
    logger.info("Shutdown initiated. Cancelling all component tasks...")

    # --- Clean Up ---
    for task in tasks:
        if task:
            task.cancel()

    # Allow tasks to process cancellation
    await asyncio.gather(*tasks, return_exceptions=True)

    for comp in components_to_close:
        if hasattr(comp, 'close'):
            comp.close()

    logger.info("Application shutdown complete.")


if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    )
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.warning("Shutdown requested by user.")
