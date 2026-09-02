from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from enum import Enum
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, BigInteger, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class CustomerStatus(str, Enum): ACTIVE="ACTIVE"; BLOCKED="BLOCKED"; SUSPENDED="SUSPENDED"
class PhoneStatus(str, Enum): UNPROTECTED="UNPROTECTED"; PROTECTED="PROTECTED"; SUSPENDED="SUSPENDED"; EXPIRED="EXPIRED"
class PaymentStatus(str, Enum): PENDING="PENDING"; APPROVED="APPROVED"; REJECTED="REJECTED"; CANCELLED="CANCELLED"
class TicketStatus(str, Enum): OPEN="OPEN"; PENDING_CUSTOMER="PENDING_CUSTOMER"; CLOSED="CLOSED"
class AdminRole(str, Enum): SUPER_ADMIN="super_admin"; FINANCE="finance"; SUPPORT="support"; OPERATIONS="operations"; VIEWER="viewer"

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class Customer(TimestampMixin, Base):
    __tablename__="customers"
    id: Mapped[int]=mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int]=mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str|None]=mapped_column(String(64), index=True)
    first_name: Mapped[str|None]=mapped_column(String(128)); last_name: Mapped[str|None]=mapped_column(String(128)); full_name: Mapped[str|None]=mapped_column(String(255))
    status: Mapped[CustomerStatus]=mapped_column(SAEnum(CustomerStatus, values_callable=lambda x:[e.value for e in x], name="customerstatus"), default=CustomerStatus.ACTIVE, server_default="ACTIVE", nullable=False, index=True)
    last_activity_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True), index=True)
    phones: Mapped[list[PhoneNumber]]=relationship(back_populates="customer")

class TelecomCompany(TimestampMixin, Base):
    __tablename__="telecom_companies"
    __table_args__=(Index("ix_telecom_active_order","active","sort_order"),)
    id: Mapped[int]=mapped_column(Integer, primary_key=True); name: Mapped[str]=mapped_column(String(120), unique=True); code: Mapped[str]=mapped_column(String(32), unique=True); active: Mapped[bool]=mapped_column(Boolean, default=True, server_default="true", nullable=False); sort_order: Mapped[int]=mapped_column(Integer, default=0, server_default="0", nullable=False)

class PhoneNumber(TimestampMixin, Base):
    __tablename__="phone_numbers"
    __table_args__=(UniqueConstraint("normalized_phone", name="uq_phone_normalized"), Index("ix_phone_customer_status","customer_id","status"), Index("ix_phone_company_status","telecom_company_id","status"), CheckConstraint("normalized_phone LIKE '+9677%'", name="ck_yemen_phone"))
    id: Mapped[int]=mapped_column(Integer, primary_key=True); customer_id: Mapped[int]=mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), index=True, nullable=False); telecom_company_id: Mapped[int]=mapped_column(ForeignKey("telecom_companies.id", ondelete="RESTRICT"), index=True, nullable=False); phone_number: Mapped[str]=mapped_column(String(32), nullable=False); normalized_phone: Mapped[str]=mapped_column(String(16), index=True, nullable=False); status: Mapped[PhoneStatus]=mapped_column(SAEnum(PhoneStatus, values_callable=lambda x:[e.value for e in x], name="phonestatus"), default=PhoneStatus.UNPROTECTED, server_default="UNPROTECTED", index=True, nullable=False)
    customer: Mapped[Customer]=relationship(back_populates="phones"); telecom_company: Mapped[TelecomCompany]=relationship()

class PaymentMethod(TimestampMixin, Base):
    __tablename__="payment_methods"
    __table_args__=(Index("ix_payment_method_active_order","active","sort_order"),)
    id: Mapped[int]=mapped_column(Integer, primary_key=True); name: Mapped[str]=mapped_column(String(120), nullable=False); account_name: Mapped[str]=mapped_column(String(255), nullable=False); account_number: Mapped[str]=mapped_column(String(120), nullable=False); instructions: Mapped[str]=mapped_column(Text, nullable=False); requires_proof: Mapped[bool]=mapped_column(Boolean, default=False, server_default="false", nullable=False); active: Mapped[bool]=mapped_column(Boolean, default=True, server_default="true", nullable=False); sort_order: Mapped[int]=mapped_column(Integer, default=0, server_default="0", nullable=False)

class PaymentRequest(TimestampMixin, Base):
    __tablename__="payment_requests"
    __table_args__=(Index("ix_payment_status_created","status","created_at"), Index("ix_payment_customer_status","customer_id","status"), Index("ix_payment_reviewed_at","reviewed_at"), UniqueConstraint("phone_number_id","transaction_reference",name="uq_payment_phone_reference"))
    id: Mapped[int]=mapped_column(Integer, primary_key=True); customer_id: Mapped[int]=mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), index=True, nullable=False); phone_number_id: Mapped[int]=mapped_column(ForeignKey("phone_numbers.id", ondelete="RESTRICT"), index=True, nullable=False); payment_method_id: Mapped[int]=mapped_column(ForeignKey("payment_methods.id", ondelete="RESTRICT"), nullable=False); amount: Mapped[Decimal]=mapped_column(Numeric(18,2), nullable=False); currency: Mapped[str]=mapped_column(String(8), nullable=False); transaction_reference: Mapped[str]=mapped_column(String(255), nullable=False); proof_file_id: Mapped[str|None]=mapped_column(String(255)); status: Mapped[PaymentStatus]=mapped_column(SAEnum(PaymentStatus, values_callable=lambda x:[e.value for e in x], name="paymentstatus"), default=PaymentStatus.PENDING, server_default="PENDING", index=True, nullable=False); submitted_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False); reviewed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); reviewed_by: Mapped[int|None]=mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL")); rejection_reason: Mapped[str|None]=mapped_column(Text)

class Subscription(TimestampMixin, Base):
    __tablename__="subscriptions"
    __table_args__=(Index("ix_sub_phone_dates","phone_number_id","start_at","end_at"), Index("ix_sub_end_at","end_at"), CheckConstraint("end_at > start_at", name="ck_subscription_dates"))
    id: Mapped[int]=mapped_column(Integer, primary_key=True); customer_id: Mapped[int]=mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), index=True, nullable=False); phone_number_id: Mapped[int]=mapped_column(ForeignKey("phone_numbers.id", ondelete="RESTRICT"), index=True, nullable=False); payment_request_id: Mapped[int]=mapped_column(ForeignKey("payment_requests.id", ondelete="RESTRICT"), unique=True, nullable=False); start_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), nullable=False); end_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), nullable=False); price: Mapped[Decimal]=mapped_column(Numeric(18,2), nullable=False); currency: Mapped[str]=mapped_column(String(8), nullable=False)

class Followup(TimestampMixin, Base):
    __tablename__="followups"
    __table_args__=(UniqueConstraint("phone_number_id", name="uq_followup_phone"), Index("ix_followup_cycle_end","cycle_end"))
    id: Mapped[int]=mapped_column(Integer, primary_key=True); phone_number_id: Mapped[int]=mapped_column(ForeignKey("phone_numbers.id", ondelete="RESTRICT"), nullable=False); customer_id: Mapped[int]=mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False); cycle_start: Mapped[datetime]=mapped_column(DateTime(timezone=True), nullable=False); cycle_end: Mapped[datetime]=mapped_column(DateTime(timezone=True), nullable=False); last_followup_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))

class SupportTicket(TimestampMixin, Base):
    __tablename__="support_tickets"
    __table_args__=(Index("ix_support_customer_status","customer_id","status"),)
    id: Mapped[int]=mapped_column(Integer, primary_key=True); customer_id: Mapped[int]=mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), index=True, nullable=False); subject: Mapped[str]=mapped_column(String(255), nullable=False); status: Mapped[TicketStatus]=mapped_column(SAEnum(TicketStatus, values_callable=lambda x:[e.value for e in x], name="ticketstatus"), default=TicketStatus.OPEN, server_default="OPEN", index=True, nullable=False); assigned_admin_id: Mapped[int|None]=mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"))

class SupportMessage(Base):
    __tablename__="support_messages"
    id: Mapped[int]=mapped_column(Integer, primary_key=True); ticket_id: Mapped[int]=mapped_column(ForeignKey("support_tickets.id", ondelete="CASCADE"), index=True, nullable=False); sender_telegram_id: Mapped[int]=mapped_column(BigInteger, index=True, nullable=False); message_text: Mapped[str]=mapped_column(Text, nullable=False); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Notification(Base):
    __tablename__="notifications"
    __table_args__=(UniqueConstraint("dedupe_key", name="uq_notification_dedupe"), Index("ix_notification_customer_status","customer_id","sent_at"), Index("ix_notification_pending","sent_at","attempts"), Index("ix_notification_claimable","sent_at","next_attempt_at","processing_until","attempts"))
    id: Mapped[int]=mapped_column(Integer, primary_key=True); customer_id: Mapped[int]=mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), index=True, nullable=False); kind: Mapped[str]=mapped_column(String(64), nullable=False); body: Mapped[str]=mapped_column(Text, nullable=False); dedupe_key: Mapped[str]=mapped_column(String(255), nullable=False); attempts: Mapped[int]=mapped_column(Integer, default=0, server_default="0", nullable=False); sent_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); last_error: Mapped[str|None]=mapped_column(Text); next_attempt_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True), index=True); processing_token: Mapped[str|None]=mapped_column(String(64), unique=True); processing_started_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); processing_until: Mapped[datetime|None]=mapped_column(DateTime(timezone=True), index=True)

class SystemSetting(TimestampMixin, Base):
    __tablename__="system_settings"
    id: Mapped[int]=mapped_column(Integer, primary_key=True); key: Mapped[str]=mapped_column(String(100), unique=True, nullable=False); value: Mapped[str]=mapped_column(String(255), nullable=False); description: Mapped[str|None]=mapped_column(Text)

class AdminUser(TimestampMixin, Base):
    __tablename__="admin_users"
    id: Mapped[int]=mapped_column(Integer, primary_key=True); telegram_id: Mapped[int]=mapped_column(BigInteger, unique=True, index=True, nullable=False); role: Mapped[AdminRole]=mapped_column(SAEnum(AdminRole, values_callable=lambda x:[e.value for e in x], name="adminrole"), default=AdminRole.VIEWER, server_default="viewer", nullable=False); active: Mapped[bool]=mapped_column(Boolean, default=True, server_default="true", index=True, nullable=False)

class FAQItem(TimestampMixin, Base):
    __tablename__="faq_items"
    __table_args__=(Index("ix_faq_active_order","active","sort_order"),)
    id: Mapped[int]=mapped_column(Integer, primary_key=True); question: Mapped[str]=mapped_column(String(255), nullable=False); answer: Mapped[str]=mapped_column(Text, nullable=False); active: Mapped[bool]=mapped_column(Boolean, default=True, server_default="true", nullable=False); sort_order: Mapped[int]=mapped_column(Integer, default=0, server_default="0", nullable=False)

class FSMState(Base):
    __tablename__="fsm_states"
    __table_args__=(UniqueConstraint("telegram_id", name="uq_fsm_telegram"),)
    id: Mapped[int]=mapped_column(Integer, primary_key=True); telegram_id: Mapped[int]=mapped_column(BigInteger, index=True, nullable=False); chat_id: Mapped[int]=mapped_column(BigInteger, index=True, nullable=False); current_state: Mapped[str]=mapped_column(String(100), nullable=False); state_data: Mapped[str]=mapped_column(Text, default="{}", server_default="{}", nullable=False); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class AuditLog(Base):
    __tablename__="audit_logs"
    __table_args__=(Index("ix_audit_entity","entity_type","entity_id"), Index("ix_audit_admin_time","admin_telegram_id","created_at"))
    id: Mapped[int]=mapped_column(Integer, primary_key=True); admin_telegram_id: Mapped[int]=mapped_column(BigInteger, index=True, nullable=False); action: Mapped[str]=mapped_column(String(100), nullable=False); entity_type: Mapped[str]=mapped_column(String(100), nullable=False); entity_id: Mapped[str]=mapped_column(String(100), nullable=False); old_value: Mapped[str|None]=mapped_column(Text); new_value: Mapped[str|None]=mapped_column(Text); metadata_json: Mapped[str|None]=mapped_column(Text); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
