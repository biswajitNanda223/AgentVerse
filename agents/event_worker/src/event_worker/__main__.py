"""Headless worker: `python -m event_worker`. Use `event_worker.app` when you want probes."""

import asyncio
import logging
import signal

from event_worker.service import build_service
from event_worker.settings import get_settings


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    service = build_service(get_settings())
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, service.request_stop)
    await service.run()


if __name__ == "__main__":
    asyncio.run(main())
