import logging
import signal
import threading
from datetime import timedelta

from sqlalchemy.exc import SQLAlchemyError

from app.application.build_plans import BuildPlans
from app.presentation.composition import build_plans, database_engine, load_settings

logger = logging.getLogger(__name__)


def work(
    builder: BuildPlans, stall_limit: timedelta, poll_seconds: float, stop: threading.Event
) -> None:
    while not stop.is_set():
        try:
            builder.fail_stalled(stall_limit)
            built = builder.build_next()
        except SQLAlchemyError:
            logger.exception("道標の DB の操作に失敗しました")
            built = None
        if built is None:
            stop.wait(poll_seconds)
        else:
            logger.info("道標 %s を %s にしました", built.id, built.status)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = load_settings()
    engine = database_engine(settings)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda signum, frame: stop.set())
    signal.signal(signal.SIGINT, lambda signum, frame: stop.set())
    logger.info("道標の worker を始めます")
    try:
        work(
            build_plans(settings, engine),
            timedelta(minutes=settings.plan_stall_minutes),
            settings.worker_poll_seconds,
            stop,
        )
    finally:
        engine.dispose()
    logger.info("道標の worker を止めました")


if __name__ == "__main__":
    main()
