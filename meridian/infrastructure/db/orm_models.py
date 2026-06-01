from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class FeedRow(Base):
    __tablename__ = "feeds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    platform_id: Mapped[str | None] = mapped_column(String, nullable=True)
    rss_fallback_url: Mapped[str | None] = mapped_column(String, nullable=True)
    filter_expr: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String, nullable=True)
    language: Mapped[str | None] = mapped_column(String, nullable=True)

    poll_states: Mapped[list["PollStateRow"]] = relationship(
        "PollStateRow", back_populates="feed", cascade="all, delete-orphan"
    )
    items: Mapped[list["ItemRow"]] = relationship(
        "ItemRow", back_populates="feed", cascade="all, delete-orphan"
    )


class PollStateRow(Base):
    __tablename__ = "poll_states"

    feed_id: Mapped[int] = mapped_column(
        ForeignKey("feeds.id"), primary_key=True, nullable=False
    )
    last_polled: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_poll: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    etag: Mapped[str | None] = mapped_column(String, nullable=True)
    last_modified: Mapped[str | None] = mapped_column(String, nullable=True)
    backoff_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    moved_to: Mapped[str | None] = mapped_column(String, nullable=True)
    deprecated: Mapped[bool] = mapped_column(Boolean, default=False)
    deprecated_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    feed: Mapped["FeedRow"] = relationship("FeedRow", back_populates="poll_states")


class ItemRow(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    feed_id: Mapped[int] = mapped_column(ForeignKey("feeds.id"), nullable=False)
    item_id: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    published: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String, nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(String, nullable=True)
    preview_url: Mapped[str | None] = mapped_column(String, nullable=True)
    license_id: Mapped[str | None] = mapped_column(String, nullable=True)
    live_status: Mapped[str | None] = mapped_column(String, nullable=True)
    scheduled_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    authors: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    media: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    thumbnail: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    chapters: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    captions: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    transcript: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    series: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    content_rating: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    geo_restriction: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    paywall: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    source: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    feed: Mapped["FeedRow"] = relationship("FeedRow", back_populates="items")

    __table_args__ = (
        UniqueConstraint("feed_id", "item_id", name="uq_feed_item_id"),
    )
