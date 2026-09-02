"""${message}"""
from alembic import op
import sqlalchemy as sa
${up_revision if up_revision else ""}
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}

def upgrade():
    return None

def downgrade():
    return None
