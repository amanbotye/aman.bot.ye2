from decimal import Decimal
from sqlalchemy import select
from ..models import SystemSetting
from ..utils import money, safe_int

DEFAULTS = {
    "service_price": "1000.00", "currency": "YER", "service_duration_days": "365",
    "followup_cycle_days": "90", "subscription_safe_until_day": "299", "subscription_near_until_day": "349",
    "subscription_danger_until_day": "365", "followup_safe_until_day": "79", "followup_near_until_day": "84",
    "followup_danger_until_day": "90", "notification_max_attempts": "3", "proof_max_size_mb": "10",
}
NUMERIC = set(DEFAULTS) - {"currency"}

class SettingsService:
    def __init__(self, s): self.s = s
    async def get(self, key):
        if key not in DEFAULTS: raise ValueError("الإعداد غير معروف")
        row = await self.s.scalar(select(SystemSetting).where(SystemSetting.key == key))
        return row.value if row else DEFAULTS[key]
    async def get_int(self, key): return safe_int(await self.get(key), 0)
    async def get_money(self, key="service_price"): return money(await self.get(key))
    async def validate(self, key, value):
        if key not in DEFAULTS: raise ValueError("الإعداد غير معروف")
        value = str(value).strip()
        if key == "service_price":
            amount = money(value)
            if amount <= 0: raise ValueError("السعر يجب أن يكون أكبر من صفر")
            return str(amount)
        if key == "currency":
            if not value.isalpha() or not 3 <= len(value) <= 8: raise ValueError("العملة يجب أن تكون 3-8 أحرف")
            return value.upper()
        minimum = 0 if key in {"subscription_safe_until_day", "followup_safe_until_day"} else 1
        n = safe_int(value, minimum)
        limits = {
            "service_duration_days": (1, 3650), "followup_cycle_days": (1, 3650),
            "subscription_safe_until_day": (0, 3650), "subscription_near_until_day": (1, 3650),
            "subscription_danger_until_day": (1, 3650), "followup_safe_until_day": (0, 3650),
            "followup_near_until_day": (1, 3650), "followup_danger_until_day": (1, 3650),
            "notification_max_attempts": (1, 10), "proof_max_size_mb": (1, 50),
        }
        lo, hi = limits[key]
        if not lo <= n <= hi: raise ValueError(f"القيمة يجب أن تكون بين {lo} و{hi}")
        sub_safe=n if key=="subscription_safe_until_day" else int(await self.get("subscription_safe_until_day"))
        sub_near=n if key=="subscription_near_until_day" else int(await self.get("subscription_near_until_day"))
        sub_danger=n if key=="subscription_danger_until_day" else int(await self.get("subscription_danger_until_day"))
        if not sub_safe < sub_near < sub_danger: raise ValueError("حدود الاشتراك يجب أن تكون متدرجة: أمان < قريب < خطر")
        fu_safe=n if key=="followup_safe_until_day" else int(await self.get("followup_safe_until_day"))
        fu_near=n if key=="followup_near_until_day" else int(await self.get("followup_near_until_day"))
        fu_danger=n if key=="followup_danger_until_day" else int(await self.get("followup_danger_until_day"))
        if not fu_safe < fu_near < fu_danger: raise ValueError("حدود المتابعة يجب أن تكون متدرجة: أمان < قريب < خطر")
        return str(n)
    async def set(self, key, value):
        value = await self.validate(key, value)
        row = await self.s.scalar(select(SystemSetting).where(SystemSetting.key == key).with_for_update())
        if not row: row = SystemSetting(key=key, value=value); self.s.add(row)
        else: row.value = value
        await self.s.flush(); return row
    async def seed_defaults(self):
        for key, value in DEFAULTS.items():
            if not await self.s.scalar(select(SystemSetting).where(SystemSetting.key == key)):
                self.s.add(SystemSetting(key=key, value=value))
        await self.s.flush()
