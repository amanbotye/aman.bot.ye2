"""Create the complete AMAN PostgreSQL schema."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

adminrole = postgresql.ENUM("super_admin", "finance", "support", "operations", "viewer", name="adminrole")
customerstatus = postgresql.ENUM("ACTIVE", "BLOCKED", "SUSPENDED", name="customerstatus")
phonestatus = postgresql.ENUM("UNPROTECTED", "PROTECTED", "SUSPENDED", "EXPIRED", name="phonestatus")
ticketstatus = postgresql.ENUM("OPEN", "PENDING_CUSTOMER", "CLOSED", name="ticketstatus")
paymentstatus = postgresql.ENUM("PENDING", "APPROVED", "REJECTED", "CANCELLED", name="paymentstatus")
adminrole_col = postgresql.ENUM("super_admin", "finance", "support", "operations", "viewer", name="adminrole", create_type=False)
customerstatus_col = postgresql.ENUM("ACTIVE", "BLOCKED", "SUSPENDED", name="customerstatus", create_type=False)
phonestatus_col = postgresql.ENUM("UNPROTECTED", "PROTECTED", "SUSPENDED", "EXPIRED", name="phonestatus", create_type=False)
ticketstatus_col = postgresql.ENUM("OPEN", "PENDING_CUSTOMER", "CLOSED", name="ticketstatus", create_type=False)
paymentstatus_col = postgresql.ENUM("PENDING", "APPROVED", "REJECTED", "CANCELLED", name="paymentstatus", create_type=False)


def upgrade():
    bind = op.get_bind()
    for enum in (adminrole, customerstatus, phonestatus, ticketstatus, paymentstatus):
        enum.create(bind, checkfirst=True)

    op.create_table("admin_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("role", adminrole_col, nullable=False, server_default="viewer"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_admin_users_telegram_id", "admin_users", ["telegram_id"], unique=True)
    op.create_index("ix_admin_users_active", "admin_users", ["active"])

    op.create_table("audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("admin_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("old_value", sa.Text()), sa.Column("new_value", sa.Text()), sa.Column("metadata_json", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_admin_telegram_id", "audit_logs", ["admin_telegram_id"])
    op.create_index("ix_audit_admin_time", "audit_logs", ["admin_telegram_id", "created_at"])
    op.create_index("ix_audit_entity", "audit_logs", ["entity_type", "entity_id"])

    op.create_table("customers",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(64)), sa.Column("first_name", sa.String(128)), sa.Column("last_name", sa.String(128)),
        sa.Column("full_name", sa.String(255)), sa.Column("status", customerstatus_col, nullable=False, server_default="ACTIVE"),
        sa.Column("last_activity_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_customers_telegram_id", "customers", ["telegram_id"], unique=True)
    op.create_index("ix_customers_username", "customers", ["username"]); op.create_index("ix_customers_status", "customers", ["status"]); op.create_index("ix_customers_last_activity_at", "customers", ["last_activity_at"])

    op.create_table("telecom_companies",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("code", sa.String(32), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("name"), sa.UniqueConstraint("code"),
    )
    op.create_index("ix_telecom_active_order", "telecom_companies", ["active", "sort_order"])

    op.create_table("payment_methods",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("account_name", sa.String(255), nullable=False),
        sa.Column("account_number", sa.String(120), nullable=False), sa.Column("instructions", sa.Text(), nullable=False), sa.Column("requires_proof", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_payment_method_active_order", "payment_methods", ["active", "sort_order"])

    op.create_table("system_settings",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("key", sa.String(100), nullable=False), sa.Column("value", sa.String(255), nullable=False), sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("key"),
    )

    op.create_table("faq_items",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("question", sa.String(255), nullable=False), sa.Column("answer", sa.Text(), nullable=False), sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_faq_active_order", "faq_items", ["active", "sort_order"])

    op.create_table("phone_numbers",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False), sa.Column("telecom_company_id", sa.Integer(), sa.ForeignKey("telecom_companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("phone_number", sa.String(32), nullable=False), sa.Column("normalized_phone", sa.String(16), nullable=False), sa.Column("status", phonestatus_col, nullable=False, server_default="UNPROTECTED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("normalized_phone", name="uq_phone_normalized"), sa.CheckConstraint("normalized_phone LIKE '+9677%'", name="ck_yemen_phone"),
    )
    op.create_index("ix_phone_numbers_customer_id", "phone_numbers", ["customer_id"]); op.create_index("ix_phone_numbers_telecom_company_id", "phone_numbers", ["telecom_company_id"]); op.create_index("ix_phone_numbers_normalized_phone", "phone_numbers", ["normalized_phone"]); op.create_index("ix_phone_numbers_status", "phone_numbers", ["status"]); op.create_index("ix_phone_customer_status", "phone_numbers", ["customer_id", "status"]); op.create_index("ix_phone_company_status", "phone_numbers", ["telecom_company_id", "status"])

    op.create_table("payment_requests",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False), sa.Column("phone_number_id", sa.Integer(), sa.ForeignKey("phone_numbers.id", ondelete="RESTRICT"), nullable=False), sa.Column("payment_method_id", sa.Integer(), sa.ForeignKey("payment_methods.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount", sa.Numeric(18,2), nullable=False), sa.Column("currency", sa.String(8), nullable=False), sa.Column("transaction_reference", sa.String(255), nullable=False), sa.Column("proof_file_id", sa.String(255)), sa.Column("status", paymentstatus_col, nullable=False, server_default="PENDING"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("reviewed_at", sa.DateTime(timezone=True)), sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("admin_users.id", ondelete="SET NULL")), sa.Column("rejection_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("phone_number_id", "transaction_reference", name="uq_payment_phone_reference"),
    )
    op.create_index("ix_payment_requests_customer_id", "payment_requests", ["customer_id"]); op.create_index("ix_payment_requests_phone_number_id", "payment_requests", ["phone_number_id"]); op.create_index("ix_payment_requests_status", "payment_requests", ["status"]); op.create_index("ix_payment_status_created", "payment_requests", ["status", "created_at"]); op.create_index("ix_payment_customer_status", "payment_requests", ["customer_id", "status"])

    op.create_table("subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False), sa.Column("phone_number_id", sa.Integer(), sa.ForeignKey("phone_numbers.id", ondelete="RESTRICT"), nullable=False), sa.Column("payment_request_id", sa.Integer(), sa.ForeignKey("payment_requests.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False), sa.Column("end_at", sa.DateTime(timezone=True), nullable=False), sa.Column("price", sa.Numeric(18,2), nullable=False), sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("payment_request_id"), sa.CheckConstraint("end_at > start_at", name="ck_subscription_dates"),
    )
    op.create_index("ix_subscriptions_customer_id", "subscriptions", ["customer_id"]); op.create_index("ix_subscriptions_phone_number_id", "subscriptions", ["phone_number_id"]); op.create_index("ix_sub_end_at", "subscriptions", ["end_at"]); op.create_index("ix_sub_phone_dates", "subscriptions", ["phone_number_id", "start_at", "end_at"])

    op.create_table("followups",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("phone_number_id", sa.Integer(), sa.ForeignKey("phone_numbers.id", ondelete="RESTRICT"), nullable=False), sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False), sa.Column("cycle_start", sa.DateTime(timezone=True), nullable=False), sa.Column("cycle_end", sa.DateTime(timezone=True), nullable=False), sa.Column("last_followup_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("phone_number_id", name="uq_followup_phone"),
    )
    op.create_index("ix_followup_cycle_end", "followups", ["cycle_end"])

    op.create_table("support_tickets",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False), sa.Column("subject", sa.String(255), nullable=False), sa.Column("status", ticketstatus_col, nullable=False, server_default="OPEN"), sa.Column("assigned_admin_id", sa.Integer(), sa.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_support_tickets_customer_id", "support_tickets", ["customer_id"]); op.create_index("ix_support_tickets_status", "support_tickets", ["status"]); op.create_index("ix_support_customer_status", "support_tickets", ["customer_id", "status"])

    op.create_table("support_messages",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("ticket_id", sa.Integer(), sa.ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False), sa.Column("sender_telegram_id", sa.BigInteger(), nullable=False), sa.Column("message_text", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_support_messages_ticket_id", "support_messages", ["ticket_id"]); op.create_index("ix_support_messages_sender_telegram_id", "support_messages", ["sender_telegram_id"])

    op.create_table("notifications",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False), sa.Column("kind", sa.String(64), nullable=False), sa.Column("body", sa.Text(), nullable=False), sa.Column("dedupe_key", sa.String(255), nullable=False), sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"), sa.Column("sent_at", sa.DateTime(timezone=True)), sa.Column("last_error", sa.Text()), sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("dedupe_key", name="uq_notification_dedupe"),
    )
    op.create_index("ix_notifications_customer_id", "notifications", ["customer_id"]); op.create_index("ix_notification_customer_status", "notifications", ["customer_id", "sent_at"]); op.create_index("ix_notification_pending", "notifications", ["sent_at", "attempts"]); op.create_index("ix_notifications_next_attempt_at", "notifications", ["next_attempt_at"])

    op.create_table("fsm_states",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("telegram_id", sa.BigInteger(), nullable=False), sa.Column("chat_id", sa.BigInteger(), nullable=False), sa.Column("current_state", sa.String(100), nullable=False), sa.Column("state_data", sa.Text(), nullable=False, server_default="{}"), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("telegram_id", name="uq_fsm_telegram"),
    )
    op.create_index("ix_fsm_states_telegram_id", "fsm_states", ["telegram_id"]); op.create_index("ix_fsm_states_chat_id", "fsm_states", ["chat_id"])


def downgrade():
    for name in ("fsm_states", "notifications", "support_messages", "support_tickets", "followups", "subscriptions", "payment_requests", "phone_numbers", "faq_items", "system_settings", "payment_methods", "telecom_companies", "customers", "audit_logs", "admin_users"):
        op.drop_table(name)
    bind = op.get_bind()
    for enum in (paymentstatus, ticketstatus, phonestatus, customerstatus, adminrole):
        enum.drop(bind, checkfirst=True)
