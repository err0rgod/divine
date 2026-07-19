"""Async-friendly SQLite metadata persistence using SQLAlchemy 2.x."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import DateTime, Float, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class UsageRecord(Base):
    __tablename__ = "usage_records"

    request_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    client_type: Mapped[str] = mapped_column(String(32), default="unknown")
    requested_model: Mapped[str] = mapped_column(String(255))
    selected_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    selected_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    route: Mapped[str] = mapped_column(String(100), default="explicit")
    fallback_attempts: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32))
    latency_ms: Mapped[float] = mapped_column(Float, default=0)
    time_to_first_token_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(100), nullable=True)


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{path}")

    def initialize(self) -> None:
        Base.metadata.create_all(self.engine)

    def add_usage(self, record: UsageRecord) -> None:
        with Session(self.engine) as session:
            session.add(record)
            session.commit()

    def recent_usage(self, limit: int = 100) -> list[UsageRecord]:
        with Session(self.engine) as session:
            statement = select(UsageRecord).order_by(UsageRecord.timestamp.desc()).limit(limit)
            return list(session.scalars(statement))

    def close(self) -> None:
        self.engine.dispose()
