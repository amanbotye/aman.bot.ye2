import os
from pydantic import BaseModel, ConfigDict, Field, field_validator
from dotenv import load_dotenv
load_dotenv()

class Settings(BaseModel):
    model_config=ConfigDict(frozen=True)
    bot_token: str = Field(min_length=1)
    database_url: str = Field(min_length=1)
    admin_ids: frozenset[int]
    timezone: str = "UTC"
    environment: str = "production"
    db_pool_size: int = Field(default=5, ge=1, le=50)
    db_max_overflow: int = Field(default=5, ge=0, le=100)
    log_level: str = "INFO"
    sandbox_database_url: str|None = None

    @field_validator("environment")
    @classmethod
    def validate_environment(cls,v):
        v=v.strip().lower()
        if v not in {"production","sandbox","test"}: raise ValueError("ENVIRONMENT must be production, sandbox, or test")
        return v

    @classmethod
    def from_env(cls):
        token=os.getenv("BOT_TOKEN","").strip(); db=os.getenv("DATABASE_URL","").strip()
        try: ids=frozenset(int(x.strip()) for x in os.getenv("ADMIN_IDS","").split(",") if x.strip())
        except ValueError as exc: raise ValueError("ADMIN_IDS must contain Telegram numeric IDs separated by commas") from exc
        if not token or not db: raise ValueError("BOT_TOKEN and DATABASE_URL are required")
        if db.startswith("postgres://"): db="postgresql+asyncpg://"+db[len("postgres://"):]
        elif db.startswith("postgresql://") and "+asyncpg" not in db: db="postgresql+asyncpg://"+db[len("postgresql://"):]
        sandbox=os.getenv("SANDBOX_DATABASE_URL") or None
        if sandbox:
            if sandbox.startswith("postgres://"):
                sandbox="postgresql+asyncpg://"+sandbox[len("postgres://"):]
            elif sandbox.startswith("postgresql://") and "+asyncpg" not in sandbox:
                sandbox="postgresql+asyncpg://"+sandbox[len("postgresql://"):]
            if sandbox == db:
                raise ValueError("SANDBOX_DATABASE_URL must point to a different PostgreSQL database")
        return cls(bot_token=token,database_url=db,admin_ids=ids,timezone=os.getenv("TIMEZONE","UTC"),environment=os.getenv("ENVIRONMENT","production"),db_pool_size=int(os.getenv("DB_POOL_SIZE","5")),db_max_overflow=int(os.getenv("DB_MAX_OVERFLOW","5")),log_level=os.getenv("LOG_LEVEL","INFO"),sandbox_database_url=sandbox)
