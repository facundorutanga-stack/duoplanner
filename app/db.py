import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./duoplanner.db")
    # Neon da URLs "postgresql://" o "postgres://"; SQLAlchemy necesita el driver explícito.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


DATABASE_URL = _database_url()

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # En Vercel cada request puede correr en una función nueva: sin pool propio,
    # usamos el pooler de Neon (la URL que tiene "-pooler").
    engine = create_engine(DATABASE_URL, poolclass=NullPool)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
