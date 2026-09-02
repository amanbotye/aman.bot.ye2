from __future__ import annotations
from datetime import datetime, timezone
import enum
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase): pass

def utcnow(): return datetime.now(timezone.utc)

class StrEnum(str, enum.Enum): pass
class UserStatus(StrEnum): active='active'; blocked='blocked'
class PhoneStatus(StrEnum): active='active'; inactive='inactive'; suspended='suspended'; cancelled='cancelled'
class SubscriptionStatus(StrEnum): active='active'; inactive='inactive'; expired='expired'; suspended='suspended'; cancelled='cancelled'
class PaymentStatus(StrEnum): pending='pending'; approved='approved'; rejected='rejected'; cancelled='cancelled'
class FollowupStatus(StrEnum): upcoming='upcoming'; due='due'; overdue='overdue'; completed='completed'; cancelled='cancelled'
class SupportStatus(StrEnum): new='new'; open='open'; closed='closed'
class NotificationStatus(StrEnum): pending='pending'; sent='sent'; failed='failed'; cancelled='cancelled'

class Customer(Base):
    __tablename__='customers'
    id: Mapped[int]=mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int]=mapped_column(BigInteger, unique=True, index=True)
    telegram_username: Mapped[str|None]=mapped_column(String(255))
    full_name: Mapped[str|None]=mapped_column(String(255))
    phone: Mapped[str|None]=mapped_column(String(50))
    status: Mapped[UserStatus]=mapped_column(default=UserStatus.active)
    language_code: Mapped[str|None]=mapped_column(String(10), default='ar')
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    phone_numbers: Mapped[list['PhoneNumber']]=relationship(back_populates='customer')

class TelecomCompany(Base):
    __tablename__='telecom_companies'
    id: Mapped[int]=mapped_column(Integer, primary_key=True)
    name: Mapped[str]=mapped_column(String(100), nullable=False)
    code: Mapped[str]=mapped_column(String(50), unique=True, nullable=False)
    is_active: Mapped[bool]=mapped_column(Boolean, default=True)
    sort_order: Mapped[int]=mapped_column(Integer, default=0)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    phone_numbers: Mapped[list['PhoneNumber']]=relationship(back_populates='telecom_company')

class PhoneNumber(Base):
    __tablename__='phone_numbers'
    __table_args__=(UniqueConstraint('phone_number', name='uq_phone_number_global'), Index('ix_phone_customer','customer_id'))
    id: Mapped[int]=mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int]=mapped_column(ForeignKey('customers.id', ondelete='CASCADE'))
    telecom_company_id: Mapped[int]=mapped_column(ForeignKey('telecom_companies.id'))
    phone_number: Mapped[str]=mapped_column(String(50), nullable=False, index=True)
    status: Mapped[PhoneStatus]=mapped_column(default=PhoneStatus.inactive)
    last_recharge_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    validity_expires_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    protection_due_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    confiscation_risk_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    notes: Mapped[str|None]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    customer: Mapped['Customer']=relationship(back_populates='phone_numbers')
    telecom_company: Mapped['TelecomCompany']=relationship(back_populates='phone_numbers')

class Subscription(Base):
    __tablename__='subscriptions'
    id: Mapped[int]=mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int]=mapped_column(ForeignKey('customers.id', ondelete='CASCADE'))
    phone_number_id: Mapped[int]=mapped_column(ForeignKey('phone_numbers.id', ondelete='CASCADE'))
    plan_name: Mapped[str]=mapped_column(String(100), default='حماية أساسية')
    price: Mapped[object]=mapped_column(Numeric(12,2), nullable=False)
    currency: Mapped[str]=mapped_column(String(10), default='YER')
    duration_days: Mapped[int]=mapped_column(Integer, default=365)
    duration_months: Mapped[int]=mapped_column(Integer, default=12)
    starts_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    status: Mapped[SubscriptionStatus]=mapped_column(default=SubscriptionStatus.inactive)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class PaymentMethod(Base):
    __tablename__='payment_methods'
    id: Mapped[int]=mapped_column(Integer, primary_key=True)
    name: Mapped[str]=mapped_column(String(100), nullable=False)
    account_name: Mapped[str|None]=mapped_column(String(255))
    account_number: Mapped[str|None]=mapped_column(String(100))
    instructions: Mapped[str|None]=mapped_column(Text)
    proof_required: Mapped[bool]=mapped_column(Boolean, default=False)
    is_active: Mapped[bool]=mapped_column(Boolean, default=True)
    sort_order: Mapped[int]=mapped_column(Integer, default=0)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class PaymentRequest(Base):
    __tablename__='payment_requests'
    __table_args__=(Index('ix_payment_pending_phone','customer_id','phone_number_id','status'),)
    id: Mapped[int]=mapped_column(Integer, primary_key=True)
    payment_code: Mapped[str]=mapped_column(String(50), unique=True, index=True)
    customer_id: Mapped[int]=mapped_column(ForeignKey('customers.id', ondelete='CASCADE'))
    phone_number_id: Mapped[int]=mapped_column(ForeignKey('phone_numbers.id'))
    subscription_id: Mapped[int|None]=mapped_column(ForeignKey('subscriptions.id'))
    payment_method_id: Mapped[int]=mapped_column(ForeignKey('payment_methods.id'))
    amount: Mapped[object]=mapped_column(Numeric(12,2), nullable=False)
    currency: Mapped[str]=mapped_column(String(10), nullable=False)
    transaction_reference: Mapped[str]=mapped_column(String(255), nullable=False)
    proof_file_url: Mapped[str|None]=mapped_column(Text)
    proof_file_type: Mapped[str|None]=mapped_column(String(30))
    status: Mapped[PaymentStatus]=mapped_column(default=PaymentStatus.pending)
    rejection_reason: Mapped[str|None]=mapped_column(Text)
    submitted_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)
    reviewed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[int|None]=mapped_column(BigInteger)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class Followup(Base):
    __tablename__='followups'
    id: Mapped[int]=mapped_column(Integer, primary_key=True)
    phone_number_id: Mapped[int]=mapped_column(ForeignKey('phone_numbers.id', ondelete='CASCADE'))
    subscription_id: Mapped[int|None]=mapped_column(ForeignKey('subscriptions.id'))
    previous_followup_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[FollowupStatus]=mapped_column(default=FollowupStatus.upcoming)
    amount_paid: Mapped[object|None]=mapped_column(Numeric(12,2))
    payment_method: Mapped[str|None]=mapped_column(String(100))
    payment_reference: Mapped[str|None]=mapped_column(String(255))
    completed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    completed_by: Mapped[int|None]=mapped_column(BigInteger)
    notes: Mapped[str|None]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class SupportTicket(Base):
    __tablename__='support_tickets'
    id: Mapped[int]=mapped_column(Integer, primary_key=True)
    ticket_code: Mapped[str]=mapped_column(String(50), unique=True, index=True)
    customer_id: Mapped[int]=mapped_column(ForeignKey('customers.id', ondelete='CASCADE'))
    subject: Mapped[str]=mapped_column(String(255))
    status: Mapped[SupportStatus]=mapped_column(default=SupportStatus.new)
    assigned_to: Mapped[int|None]=mapped_column(BigInteger)
    last_message_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class SupportMessage(Base):
    __tablename__='support_messages'
    id: Mapped[int]=mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int]=mapped_column(ForeignKey('support_tickets.id', ondelete='CASCADE'))
    sender_telegram_id: Mapped[int]=mapped_column(BigInteger)
    sender_is_admin: Mapped[bool]=mapped_column(Boolean, default=False)
    text: Mapped[str|None]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)

class FAQ(Base):
    __tablename__='faqs'
    id: Mapped[int]=mapped_column(Integer, primary_key=True)
    question: Mapped[str]=mapped_column(String(500))
    answer: Mapped[str]=mapped_column(Text)
    is_active: Mapped[bool]=mapped_column(Boolean, default=True)
    sort_order: Mapped[int]=mapped_column(Integer, default=0)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class Notification(Base):
    __tablename__='notifications'
    __table_args__=(UniqueConstraint('dedupe_key', name='uq_notification_dedupe'),)
    id: Mapped[int]=mapped_column(Integer, primary_key=True)
    recipient_telegram_id: Mapped[int]=mapped_column(BigInteger, index=True)
    kind: Mapped[str]=mapped_column(String(100))
    dedupe_key: Mapped[str]=mapped_column(String(255))
    text: Mapped[str]=mapped_column(Text)
    status: Mapped[NotificationStatus]=mapped_column(default=NotificationStatus.pending)
    attempts: Mapped[int]=mapped_column(Integer, default=0)
    last_error: Mapped[str|None]=mapped_column(Text)
    sent_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class SystemSetting(Base):
    __tablename__='system_settings'
    id: Mapped[int]=mapped_column(Integer, primary_key=True)
    key: Mapped[str]=mapped_column(String(100), unique=True, index=True)
    value: Mapped[str]=mapped_column(Text)
    description: Mapped[str|None]=mapped_column(Text)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class AdminUser(Base):
    __tablename__='admin_users'
    id: Mapped[int]=mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int]=mapped_column(BigInteger, unique=True, index=True)
    role: Mapped[str]=mapped_column(String(30), default='viewer')
    is_active: Mapped[bool]=mapped_column(Boolean, default=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class AuditLog(Base):
    __tablename__='audit_logs'
    id: Mapped[int]=mapped_column(Integer, primary_key=True)
    actor: Mapped[int]=mapped_column(BigInteger, index=True)
    action: Mapped[str]=mapped_column(String(100))
    entity_type: Mapped[str|None]=mapped_column(String(100))
    entity_id: Mapped[int|None]=mapped_column(Integer)
    old_data: Mapped[str|None]=mapped_column(Text)
    new_data: Mapped[str|None]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow)

class UserSession(Base):
    __tablename__='user_sessions'
    user_key: Mapped[int]=mapped_column(BigInteger, primary_key=True)
    state: Mapped[str|None]=mapped_column(String(100))
    data: Mapped[str]=mapped_column(Text, default='{}')
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
