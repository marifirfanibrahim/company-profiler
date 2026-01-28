"""
periodic seeding scheduler
called from startup
run from seeder
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit
import datetime

from backend.configuration.seeding import (
    SEED_INTERVAL_MINUTES,
    SEED_ENTITY_UPDATE_INTERVAL_MINUTES,
    SEED_ENTITY_UPDATE_ENABLED,
    SEED_START_IMMEDIATELY,
    SEED_ENV,
    SEED_EXPANSION_PROMOTION_ENABLED,
    SEED_EXPANSION_PROMOTION_INTERVAL_MINUTES,
)
from backend.data.seeder.seed_chromadb import run_seed_rounds
from backend.data.seeder.update_seed_entities import build_seed_entities
from backend.helpers.logic.seed_helpers import promote_seed_entity_candidates


# ==================== STATE ====================

# store scheduler handle
_scheduler = None


def start_scheduler():
    # start scheduler singleton
    global _scheduler

    # stop on active scheduler
    if _scheduler is not None:
        print("[SCHEDULER] already running")
        return _scheduler

    def _seed_job_local():
        # run seed job
        print("[SCHEDULER] running seed job")
        run_seed_rounds(env=SEED_ENV)
        print("[SCHEDULER] seed job completed")

    def _update_entities_local():
        # run seed entity update
        print("[SCHEDULER] updating seed entities")
        build_seed_entities(env=SEED_ENV)
        print("[SCHEDULER] seed entities updated")

    def _promote_candidates_local():
        # promote candidates into seed list
        stats = promote_seed_entity_candidates()

        # read promoted count
        promoted = int(stats.get("promoted", 0))

        # print promotion status
        if promoted > 0:
            print(
                "[SCHEDULER] seed expansion promoted "
                f"{promoted} entities "
                f"(candidates_total={stats.get('candidates_total', 0)}, seed_total={stats.get('seed_total', 0)})"
            )

    # create scheduler instance
    _scheduler = BackgroundScheduler()

    # read schedule settings
    seed_interval = SEED_INTERVAL_MINUTES
    entity_interval = SEED_ENTITY_UPDATE_INTERVAL_MINUTES
    start_immediately = SEED_START_IMMEDIATELY
    env = SEED_ENV

    # build seed trigger
    seed_trigger = IntervalTrigger(minutes=seed_interval)

    # compute first run
    first_run = datetime.datetime.now() if start_immediately else None

    # register seed job
    _scheduler.add_job(
        _seed_job_local,
        seed_trigger,
        id="seed_job",
        replace_existing=True,
        next_run_time=first_run,
    )

    # register entities job
    if SEED_ENTITY_UPDATE_ENABLED and entity_interval > 0:
        # build entities trigger
        entities_trigger = IntervalTrigger(minutes=entity_interval)

        # register entities job
        _scheduler.add_job(
            _update_entities_local,
            entities_trigger,
            id="seed_entities_job",
            replace_existing=True,
            next_run_time=first_run,
        )

    # register promotion job
    if SEED_EXPANSION_PROMOTION_ENABLED and int(SEED_EXPANSION_PROMOTION_INTERVAL_MINUTES) > 0:
        # build promotion trigger
        promote_trigger = IntervalTrigger(minutes=int(SEED_EXPANSION_PROMOTION_INTERVAL_MINUTES))

        # register promotion job
        _scheduler.add_job(
            _promote_candidates_local,
            promote_trigger,
            id="seed_candidate_promotion_job",
            replace_existing=True,
            next_run_time=first_run,
        )

    # start scheduler thread
    _scheduler.start()

    # print scheduler status
    print(
        f"[SCHEDULER] started: seed_interval={seed_interval}, "
        f"entities_interval={entity_interval if SEED_ENTITY_UPDATE_ENABLED else 'disabled'}, "
        f"promote_interval={SEED_EXPANSION_PROMOTION_INTERVAL_MINUTES if SEED_EXPANSION_PROMOTION_ENABLED else 'disabled'}, "
        f"env={env}"
    )

    # register shutdown hook
    atexit.register(lambda: _scheduler.shutdown(wait=False))

    # return scheduler handle
    return _scheduler