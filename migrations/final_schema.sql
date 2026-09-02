BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001_initial

CREATE TYPE adminrole AS ENUM ('super_admin', 'finance', 'support', 'operations', 'viewer');

CREATE TYPE customerstatus AS ENUM ('ACTIVE', 'BLOCKED', 'SUSPENDED');

CREATE TYPE phonestatus AS ENUM ('UNPROTECTED', 'PROTECTED', 'SUSPENDED', 'EXPIRED');

CREATE TYPE ticketstatus AS ENUM ('OPEN', 'PENDING_CUSTOMER', 'CLOSED');

CREATE TYPE paymentstatus AS ENUM ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED');

CREATE TABLE admin_users (
    id SERIAL NOT NULL, 
    telegram_id BIGINT NOT NULL, 
    role adminrole DEFAULT 'viewer' NOT NULL, 
    active BOOLEAN DEFAULT true NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_admin_users_telegram_id ON admin_users (telegram_id);

CREATE INDEX ix_admin_users_active ON admin_users (active);

CREATE TABLE audit_logs (
    id SERIAL NOT NULL, 
    admin_telegram_id BIGINT NOT NULL, 
    action VARCHAR(100) NOT NULL, 
    entity_type VARCHAR(100) NOT NULL, 
    entity_id VARCHAR(100) NOT NULL, 
    old_value TEXT, 
    new_value TEXT, 
    metadata_json TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_audit_logs_admin_telegram_id ON audit_logs (admin_telegram_id);

CREATE INDEX ix_audit_admin_time ON audit_logs (admin_telegram_id, created_at);

CREATE INDEX ix_audit_entity ON audit_logs (entity_type, entity_id);

CREATE TABLE customers (
    id SERIAL NOT NULL, 
    telegram_id BIGINT NOT NULL, 
    username VARCHAR(64), 
    first_name VARCHAR(128), 
    last_name VARCHAR(128), 
    full_name VARCHAR(255), 
    status customerstatus DEFAULT 'ACTIVE' NOT NULL, 
    last_activity_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_customers_telegram_id ON customers (telegram_id);

CREATE INDEX ix_customers_username ON customers (username);

CREATE INDEX ix_customers_status ON customers (status);

CREATE INDEX ix_customers_last_activity_at ON customers (last_activity_at);

CREATE TABLE telecom_companies (
    id SERIAL NOT NULL, 
    name VARCHAR(120) NOT NULL, 
    code VARCHAR(32) NOT NULL, 
    active BOOLEAN DEFAULT true NOT NULL, 
    sort_order INTEGER DEFAULT '0' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (name), 
    UNIQUE (code)
);

CREATE INDEX ix_telecom_active_order ON telecom_companies (active, sort_order);

CREATE TABLE payment_methods (
    id SERIAL NOT NULL, 
    name VARCHAR(120) NOT NULL, 
    account_name VARCHAR(255) NOT NULL, 
    account_number VARCHAR(120) NOT NULL, 
    instructions TEXT NOT NULL, 
    requires_proof BOOLEAN DEFAULT false NOT NULL, 
    active BOOLEAN DEFAULT true NOT NULL, 
    sort_order INTEGER DEFAULT '0' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_payment_method_active_order ON payment_methods (active, sort_order);

CREATE TABLE system_settings (
    id SERIAL NOT NULL, 
    key VARCHAR(100) NOT NULL, 
    value VARCHAR(255) NOT NULL, 
    description TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (key)
);

CREATE TABLE faq_items (
    id SERIAL NOT NULL, 
    question VARCHAR(255) NOT NULL, 
    answer TEXT NOT NULL, 
    active BOOLEAN DEFAULT true NOT NULL, 
    sort_order INTEGER DEFAULT '0' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_faq_active_order ON faq_items (active, sort_order);

CREATE TABLE phone_numbers (
    id SERIAL NOT NULL, 
    customer_id INTEGER NOT NULL, 
    telecom_company_id INTEGER NOT NULL, 
    phone_number VARCHAR(32) NOT NULL, 
    normalized_phone VARCHAR(16) NOT NULL, 
    status phonestatus DEFAULT 'UNPROTECTED' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_phone_normalized UNIQUE (normalized_phone), 
    CONSTRAINT ck_yemen_phone CHECK (normalized_phone LIKE '+9677%'), 
    FOREIGN KEY(customer_id) REFERENCES customers (id) ON DELETE RESTRICT, 
    FOREIGN KEY(telecom_company_id) REFERENCES telecom_companies (id) ON DELETE RESTRICT
);

CREATE INDEX ix_phone_numbers_customer_id ON phone_numbers (customer_id);

CREATE INDEX ix_phone_numbers_telecom_company_id ON phone_numbers (telecom_company_id);

CREATE INDEX ix_phone_numbers_normalized_phone ON phone_numbers (normalized_phone);

CREATE INDEX ix_phone_numbers_status ON phone_numbers (status);

CREATE INDEX ix_phone_customer_status ON phone_numbers (customer_id, status);

CREATE INDEX ix_phone_company_status ON phone_numbers (telecom_company_id, status);

CREATE TABLE payment_requests (
    id SERIAL NOT NULL, 
    customer_id INTEGER NOT NULL, 
    phone_number_id INTEGER NOT NULL, 
    payment_method_id INTEGER NOT NULL, 
    amount NUMERIC(18, 2) NOT NULL, 
    currency VARCHAR(8) NOT NULL, 
    transaction_reference VARCHAR(255) NOT NULL, 
    proof_file_id VARCHAR(255), 
    status paymentstatus DEFAULT 'PENDING' NOT NULL, 
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    reviewed_at TIMESTAMP WITH TIME ZONE, 
    reviewed_by INTEGER, 
    rejection_reason TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_payment_phone_reference UNIQUE (phone_number_id, transaction_reference), 
    FOREIGN KEY(customer_id) REFERENCES customers (id) ON DELETE RESTRICT, 
    FOREIGN KEY(phone_number_id) REFERENCES phone_numbers (id) ON DELETE RESTRICT, 
    FOREIGN KEY(payment_method_id) REFERENCES payment_methods (id) ON DELETE RESTRICT, 
    FOREIGN KEY(reviewed_by) REFERENCES admin_users (id) ON DELETE SET NULL
);

CREATE INDEX ix_payment_requests_customer_id ON payment_requests (customer_id);

CREATE INDEX ix_payment_requests_phone_number_id ON payment_requests (phone_number_id);

CREATE INDEX ix_payment_requests_status ON payment_requests (status);

CREATE INDEX ix_payment_status_created ON payment_requests (status, created_at);

CREATE INDEX ix_payment_customer_status ON payment_requests (customer_id, status);

CREATE TABLE subscriptions (
    id SERIAL NOT NULL, 
    customer_id INTEGER NOT NULL, 
    phone_number_id INTEGER NOT NULL, 
    payment_request_id INTEGER NOT NULL, 
    start_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    end_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    price NUMERIC(18, 2) NOT NULL, 
    currency VARCHAR(8) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (payment_request_id), 
    CONSTRAINT ck_subscription_dates CHECK (end_at > start_at), 
    FOREIGN KEY(customer_id) REFERENCES customers (id) ON DELETE RESTRICT, 
    FOREIGN KEY(phone_number_id) REFERENCES phone_numbers (id) ON DELETE RESTRICT, 
    FOREIGN KEY(payment_request_id) REFERENCES payment_requests (id) ON DELETE RESTRICT
);

CREATE INDEX ix_subscriptions_customer_id ON subscriptions (customer_id);

CREATE INDEX ix_subscriptions_phone_number_id ON subscriptions (phone_number_id);

CREATE INDEX ix_sub_end_at ON subscriptions (end_at);

CREATE INDEX ix_sub_phone_dates ON subscriptions (phone_number_id, start_at, end_at);

CREATE TABLE followups (
    id SERIAL NOT NULL, 
    phone_number_id INTEGER NOT NULL, 
    customer_id INTEGER NOT NULL, 
    cycle_start TIMESTAMP WITH TIME ZONE NOT NULL, 
    cycle_end TIMESTAMP WITH TIME ZONE NOT NULL, 
    last_followup_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_followup_phone UNIQUE (phone_number_id), 
    FOREIGN KEY(phone_number_id) REFERENCES phone_numbers (id) ON DELETE RESTRICT, 
    FOREIGN KEY(customer_id) REFERENCES customers (id) ON DELETE RESTRICT
);

CREATE INDEX ix_followup_cycle_end ON followups (cycle_end);

CREATE TABLE support_tickets (
    id SERIAL NOT NULL, 
    customer_id INTEGER NOT NULL, 
    subject VARCHAR(255) NOT NULL, 
    status ticketstatus DEFAULT 'OPEN' NOT NULL, 
    assigned_admin_id INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(customer_id) REFERENCES customers (id) ON DELETE RESTRICT, 
    FOREIGN KEY(assigned_admin_id) REFERENCES admin_users (id) ON DELETE SET NULL
);

CREATE INDEX ix_support_tickets_customer_id ON support_tickets (customer_id);

CREATE INDEX ix_support_tickets_status ON support_tickets (status);

CREATE INDEX ix_support_customer_status ON support_tickets (customer_id, status);

CREATE TABLE support_messages (
    id SERIAL NOT NULL, 
    ticket_id INTEGER NOT NULL, 
    sender_telegram_id BIGINT NOT NULL, 
    message_text TEXT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(ticket_id) REFERENCES support_tickets (id) ON DELETE CASCADE
);

CREATE INDEX ix_support_messages_ticket_id ON support_messages (ticket_id);

CREATE INDEX ix_support_messages_sender_telegram_id ON support_messages (sender_telegram_id);

CREATE TABLE notifications (
    id SERIAL NOT NULL, 
    customer_id INTEGER NOT NULL, 
    kind VARCHAR(64) NOT NULL, 
    body TEXT NOT NULL, 
    dedupe_key VARCHAR(255) NOT NULL, 
    attempts INTEGER DEFAULT '0' NOT NULL, 
    sent_at TIMESTAMP WITH TIME ZONE, 
    last_error TEXT, 
    next_attempt_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_notification_dedupe UNIQUE (dedupe_key), 
    FOREIGN KEY(customer_id) REFERENCES customers (id) ON DELETE RESTRICT
);

CREATE INDEX ix_notifications_customer_id ON notifications (customer_id);

CREATE INDEX ix_notification_customer_status ON notifications (customer_id, sent_at);

CREATE INDEX ix_notification_pending ON notifications (sent_at, attempts);

CREATE INDEX ix_notifications_next_attempt_at ON notifications (next_attempt_at);

CREATE TABLE fsm_states (
    id SERIAL NOT NULL, 
    telegram_id BIGINT NOT NULL, 
    chat_id BIGINT NOT NULL, 
    current_state VARCHAR(100) NOT NULL, 
    state_data TEXT DEFAULT '{}' NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_fsm_telegram UNIQUE (telegram_id)
);

CREATE INDEX ix_fsm_states_telegram_id ON fsm_states (telegram_id);

CREATE INDEX ix_fsm_states_chat_id ON fsm_states (chat_id);

INSERT INTO alembic_version (version_num) VALUES ('0001_initial') RETURNING alembic_version.version_num;

-- Running upgrade 0001_initial -> 0002_notification_leases

ALTER TABLE notifications ADD COLUMN processing_token VARCHAR(64);

ALTER TABLE notifications ADD COLUMN processing_started_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE notifications ADD COLUMN processing_until TIMESTAMP WITH TIME ZONE;

ALTER TABLE notifications ADD CONSTRAINT uq_notifications_processing_token UNIQUE (processing_token);

CREATE INDEX ix_notification_processing_until ON notifications (processing_until);

CREATE INDEX ix_notification_claimable ON notifications (sent_at, next_attempt_at, processing_until, attempts);

CREATE INDEX ix_payment_reviewed_at ON payment_requests (reviewed_at);

UPDATE alembic_version SET version_num='0002_notification_leases' WHERE alembic_version.version_num = '0001_initial';

COMMIT;

