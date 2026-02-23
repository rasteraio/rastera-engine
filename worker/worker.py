"""
Rastera Engine — Background Worker
APScheduler-based cron runner inside the worker container.

V1 jobs:
  • Nightly demo score refresh (placeholder — logs intent only)
  • Monday 06:00 UTC weekly portfolio report generation (placeholder)

TODO V2:
  • Call /v1/site/analyze for each demo site to keep scores fresh.
  • Iterate tenants → generate PDF summaries → upload to S3 / email.
  • Add real-time POI refresh pipeline (OSM Overpass, Google Places, etc.).
  • Switch to Celery + Redis for distributed task execution.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("rastera.worker")


async def refresh_demo_scores() -> None:
    """
    Re-score all demo sites so the portfolio ranking stays fresh.
    TODO: import and call the scoring pipeline directly, or hit the internal API.
    """
    now = datetime.now(timezone.utc).isoformat()
    logger.info("[%s] Job: refresh_demo_scores — starting (TODO: implement)", now)
    # Placeholder: no-op in V1
    await asyncio.sleep(0)
    logger.info("[%s] Job: refresh_demo_scores — complete", now)


async def generate_weekly_report() -> None:
    """
    Generate a weekly portfolio PDF for each active tenant and store / email it.
    TODO: implement once PDF + S3 + email services are wired.
    """
    now = datetime.now(timezone.utc).isoformat()
    logger.info("[%s] Job: generate_weekly_report — starting (TODO: implement)", now)
    await asyncio.sleep(0)
    logger.info("[%s] Job: generate_weekly_report — complete", now)


async def main() -> None:
    scheduler = AsyncIOScheduler(timezone="UTC")

    # Nightly at 02:00 UTC
    scheduler.add_job(refresh_demo_scores, "cron", hour=2, minute=0, id="refresh_scores")

    # Every Monday at 06:00 UTC
    scheduler.add_job(generate_weekly_report, "cron", day_of_week="mon", hour=6, id="weekly_report")

    scheduler.start()
    logger.info("Rastera worker started. Scheduled jobs: %s", [j.id for j in scheduler.get_jobs()])

    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker shutting down…")
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
