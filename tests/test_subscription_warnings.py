from datetime import timedelta
from app.scheduler.subscription_jobs import warning_day_for_remaining

def test_warning_boundaries_are_inclusive_and_recover_from_late_scheduler_runs():
    assert warning_day_for_remaining(timedelta(days=30)) == 30
    assert warning_day_for_remaining(timedelta(days=29, seconds=86399)) == 30
    assert warning_day_for_remaining(timedelta(days=7)) == 7
    assert warning_day_for_remaining(timedelta(days=3)) == 3
    assert warning_day_for_remaining(timedelta(days=1)) == 1
    assert warning_day_for_remaining(timedelta(seconds=1)) == 1
    assert warning_day_for_remaining(timedelta(0)) is None
    assert warning_day_for_remaining(timedelta(days=-1)) is None
