from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import SystemSetting
DEFAULTS={'service_price':'1000','currency':'YER','service_duration_days':'365','followup_cycle_days':'90','subscription_safe_until_day':'299','subscription_near_until_day':'349','subscription_danger_until_day':'365','followup_safe_until_day':'79','followup_near_until_day':'84','followup_danger_until_day':'90','notification_retry_max':'3'}
async def seed_defaults(db):
    for k,v in DEFAULTS.items():
        if not (await db.execute(select(SystemSetting).where(SystemSetting.key==k))).scalar_one_or_none(): db.add(SystemSetting(key=k,value=v))
    await db.commit()
async def get(db,key,default=None):
    x=(await db.execute(select(SystemSetting).where(SystemSetting.key==key))).scalar_one_or_none(); return x.value if x else default
async def get_int(db,key,default):
    try:return int(await get(db,key,str(default)))
    except (TypeError,ValueError):return default
async def get_decimal(db,key,default):
    try:return Decimal(await get(db,key,str(default)))
    except Exception:return Decimal(str(default))
async def set_value(db,key,value,description=None):
    x=(await db.execute(select(SystemSetting).where(SystemSetting.key==key))).scalar_one_or_none()
    if x: x.value=str(value); x.description=description or x.description
    else: db.add(SystemSetting(key=key,value=str(value),description=description))
