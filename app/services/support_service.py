from ..models import TicketStatus
class SupportService:
    def __init__(self,repo): self.repo=repo
    async def create(self,customer_id,subject):
        subject=" ".join(str(subject).split())
        if len(subject)<2 or len(subject)>255: raise ValueError("عنوان التذكرة غير صالح.")
        return await self.repo.create_ticket(customer_id=customer_id,subject=subject,status=TicketStatus.OPEN)
    async def message(self,ticket_id,sender,text,is_admin=False):
        t=await self.repo.get(ticket_id)
        if not t: raise ValueError("التذكرة غير موجودة.")
        if t.status==TicketStatus.CLOSED: raise ValueError("التذكرة مغلقة ولا تستقبل رسائل. أعد فتحها أولًا.")
        text=text.strip()
        if not text or len(text)>4000: raise ValueError("الرسالة غير صالحة.")
        row=await self.repo.add_message(ticket_id=ticket_id,sender_telegram_id=sender,message_text=text)
        t.status=TicketStatus.PENDING_CUSTOMER if is_admin else TicketStatus.OPEN
        return row
    async def close(self,ticket_id):
        t=await self.repo.get(ticket_id)
        if not t: raise ValueError("التذكرة غير موجودة.")
        t.status=TicketStatus.CLOSED; return t
    async def reopen(self,ticket_id):
        t=await self.repo.get(ticket_id)
        if not t: raise ValueError("التذكرة غير موجودة.")
        t.status=TicketStatus.OPEN; return t
    async def assign(self,ticket_id,admin_id):
        t=await self.repo.get(ticket_id)
        if not t: raise ValueError("التذكرة غير موجودة.")
        t.assigned_admin_id=admin_id; return t
