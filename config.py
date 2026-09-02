import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_TELEGRAM_ID: int
    DATABASE_URL: str

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings(
    BOT_TOKEN=os.getenv("BOT_TOKEN", ""),
    ADMIN_TELEGRAM_ID=int(os.getenv("ADMIN_TELEGRAM_ID", "0")),
    DATABASE_URL=os.getenv("DATABASE_URL", "")
)
