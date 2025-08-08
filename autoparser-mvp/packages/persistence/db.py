import os
import platform
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager

Base = declarative_base()

def _default_sqlite_path() -> Path:
    # %LOCALAPPDATA%\Autoparser\autoparser.db  (Windows)
    if platform.system() == "Windows":
        base = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        p = Path(base) / "Autoparser" / "autoparser.db"
    else:
        # *nix fallback: ~/.local/share/Autoparser/autoparser.db
        p = Path.home() / ".local" / "share" / "Autoparser" / "autoparser.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _default_sqlite_url() -> str:
    return f"sqlite:///{_default_sqlite_path().as_posix()}"

def resolve_database_url() -> str:
    env_url = os.getenv("DATABASE_URL")
    local_exe = os.getenv("LOCAL_SINGLEEXE") == "1"
    is_windows = platform.system() == "Windows"

    # Если явно задан DATABASE_URL — используем его, кроме случая локального single-exe на Windows
    if env_url and not (local_exe and is_windows and env_url.startswith("postgres")):
        return env_url

    # В single-exе на Windows всегда используем локальный SQLite
    if local_exe and is_windows:
        return _default_sqlite_url()

    # Последний безопасный дефолт
    return env_url or _default_sqlite_url()

DB_URL = resolve_database_url()

# Важно для SQLite: check_same_thread=False
connect_args = {}
if DB_URL.startswith("sqlite:"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DB_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

def init_db():
    # Неблокирующий create_all для MVP; позже — alembic
    Base.metadata.create_all(bind=engine)

# Контекстный помощник
@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
