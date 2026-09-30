from datetime import datetime

from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class QueryRecord(Base):
    __tablename__ = "queries"

    id: Mapped[int] = mapped_column(primary_key=True)
    query_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    analyses: Mapped[list["AnalysisRecord"]] = relationship(
        back_populates="query", cascade="all, delete-orphan"
    )
