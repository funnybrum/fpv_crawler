"""
Main entry point and async orchestrator for the FPV Crawler application.
"""
import asyncio
import signal
import logging
from . import config
from .crawler import Crawler
from .mavlink import MAVLinkInterface
from .gps import GPS

# Setup logger
logger = logging.getLogger(__name__)


async def main():
    """
    Initializes, runs, and orchestrates the crawler's async components.
    """
    shutdown_event = asyncio.Event()

    # --- Setup Signal Handlers ---
    loop = asyncio.get_running_loop()

    def handle_shutdown_signal(sig):
        logger.info(f"Received shutdown signal: {sig.name}")
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_shutdown_signal, sig)

    # --- Create Queues and Components ---
    manual_control_queue = asyncio.Queue()
    gps_queue = asyncio.Queue()

    # Pass the shared shutdown_event to the MAVLink interface
    mavlink_interface = MAVLinkInterface(config, manual_control_queue, gps_queue, shutdown_event)
    crawler = Crawler(config, manual_control_queue)
    gps = GPS(config, gps_queue)

    # --- Start and Monitor Components ---
    logger.info("Starting all components...")
    tasks = [
        mavlink_interface.start(),
        crawler.start(),
        gps.start()
    ]

    # Wait until a shutdown signal is received
    await shutdown_event.wait()

    logger.info("Shutdown initiated...")

    # Gracefully cancel all running tasks
    for task in tasks:
        task.cancel()
    
    # Wait for all tasks to acknowledge cancellation
    await asyncio.gather(*tasks, return_exceptions=True)

    # Perform final cleanup
    crawler.close()
    mavlink_interface.close()
    logger.info("Application has shut down gracefully.")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    )
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.warning("Shutdown requested by user.")
