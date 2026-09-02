import json
class AuditService:
 async def log(self,s,admin_id,action,entity_type,entity_id,old=None,new=None,metadata=None):
  from ..models import AuditLog
  row=AuditLog(admin_telegram_id=admin_id,action=action,entity_type=entity_type,entity_id=str(entity_id),old_value=json.dumps(old,ensure_ascii=False,default=str) if old is not None else None,new_value=json.dumps(new,ensure_ascii=False,default=str) if new is not None else None,metadata_json=json.dumps(metadata,ensure_ascii=False,default=str) if metadata else None)
  s.add(row); await s.flush(); return row
