from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

_scheduler: AsyncIOScheduler | None = None


async def _run_job(config: dict):
    from src.pipeline import try_run_pipeline
    print("[scheduler] Starting scheduled pipeline run...")
    try:
        started = await try_run_pipeline(config)
        if not started:
            print("[scheduler] Pipeline already running, skipping")
    except Exception as e:
        print(f"[scheduler] Pipeline run failed: {e}")


def start(config: dict):
    global _scheduler
    sched_cfg = config.get("scheduler", {})
    if not sched_cfg.get("enabled", True):
        print("[scheduler] Disabled in config")
        return

    daily_at = sched_cfg.get("daily_at", "07:00")
    timezone = sched_cfg.get("timezone", "UTC")
    hour, minute = daily_at.split(":")

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _run_job,
        CronTrigger(hour=int(hour), minute=int(minute), timezone=timezone),
        args=[config],
        id="daily_pipeline",
        replace_existing=True,
    )
    _scheduler.start()
    print(f"[scheduler] Scheduled daily run at {daily_at} {timezone}")


def stop():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
