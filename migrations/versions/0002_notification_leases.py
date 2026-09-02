"""Add atomic notification claiming and crash-recovery leases."""
from alembic import op
import sqlalchemy as sa

revision = "0002_notification_leases"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("notifications", sa.Column("processing_token", sa.String(64), nullable=True))
    op.add_column("notifications", sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("notifications", sa.Column("processing_until", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_notifications_processing_token", "notifications", ["processing_token"])
    op.create_index("ix_notification_processing_until", "notifications", ["processing_until"])
    op.create_index(
        "ix_notification_claimable",
        "notifications",
        ["sent_at", "next_attempt_at", "processing_until", "attempts"],
    )
    op.create_index("ix_payment_reviewed_at", "payment_requests", ["reviewed_at"])


def downgrade():
    op.drop_index("ix_payment_reviewed_at", table_name="payment_requests")
    op.drop_index("ix_notification_claimable", table_name="notifications")
    op.drop_index("ix_notification_processing_until", table_name="notifications")
    op.drop_constraint("uq_notifications_processing_token", "notifications", type_="unique")
    op.drop_column("notifications", "processing_until")
    op.drop_column("notifications", "processing_started_at")
    op.drop_column("notifications", "processing_token")
