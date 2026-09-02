import os
os.environ['DATABASE_URL']='postgresql+asyncpg://u:p@localhost/db'
from app.config import Settings

def test_url_normalization():
    assert Settings(DATABASE_URL='postgres://u:p@h/db').database_url.startswith('postgresql+asyncpg://')
