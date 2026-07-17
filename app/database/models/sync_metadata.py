from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class SyncMetadata(Base):
    __tablename__ = "sync_metadata"

    entity_name: Mapped[str] = mapped_column(primary_key=True)

    last_sync_time: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )