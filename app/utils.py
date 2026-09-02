import re


ARABIC_DIGITS = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹",
    "01234567890123456789",
)


def normalize_phone(phone: str) -> str:
    """
    توحيد صيغة رقم الهاتف اليمني.
    أمثلة:
    771234567
    967771234567
    00967771234567
    +967771234567

    النتيجة:
    +967771234567
    """

    if not phone:
        return ""

    phone = phone.strip().translate(ARABIC_DIGITS)

    # حذف المسافات والرموز الشائعة
    phone = re.sub(r"[\s\-().]", "", phone)

    if phone.startswith("00"):
        phone = "+" + phone[2:]

    if phone.startswith("967"):
        phone = "+" + phone

    if phone.startswith("7") and len(phone) == 9:
        phone = "+967" + phone

    return phone


def is_valid_yemeni_phone(phone: str) -> bool:
    """
    رقم يمني محمول:
    +967 ثم 9 أرقام تبدأ بـ 7.
    """

    return bool(
        re.fullmatch(r"\+9677\d{8}", phone or "")
    )


def normalize_name(name: str) -> str:
    return " ".join((name or "").strip().split())


def is_valid_full_name(name: str) -> bool:
    """
    لا نفرض عدد كلمات صارم حتى لا نرفض أسماء عربية صحيحة.
    """
    return len(normalize_name(name)) >= 2
