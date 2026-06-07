import logging
import time

import click
from sqlalchemy import update

import app
from extensions.ext_database import db
from models.account import UserQuota, UserQuotaPeriod

logger = logging.getLogger(__name__)


@app.celery.task(queue="dataset")
def reset_daily_user_quota_task():
    """Reset quota_used to 0 for all active DAILY quotas. Runs every day at 00:05."""
    _do_reset([UserQuotaPeriod.DAILY], "daily")


@app.celery.task(queue="dataset")
def reset_monthly_user_quota_task():
    """Reset quota_used to 0 for all active MONTHLY quotas. Runs on the 1st of each month at 00:05."""
    _do_reset([UserQuotaPeriod.MONTHLY], "monthly")


def _do_reset(periods: list[UserQuotaPeriod], label: str) -> None:
    click.echo(click.style(f"Start reset_{label}_user_quota_task.", fg="green"))
    start_at = time.perf_counter()
    try:
        result = db.session.execute(
            update(UserQuota)
            .where(
                UserQuota.is_active == True,  # noqa: E712
                UserQuota.period.in_(periods),
            )
            .values(quota_used=0)
        )
        db.session.commit()
        elapsed = time.perf_counter() - start_at
        click.echo(
            click.style(
                f"reset_{label}_user_quota_task done: {result.rowcount} records reset in {elapsed:.3f}s.",
                fg="green",
            )
        )
    except Exception:
        db.session.rollback()
        logger.exception("reset_%s_user_quota_task failed", label)
        raise
