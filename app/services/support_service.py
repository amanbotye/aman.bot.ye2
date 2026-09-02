from sqlalchemy import select,func
from app.models import SupportTicket,SupportMessage,SupportStatus
from app.utils import ticket_code,utcnow
async def create_ticket(db,customer_id,subject):
    t=SupportTicket(ticket_code=ticket_code(),customer_id=customer_id,subject=subject.strip(),status=SupportStatus.new,last_message_at=utcnow());db.add(t);await db.flush();return t
async def add_message(db,ticket_id,sender_id,text,is_admin=False):
    t=(await db.execute(select(SupportTicket).where(SupportTicket.id==ticket_id).with_for_update())).scalar_one_or_none()
    if not t or t.status==SupportStatus.closed:return None,'closed'
    m=SupportMessage(ticket_id=ticket_id,sender_telegram_id=sender_id,sender_is_admin=is_admin,text=text);db.add(m);t.status=SupportStatus.open;t.last_message_at=utcnow();await db.flush();return m,'ok'
async def customer_tickets(db,customer_id):return (await db.execute(select(SupportTicket).where(SupportTicket.customer_id==customer_id).order_by(SupportTicket.updated_at.desc()))).scalars().all()
async def messages(db,ticket_id):return (await db.execute(select(SupportMessage).where(SupportMessage.ticket_id==ticket_id).order_by(SupportMessage.created_at))).scalars().all()
