# app/models.py
import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean, DateTime, Numeric, ForeignKey, Enum as SQLEnum, Index
)
from sqlalchemy.orm import relationship
from app.database import Base

class UserStatus(str, enum.Enum):
    active = "active"
    blocked = "blocked"

class PhoneStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"
    cancelled = "cancelled"

class SubscriptionStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    expired = "expired"
    suspended = "suspended"
    cancelled = "cancelled"

class PaymentStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"

class FollowupStatus(str, enum.Enum):
    upcoming = "upcoming"
    due = "due"
    overdue = "overdue"
    completed = "completed"
    cancelled = "cancelled"

class SupportStatus(str, enum.Enum):
    new = "new"
    open = "open"
    closed = "closed"

class NotificationStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"
    cancelled = "cancelled"


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    telegram_username = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    status = Column(SQLEnum(UserStatus), default=UserStatus.active, nullable=False)
    language_code = Column(String(10), default="ar", nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    phone_numbers = relationship("PhoneNumber", back_populates="customer", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="customer", cascade="all, delete-orphan")
    payment_requests = relationship("PaymentRequest", back_populates="customer", cascade="all, delete-orphan")


class TelecomCompany(Base):
    __tablename__ = "telecom_companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    phone_numbers = relationship("PhoneNumber", back_populates="telecom_company")


class PhoneNumber(Base):
    __tablename__ = "phone_numbers"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    telecom_company_id = Column(Integer, ForeignKey("telecom_companies.id"), nullable=False)
    phone_number = Column(String(50), nullable=False, index=True)
    status = Column(SQLEnum(PhoneStatus), default=PhoneStatus.inactive, nullable=False)
    last_recharge_at = Column(DateTime, nullable=True)
    validity_expires_at = Column(DateTime, nullable=True)
    protection_due_at = Column(DateTime, nullable=True)
    confiscation_risk_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    customer = relationship("Customer", back_populates="phone_numbers")
    telecom_company = relationship("TelecomCompany", back_populates="phone_numbers")
    subscriptions = relationship("Subscription", back_populates="phone_number", cascade="all, delete-orphan")
    followups = relationship("Followup", back_populates="phone_number", cascade="all, delete-orphan")
    payment_requests = relationship("PaymentRequest", back_populates="phone_number")

    __table_args__ = (
        Index('idx_customer_phone', 'customer_id', 'phone_number', unique=True),
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    phone_number_id = Column(Integer, ForeignKey("phone_numbers.id", ondelete="CASCADE"), nullable=False)
    plan_name = Column(String(100), default="حماية أساسية", nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="YER", nullable=False)
    duration_months = Column(Integer, default=12, nullable=False)
    starts_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.inactive, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    customer = relationship("Customer", back_populates="subscriptions")
    phone_number = relationship("PhoneNumber", back_populates="subscriptions")
    payment_requests = relationship("PaymentRequest", back_populates="subscription")


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    account_name = Column(String(255), nullable=True)
    account_number = Column(String(100), nullable=True)
    instructions = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    payment_requests = relationship("PaymentRequest", back_populates="payment_method")


class PaymentRequest(Base):
    __tablename__ = "payment_requests"

    id = Column(Integer, primary_key=True, index=True)
    payment_code = Column(String(50), unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    phone_number_id = Column(Integer, ForeignKey("phone_numbers.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    payment_method_id = Column(Integer, ForeignKey("payment_methods.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="YER", nullable=False)
    transaction_reference = Column(String(255), nullable=False)
    proof_file_url = Column(Text, nullable=True)
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.pending, nullable=False)
    rejection_reason = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    customer = relationship("Customer", back_populates="payment_requests")
    phone_number = relationship("PhoneNumber", back_populates="payment_requests")
    subscription = relationship("Subscription", back_populates="payment_requests")
    payment_method = relationship("PaymentMethod", back_populates="payment_requests")


class Followup(Base):
    __tablename__ = "followups"

    id = Column(Integer, primary_key=True, index=True)
    phone_number_id = Column(Integer, ForeignKey("phone_numbers.id", ondelete="CASCADE"), nullable=False)
    previous_followup_at = Column(DateTime, nullable=True)
    due_at = Column(DateTime, nullable=False, index=True)
    status = Column(SQLEnum(FollowupStatus), default=FollowupStatus.upcoming, nullable=False)
    amount_paid = Column(Numeric(10, 2), nullable=True)
    payment_method = Column(String(100), nullable=True)
    payment_reference = Column(String(255), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    completed_by = Column(BigInteger, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    phone_number = relationship("PhoneNumber", back_populates="followups")


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor = Column(BigInteger, nullable=False, index=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=True)
    entity_id = Column(Integer, nullable=True)
    old_data = Column(Text, nullable=True)
    new_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

