from datetime import timedelta
from ..utils import utcnow


class FollowupService:
    DEFAULT_SAFE = 79
    DEFAULT_NEAR = 84
    DEFAULT_DANGER = 90
    DEFAULT_CYCLE = 90

    def __init__(self, settings=None):
        self.settings = settings

    async def _thresholds(self):
        if not self.settings:
            return self.DEFAULT_SAFE, self.DEFAULT_NEAR, self.DEFAULT_DANGER
        return (
            await self.settings.get_int("followup_safe_until_day"),
            await self.settings.get_int("followup_near_until_day"),
            await self.settings.get_int("followup_danger_until_day"),
        )

    async def cycle_days(self):
        if not self.settings:
            return self.DEFAULT_CYCLE
        return await self.settings.get_int("followup_cycle_days")

    async def classify(self, cycle_start, cycle_end, now=None):
        now = now or utcnow()
        safe, near, danger = await self._thresholds()
        # At the exact cycle_end instant the cycle is still in the DANGER band;
        # only a timestamp strictly after cycle_end is EXPIRED.
        if now > cycle_end:
            return "EXPIRED"
        elapsed = max(0, (now - cycle_start).days)
        if elapsed <= safe:
            return "SAFE"
        if elapsed <= near:
            return "NEAR"
        if elapsed <= danger:
            return "DANGER"
        return "EXPIRED"

    async def next_cycle(self, start, days=None):
        if days is None:
            days = await self.cycle_days()
        return start + timedelta(days=days)
