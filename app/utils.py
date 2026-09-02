import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

YEMEN_PREFIX = "+967"

def normalize_yemen_phone(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("رقم الهاتف اليمني غير صحيح.")
    raw = re.sub(r"[\s().-]", "", value.strip())
    if raw.startswith("00"):
        raw = "+" + raw[2:]
    if raw.startswith("967"):
        raw = "+" + raw
    if raw.startswith("0"):
        raw = "+967" + raw[1:]
    elif re.fullmatch(r"7\d{8}", raw):
        raw = "+967" + raw
    if not re.fullmatch(r"\+9677\d{8}", raw):
        raise ValueError("رقم الهاتف اليمني غير صحيح. مثال: 771234567")
    return raw

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def money(value) -> Decimal:
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("قيمة مالية غير صحيحة") from exc
    if amount < 0:
        raise ValueError("القيمة المالية لا يمكن أن تكون سالبة")
    return amount

def safe_int(value: str, minimum=0) -> int:
    try:
        n = int(value)
    except (ValueError, TypeError) as exc:
        raise ValueError("القيمة يجب أن تكون رقمًا صحيحًا") from exc
    if n < minimum:
        raise ValueError(f"القيمة يجب ألا تقل عن {minimum}")
    return n
