from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, Text, JSON, DateTime, Integer, Boolean, ForeignKey
from datetime import datetime

class Base(DeclarativeBase): pass

class Measure(Base):
    __tablename__ = "measures"
    msr_intlid: Mapped[str] = mapped_column(Text, primary_key=True)
    card: Mapped[dict] = mapped_column(JSON)
    region_code: Mapped[str] = mapped_column(Text)
    prglvl: Mapped[str] = mapped_column(Text)
    segmnt: Mapped[str] = mapped_column(Text)
    typeid: Mapped[str] = mapped_column(Text)
    chkdat: Mapped[datetime | None]

class Source(Base):
    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(Text, unique=True)
    domain: Mapped[str | None] = mapped_column(Text)
    is_official: Mapped[bool | None]
    region_code: Mapped[str | None] = mapped_column(Text)
    first_seen_at: Mapped[datetime | None]
    last_checked_at: Mapped[datetime | None]
    status: Mapped[str | None] = mapped_column(Text)

class Snapshot(Base):
    __tablename__ = "snapshots"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sources.id", ondelete="CASCADE"))
    sha256: Mapped[str | None] = mapped_column(Text)
    stored_at: Mapped[datetime | None]
    path_html: Mapped[str | None] = mapped_column(Text)
    path_txt: Mapped[str | None] = mapped_column(Text)
    http_status: Mapped[int | None]
    charset: Mapped[str | None] = mapped_column(Text)

class Run(Base):
    __tablename__ = "runs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    region: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(Text, default="queued")
    found: Mapped[int] = mapped_column(Integer, default=0)
    processed: Mapped[int] = mapped_column(Integer, default=0)
    ok: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[int] = mapped_column(Integer, default=0)

class Step(Base):
    __tablename__ = "steps"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("runs.id", ondelete="CASCADE"))
    source_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("sources.id", ondelete="CASCADE"))
    stage: Mapped[str] = mapped_column(Text)  # SEARCH/FETCH/CLEAN/E1..E7/BUILD_ID/SAVE
    status: Mapped[str] = mapped_column(Text, default="queued")
    payload: Mapped[dict | None] = mapped_column(JSON)
    llm_tokens: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
