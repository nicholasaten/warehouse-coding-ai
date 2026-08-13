import uuid

from sqlalchemy import Boolean, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Site(Base):
    """A hospital/site (e.g. RSUS, SHMD, SHBP, MRCCC) -- the top level of the
    Warehouse ID hierarchy. `short_code` is a separate, explicitly-configured
    field (not derived from `code`) since it's used inside every Location ID
    on this site and is a fixed business rule, not something safe to guess
    algorithmically (e.g. RSUS -> US, SHMD -> MD -- looks like "last two
    letters" from the examples seen so far, but that's an observation, not
    a guaranteed rule, so an admin sets it explicitly per site)."""

    __tablename__ = "sites"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    short_code: Mapped[str] = mapped_column(String(5))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
