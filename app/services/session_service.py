import json
from sqlalchemy import select
from app.models import UserSession
async def load(db,user_id):
    x=(await db.execute(select(UserSession).where(UserSession.user_key==user_id))).scalar_one_or_none()
    if not x:return None,{}
    try:data=json.loads(x.data or '{}')
    except Exception:data={}
    return x.state,data
async def save(db,user_id,state,data):
    x=(await db.execute(select(UserSession).where(UserSession.user_key==user_id).with_for_update())).scalar_one_or_none()
    payload=json.dumps(data,ensure_ascii=False,default=str)
    if x:x.state=state;x.data=payload
    else:db.add(UserSession(user_key=user_id,state=state,data=payload))
    await db.commit()
async def clear(db,user_id):
    x=(await db.execute(select(UserSession).where(UserSession.user_key==user_id))).scalar_one_or_none()
    if x:x.state=None;x.data='{}';await db.commit()
