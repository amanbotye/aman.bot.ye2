"""Initial AMAN schema; existing tables are preserved."""
from alembic import op
import sqlalchemy as sa
revision='0001_initial_aman';down_revision=None;branch_labels=None;depends_on=None

def upgrade():
    # For a new database this creates the full schema. Existing installations should run
    # a reviewed diff migration after comparing their live Supabase schema; this migration
    # intentionally never drops or truncates anything.
    from app.models import Base
    bind=op.get_bind();insp=sa.inspect(bind)
    existing=set(insp.get_table_names())
    for table in Base.metadata.sorted_tables:
        if table.name not in existing: table.create(bind,checkfirst=True)

def downgrade():
    # Deliberately non-destructive: AMAN never drops production data automatically.
    pass
