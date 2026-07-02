import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

load_dotenv()


def normalize_database_url(database_url: str | None) -> str | None:
    if not database_url:
        return None

    if os.getenv("DOCKER_CONTAINER") == "1":
        return database_url

    if database_url.startswith("postgresql://") and "@postgres" in database_url:
        return database_url.replace("@postgres", "@localhost", 1)

    return database_url


DATABASE_URL = normalize_database_url(os.getenv("DATABASE_URL"))

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    """
    FastAPI dependency — yields a DB session per request, 
    always closes it after, even if the request fails.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()