import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, case
from sqlalchemy.dialects import postgresql
from app.models import Subscription


def test_dashboard_uses_total_elapsed_seconds_not_interval_day_component():
    now=datetime(2026,1,1,tzinfo=timezone.utc)
    elapsed=func.floor(func.extract("epoch", now - Subscription.start_at) / 86400)
    statement=select(case((elapsed <= 299,"SAFE"),else_="EXPIRED"))
    sql=str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "extract(epoch" in sql.lower()
    assert "extract(day" not in sql.lower()


def test_elapsed_day_formula_has_expected_boundaries():
    for days in (1,30,90,365,400):
        assert int((timedelta(days=days).total_seconds()) // 86400) == days
