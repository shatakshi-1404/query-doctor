from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AnalysisRecord(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    query_id: Mapped[int] = mapped_column(
        ForeignKey("queries.id", ondelete="CASCADE"), index=True
    )
    planning_time: Mapped[float] = mapped_column(Float)
    execution_time: Mapped[float] = mapped_column(Float)
    rows_returned: Mapped[int]
    issues_count: Mapped[int]
    result: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    query: Mapped["QueryRecord"] = relationship(back_populates="analyses")
