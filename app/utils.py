from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json, re, secrets

ARABIC_DIGITS=str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹','01234567890123456789')
def utcnow(): return datetime.now(timezone.utc)
def normalize_name(value:str)->str: return ' '.join((value or '').strip().split())
def is_valid_full_name(value:str)->bool:
    n=normalize_name(value); return 2 <= len(n) <= 255 and any(c.isalpha() for c in n)
def normalize_phone(value:str)->str:
    s=(value or '').strip().translate(ARABIC_DIGITS)
    s=re.sub(r'[\s\-().]','',s)
    if s.startswith('00'): s='+'+s[2:]
    if s.startswith('+967'): return s
    if s.startswith('967'): return '+'+s
    if s.startswith('7') and len(s)==9: return '+967'+s
    return s
def is_valid_yemeni_phone(value:str)->bool: return bool(re.fullmatch(r'\+9677\d{8}',value or ''))
def display_phone(value:str)->str: return value[4:] if value.startswith('+967') else value
def parse_decimal(value:str)->Decimal:
    try:
        d=Decimal(str(value).strip());
        if not d.is_finite() or d<0: raise InvalidOperation
        return d
    except InvalidOperation as e: raise ValueError('Invalid amount') from e
def payment_code()->str: return 'AMAN-'+secrets.token_hex(3).upper()
def ticket_code()->str: return 'TKT-'+secrets.token_hex(3).upper()
def json_dumps(data)->str: return json.dumps(data, ensure_ascii=False, default=str, sort_keys=True)
def days_remaining(end:datetime|None, now:datetime|None=None)->int:
    if not end: return 0
    now=now or utcnow(); return max(0,(end-now).days)
def setting_int(value:str, default:int)->int:
    try:return int(value)
    except (TypeError,ValueError):return default
