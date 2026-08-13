from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Every SQLAlchemy model inherits from this. Alembic's env.py imports Base.metadata
    to autogenerate migrations, so any new model file needs to be imported somewhere
    that runs before that happens (see app/models/__init__.py)."""

    pass
