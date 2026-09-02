# Compatibility shim; production database lives in app.database.
from app.database import Base,engine,SessionLocal
