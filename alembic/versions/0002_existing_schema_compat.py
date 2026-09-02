"""Safely extend the existing AMAN schema without deleting data."""
from alembic import op
import sqlalchemy as sa
revision='0002_existing_schema_compat'; down_revision='0001_initial_aman'; branch_labels=None; depends_on=None

def has_table(inspector, name): return name in inspector.get_table_names()
def has_col(inspector, table, col): return any(c['name']==col for c in inspector.get_columns(table))
def upgrade():
    bind=op.get_bind(); insp=sa.inspect(bind)
    additions={
      'telecom_companies':[('sort_order',sa.Integer(),{'nullable':False,'server_default':'0'})],
      'subscriptions':[('duration_days',sa.Integer(),{'nullable':False,'server_default':'365'})],
      'payment_methods':[('proof_required',sa.Boolean(),{'nullable':False,'server_default':'false'})],
      'payment_requests':[('proof_file_type',sa.String(30),{'nullable':True})],
      'followups':[('subscription_id',sa.Integer(),{'nullable':True})],
    }
    for table, cols in additions.items():
        if not has_table(insp,table): continue
        for name,typ,kwargs in cols:
            if not has_col(insp,table,name): op.add_column(table,sa.Column(name,typ,**kwargs))
    for table in ['support_tickets','support_messages','faqs','notifications','admin_users','user_sessions']:
        if not has_table(insp,table):
            from app.models import Base
            Base.metadata.tables[table].create(bind=bind,checkfirst=True)
    insp=sa.inspect(bind)
    if has_table(insp,'phone_numbers'):
        dup=bind.execute(sa.text('SELECT phone_number FROM phone_numbers WHERE phone_number IS NOT NULL GROUP BY phone_number HAVING COUNT(*) > 1 LIMIT 1')).first()
        if not dup:
            existing={c['name'] for c in insp.get_unique_constraints('phone_numbers')}
            if 'uq_phone_number_global' not in existing:
                try: op.create_unique_constraint('uq_phone_number_global','phone_numbers',['phone_number'])
                except Exception: pass

def downgrade(): pass
