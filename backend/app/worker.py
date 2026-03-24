from __future__ import annotations

import asyncio
import logging

from app.api.deps import get_event_consumer_worker
from app.core.config import settings
from app.db.base import get_session_factory

logger = logging.getLogger('trackme.worker')


async def run_worker() -> None:
    session_factory = get_session_factory()
    worker = get_event_consumer_worker()
    logger.info('Starting TrackMe event worker', extra={'worker_name': settings.worker_name})

    while True:
        async with session_factory() as session:
            try:
                results = await worker.drain(
                    session,
                    worker_name=settings.worker_name,
                    max_events=settings.worker_max_events_per_tick,
                )
                await session.commit()
            except Exception:
                try:
                    await session.commit()
                except Exception:
                    await session.rollback()
                logger.exception('Event worker loop failed')
                await asyncio.sleep(settings.worker_poll_interval_seconds)
                continue

        if results:
            logger.info(
                'Processed queued platform events',
                extra={'worker_name': settings.worker_name, 'processed': len(results)},
            )
        else:
            await asyncio.sleep(settings.worker_idle_sleep_seconds)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
    asyncio.run(run_worker())


if __name__ == '__main__':
    main()
