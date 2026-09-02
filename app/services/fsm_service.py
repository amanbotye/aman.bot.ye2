import json
from sqlalchemy import select, text
from ..models import FSMState


class FSMService:
    """PostgreSQL-backed FSM. The database row is the source of truth.

    A transaction-scoped PostgreSQL advisory lock serializes all updates for one
    Telegram user, including the first update when the row does not yet exist.
    """

    def __init__(self, session):
        self.s = session

    async def _lock_user(self, telegram_id: int) -> None:
        # Stable signed BIGINT key. Telegram IDs are positive and fit in BIGINT.
        await self.s.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": int(telegram_id)})

    async def load(self, telegram_id: int, chat_id: int):
        await self._lock_user(telegram_id)
        row = await self.s.scalar(
            select(FSMState).where(FSMState.telegram_id == telegram_id).with_for_update()
        )
        if not row:
            row = FSMState(
                telegram_id=telegram_id,
                chat_id=chat_id,
                current_state="IDLE",
                state_data="{}",
            )
            self.s.add(row)
            await self.s.flush()
        else:
            row.chat_id = chat_id
        try:
            data = json.loads(row.state_data or "{}")
            if not isinstance(data, dict):
                data = {}
        except (TypeError, json.JSONDecodeError):
            data = {}
        return row.current_state, data

    async def save(self, telegram_id: int, chat_id: int, state: str, data: dict) -> None:
        # load() already owns the transaction-scoped advisory lock. Keep the
        # row lock here as an additional guard for callers that save directly.
        row = await self.s.scalar(
            select(FSMState).where(FSMState.telegram_id == telegram_id).with_for_update()
        )
        if not row:
            row = FSMState(
                telegram_id=telegram_id,
                chat_id=chat_id,
                current_state=state,
                state_data=json.dumps(data, ensure_ascii=False, separators=(",", ":")),
            )
            self.s.add(row)
        else:
            row.chat_id = chat_id
            row.current_state = state
            row.state_data = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        await self.s.flush()
