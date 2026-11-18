# *** NEW ***
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# docker-compose provides DATABASE_URL; the default is for running outside Docker
# *** NEW ***
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://studystack:studystack@localhost:5432/studystack",
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    # Gives each request its own database session, then closes it
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()