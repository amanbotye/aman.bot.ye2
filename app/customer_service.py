from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Customer,
    TelecomCompany,
    PhoneNumber,
    PhoneStatus,
)


DEFAULT_COMPANIES = [
    ("يمن موبايل", "YEMEN_MOBILE"),
    ("سبأفون", "SABAFON"),
    ("YOU", "YOU"),
    ("Y", "Y"),
]


async def get_or_create_customer(
    db: AsyncSession,
    telegram_user,
) -> Customer:

    result = await db.execute(
        select(Customer).where(
            Customer.telegram_id == telegram_user.id
        )
    )

    customer = result.scalar_one_or_none()

    if customer:
        customer.telegram_username = telegram_user.username
        customer.language_code = (
            telegram_user.language_code or "ar"
        )

        await db.commit()
        await db.refresh(customer)

        return customer

    customer = Customer(
        telegram_id=telegram_user.id,
        telegram_username=telegram_user.username,
        language_code=telegram_user.language_code or "ar",
    )

    db.add(customer)

    await db.commit()
    await db.refresh(customer)

    return customer


async def seed_default_companies(
    db: AsyncSession,
):
    """
    إنشاء شركات الاتصالات الافتراضية إذا لم تكن موجودة.
    لا يحذف ولا يعدل الشركات الموجودة.
    """

    for name, code in DEFAULT_COMPANIES:

        result = await db.execute(
            select(TelecomCompany).where(
                TelecomCompany.code == code
            )
        )

        company = result.scalar_one_or_none()

        if company is None:
            db.add(
                TelecomCompany(
                    name=name,
                    code=code,
                    is_active=True,
                )
            )

    await db.commit()


async def get_active_companies(
    db: AsyncSession,
):
    result = await db.execute(
        select(TelecomCompany)
        .where(
            TelecomCompany.is_active.is_(True)
        )
        .order_by(
            TelecomCompany.sort_order
            if hasattr(TelecomCompany, "sort_order")
            else TelecomCompany.id
        )
    )

    return result.scalars().all()


async def find_phone(
    db: AsyncSession,
    phone_number: str,
):
    result = await db.execute(
        select(PhoneNumber).where(
            PhoneNumber.phone_number == phone_number
        )
    )

    return result.scalar_one_or_none()


async def register_phone(
    db: AsyncSession,
    customer: Customer,
    company: TelecomCompany,
    phone_number: str,
):
    """
    تسجيل الرقم مع منع امتلاكه من أكثر من عميل.
    """

    existing = await find_phone(
        db,
        phone_number,
    )

    if existing:

        if existing.customer_id == customer.id:
            return existing, "owned"

        return existing, "owned_by_other"

    phone = PhoneNumber(
        customer_id=customer.id,
        telecom_company_id=company.id,
        phone_number=phone_number,
        status=PhoneStatus.inactive,
    )

    db.add(phone)

    await db.commit()
    await db.refresh(phone)

    return phone, "created"


async def get_customer_numbers(
    db: AsyncSession,
    customer_id: int,
):
    result = await db.execute(
        select(PhoneNumber)
        .where(
            PhoneNumber.customer_id == customer_id
        )
        .order_by(
            PhoneNumber.created_at.desc()
        )
    )

    return result.scalars().all()


async def get_customer_number_count(
    db: AsyncSession,
    customer_id: int,
) -> int:

    result = await db.execute(
        select(func.count(PhoneNumber.id))
        .where(
            PhoneNumber.customer_id == customer_id
        )
    )

    return int(result.scalar_one() or 0)


async def get_customer_protected_count(
    db: AsyncSession,
    customer_id: int,
) -> int:

    result = await db.execute(
        select(func.count(PhoneNumber.id))
        .where(
            PhoneNumber.customer_id == customer_id,
            PhoneNumber.status == PhoneStatus.active,
        )
    )

    return int(result.scalar_one() or 0)
