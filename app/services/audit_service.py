from app.models import AuditLog
from app.utils import json_dumps
async def audit(db, actor, action, entity_type=None, entity_id=None, old_data=None, new_data=None):
    db.add(AuditLog(actor=actor,action=action,entity_type=entity_type,entity_id=entity_id,old_data=json_dumps(old_data) if old_data is not None else None,new_data=json_dumps(new_data) if new_data is not None else None))
