import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

def _get_database_url():
    """Получить URL базы данных с fallback на SQLite для Windows single-exe"""
    if os.getenv("LOCAL_SINGLEEXE"):
        # SQLite для Windows single-exe режима
        app_data = os.path.expandvars("%LOCALAPPDATA%")
        db_dir = os.path.join(app_data, "Autoparser")
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, "autoparser.db")
        return f"sqlite:///{db_path}"
    else:
        # PostgreSQL для обычного режима
        return os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/postgres")

DATABASE_URL = _get_database_url()
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db():
    Base.metadata.create_all(bind=engine)
