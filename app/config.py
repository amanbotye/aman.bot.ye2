from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')
    BOT_TOKEN: str = ''
    DATABASE_URL: str = ''
    ADMIN_IDS: str = ''
    WEB_PORT: int = Field(default=10000, ge=1, le=65535)
    TIMEZONE: str = 'UTC'
    LOG_LEVEL: str = 'INFO'

    @property
    def admin_ids(self) -> set[int]:
        return {int(x.strip()) for x in self.ADMIN_IDS.split(',') if x.strip().isdigit()}

    @property
    def database_url(self) -> str:
        url = self.DATABASE_URL.strip()
        if url.startswith('postgres://'):
            url = 'postgresql+asyncpg://' + url[len('postgres://'):]
        elif url.startswith('postgresql://'):
            url = 'postgresql+asyncpg://' + url[len('postgresql://'):]
        return url

settings = Settings()
