"""
CivicOS API — SQLAlchemy ORM models.

These map 1:1 to the tables defined in 001_initial_schema.sql.
We use SQLAlchemy's DeclarativeBase with the async engine.

Key design decisions:
- We use UUIDs as primary keys (not auto-increment integers).
- We use JSONB columns for flexible schemas (eligibility_json, snapshot, diff).
- Timestamps use TIMESTAMP(timezone=True) — always UTC in the DB, converted at the API layer.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Short alias for readability
TSTZ = TIMESTAMP(timezone=True)


class Base(DeclarativeBase):
    pass


# ── Helper: generate UUIDs at the application layer ──────────────────────
def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


class City(Base):
    __tablename__ = "cities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="America/New_York")
    created_at: Mapped[datetime] = mapped_column(TSTZ, server_default=text("NOW()"))

    programs: Mapped[list["Program"]] = relationship(back_populates="city", lazy="selectin")
    sources: Mapped[list["Source"]] = relationship(back_populates="city", lazy="selectin")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(50))

    programs: Mapped[list["Program"]] = relationship(back_populates="category", lazy="selectin")


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    city_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cities.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    eligibility: Mapped[str | None] = mapped_column(Text)
    eligibility_json: Mapped[dict | None] = mapped_column(JSONB)
    benefit_amount: Mapped[str | None] = mapped_column(String(200))
    how_to_apply: Mapped[str | None] = mapped_column(Text)
    application_url: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(Text)
    languages: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=["en"])
    deadline: Mapped[date | None] = mapped_column(Date)
    is_ongoing: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text)
    raw_html: Mapped[str | None] = mapped_column(Text)
    extracted_at: Mapped[datetime] = mapped_column(TSTZ, server_default=text("NOW()"))
    last_checked_at: Mapped[datetime | None] = mapped_column(TSTZ)
    last_modified_at: Mapped[datetime | None] = mapped_column(TSTZ)
    created_at: Mapped[datetime] = mapped_column(TSTZ, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(TSTZ, server_default=text("NOW()"))

    city: Mapped["City"] = relationship(back_populates="programs")
    category: Mapped["Category"] = relationship(back_populates="programs")
    versions: Mapped[list["ProgramVersion"]] = relationship(
        back_populates="program",
        lazy="selectin",
        order_by="ProgramVersion.changed_at.desc()",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive', 'unknown')",
            name="ck_programs_status",
        ),
        CheckConstraint(
            "source_type IN ('web', 'pdf', 'rss')",
            name="ck_programs_source_type",
        ),
        Index("idx_programs_city", "city_id"),
        Index("idx_programs_category", "category_id"),
        Index("idx_programs_status", "status"),
    )


class ProgramVersion(Base):
    __tablename__ = "program_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
    )
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    diff: Mapped[dict | None] = mapped_column(JSONB)
    changed_at: Mapped[datetime] = mapped_column(TSTZ, server_default=text("NOW()"))

    program: Mapped["Program"] = relationship(back_populates="versions")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    city_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cities.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    scrape_frequency: Mapped[str] = mapped_column(String(20), default="weekly")
    last_scraped_at: Mapped[datetime | None] = mapped_column(TSTZ)
    last_status: Mapped[str] = mapped_column(String(20), default="pending")
    last_error: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TSTZ, server_default=text("NOW()"))

    city: Mapped["City"] = relationship(back_populates="sources")

    __table_args__ = (
        CheckConstraint(
            "source_type IN ('web', 'pdf', 'rss')",
            name="ck_sources_source_type",
        ),
        CheckConstraint(
            "scrape_frequency IN ('daily', 'weekly', 'monthly', 'manual')",
            name="ck_sources_scrape_frequency",
        ),
        CheckConstraint(
            "last_status IN ('pending', 'success', 'error')",
            name="ck_sources_last_status",
        ),
    )


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="started")
    programs_found: Mapped[int] = mapped_column(Integer, default=0)
    programs_new: Mapped[int] = mapped_column(Integer, default=0)
    programs_updated: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(TSTZ, server_default=text("NOW()"))
    completed_at: Mapped[datetime | None] = mapped_column(TSTZ)

    __table_args__ = (
        CheckConstraint(
            "status IN ('started', 'scraped', 'extracted', 'stored', 'error')",
            name="ck_ingestion_runs_status",
        ),
    )
