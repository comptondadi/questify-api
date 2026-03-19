# in app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

#SQLALCHEMY_DATABASE_URL = "sqlite:///./questify.db"

SQLALCHEMY_DATABASE_URL = settings.database_url
print(f"--- CONNECTING TO DATABASE: {SQLALCHEMY_DATABASE_URL} ---")
engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- THIS IS THE NEW LOCATION ---
# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()