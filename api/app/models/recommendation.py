import uuid
from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Recommendation(Base):
    """A persisted optimization recommendation (AI Responsibilities #7/#8/#9)
    -- persisted so VIEWING recommendations never costs an LLM call, only
    explicitly triggering `POST /recommendations/generate` does. Each
    "generate" run replaces the previous set (see optimization_service);
    this isn't a history table.

    `warehouse_ids` is a JSON list of warehouse UUID strings rather than a
    join table -- a recommendation can reference 1 (redundant/underutilized/
    overloaded) or 2 (merge opportunity) warehouses, and nothing here needs
    to query "which recommendations mention warehouse X" efficiently enough
    to justify a real join table yet.
    """

    __tablename__ = "recommendations"
    __table_args__ = (
        CheckConstraint(
            "category IN ('merge_opportunity', 'redundant_warehouse', 'underutilized', 'overloaded')",
            name="chk_recommendation_category",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    category: Mapped[str] = mapped_column(String(30))
    warehouse_ids: Mapped[list[str]] = mapped_column(JSON)
    title: Mapped[str] = mapped_column(String(255))
    explanation: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
