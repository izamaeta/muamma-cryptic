from flask_login import UserMixin
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from muamma.extensions import db


def utcnow() -> datetime:
    return datetime.now(UTC)


class Puzzle(db.Model):
    __tablename__ = "puzzles"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="draft")
    clue: Mapped[str] = mapped_column(Text)
    definition: Mapped[str | None] = mapped_column(String(200))
    answer: Mapped[str] = mapped_column(String(64))
    enumeration: Mapped[str] = mapped_column(String(32))
    hints: Mapped[list[str]] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text)
    technique: Mapped[str] = mapped_column(String(32))
    difficulty: Mapped[int] = mapped_column(Integer, default=2)
    publish_date: Mapped[date | None] = mapped_column(Date, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    __table_args__ = (
        CheckConstraint("kind IN ('daily', 'practice')", name="kind_valid"),
        CheckConstraint("status IN ('draft', 'ready')", name="status_valid"),
        CheckConstraint("difficulty BETWEEN 1 AND 3", name="difficulty_range"),
        CheckConstraint(
            "(kind = 'practice' AND publish_date IS NULL) OR "
            "(kind = 'daily' AND (status = 'draft' OR publish_date IS NOT NULL))",
            name="publish_date_matches_kind",
        ),
    )


class Player(db.Model):
    __tablename__ = "players"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    current_streak: Mapped[int] = mapped_column(default=0)
    max_streak: Mapped[int] = mapped_column(default=0)
    last_streak_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    plays: Mapped[list["Play"]] = relationship(back_populates="player")

    def displayed_streak(self, today: date) -> int:
        """Stored streak, or 0 if the last streak day is before yesterday."""
        if self.last_streak_date is None:
            return 0
        if (today - self.last_streak_date).days > 1:
            return 0
        return self.current_streak


class Play(db.Model):
    __tablename__ = "plays"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), index=True
    )
    puzzle_id: Mapped[int] = mapped_column(ForeignKey("puzzles.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="in_progress")
    guess_count: Mapped[int] = mapped_column(default=0)
    hints_used: Mapped[int] = mapped_column(default=0)
    letters_revealed: Mapped[int] = mapped_column(default=0)
    counts_for_streak: Mapped[bool] = mapped_column(default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    player: Mapped[Player] = relationship(back_populates="plays")
    puzzle: Mapped[Puzzle] = relationship()

    __table_args__ = (
        UniqueConstraint("player_id", "puzzle_id"),
        CheckConstraint(
            "status IN ('in_progress', 'solved', 'revealed')", name="status_valid"
        ),
    )


class Event(db.Model):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE")
    )
    puzzle_id: Mapped[int | None] = mapped_column(ForeignKey("puzzles.id"))
    type: Mapped[str] = mapped_column(String(32))
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )

    __table_args__ = (Index("ix_events_puzzle_id_type", "puzzle_id", "type"),)

class Admin(UserMixin, db.Model):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))