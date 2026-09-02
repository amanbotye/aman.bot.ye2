class NotificationService:
    def __init__(self,repo): self.repo=repo
    async def enqueue(self,customer_id,kind,body,dedupe_key):
        return await self.repo.create(customer_id=customer_id,kind=kind,body=body,dedupe_key=dedupe_key)
    async def claim_pending(self,limit=50,max_attempts=3,lease_seconds=300):
        return await self.repo.claim_pending(limit,max_attempts,lease_seconds)
