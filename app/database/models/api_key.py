from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("api_keys.id"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(12), index=True)
    scope: Mapped[str] = mapped_column(String(20), default="read")
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)