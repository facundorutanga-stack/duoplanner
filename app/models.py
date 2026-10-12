from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    invite_code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    members: Mapped[list["User"]] = relationship(back_populates="group")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(40))
    password_hash: Mapped[str] = mapped_column(String(255))
    avatar: Mapped[str] = mapped_column(String(8), default="🙂")
    tz: Mapped[str] = mapped_column(String(64), default="America/Argentina/Buenos_Aires")
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id"), nullable=True, index=True)
    # Metas semanales, editables en el perfil
    goal_study_min: Mapped[int] = mapped_column(Integer, default=600)
    goal_workouts: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    group: Mapped[Group | None] = relationship(back_populates="members")


class Habit(Base):
    __tablename__ = "habits"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(60))
    icon: Mapped[str] = mapped_column(String(8), default="✅")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class HabitCheck(Base):
    __tablename__ = "habit_checks"
    __table_args__ = (UniqueConstraint("habit_id", "day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    habit_id: Mapped[int] = mapped_column(ForeignKey("habits.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)


class StudySession(Base):
    __tablename__ = "study_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject: Mapped[str] = mapped_column(String(60))
    minutes: Mapped[int] = mapped_column(Integer)
    day: Mapped[date] = mapped_column(Date, index=True)
    note: Mapped[str] = mapped_column(Text, default="")


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(60))
    day: Mapped[date] = mapped_column(Date, index=True)
    detail: Mapped[str] = mapped_column(Text, default="")


class PointEvent(Base):
    """Registro de puntos. El ranking es la suma de esta tabla por semana."""

    __tablename__ = "point_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    source: Mapped[str] = mapped_column(String(30))
    points: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(120), default="")


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("user_id", "code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# --- Tablero personal ---------------------------------------------------------
# Tablas nuevas (no se tocan las existentes, así tu base actual sigue andando).

class DailyLog(Base):
    """Check-in diario: sueño, ánimo, energía, familia, satisfacción."""

    __tablename__ = "daily_logs"
    __table_args__ = (UniqueConstraint("user_id", "day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    sleep_h: Mapped[float | None] = mapped_column(nullable=True)
    exercised: Mapped[bool] = mapped_column(Boolean, default=False)
    mood: Mapped[int | None] = mapped_column(Integer, nullable=True)
    energy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    family_min: Mapped[int] = mapped_column(Integer, default=0)
    satisfaction: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")


class MonthlySaving(Base):
    __tablename__ = "monthly_savings"
    __table_args__ = (UniqueConstraint("user_id", "month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    month: Mapped[date] = mapped_column(Date)  # siempre el día 1 del mes
    amount: Mapped[float] = mapped_column(default=0)


class Completion(Base):
    """Libros o cursos terminados."""

    __tablename__ = "completions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    kind: Mapped[str] = mapped_column(String(10))  # libro | curso
    title: Mapped[str] = mapped_column(String(120))


class WeeklyGoal(Base):
    __tablename__ = "weekly_goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    week_start: Mapped[date] = mapped_column(Date, index=True)
    text: Mapped[str] = mapped_column(String(120))
    done: Mapped[bool] = mapped_column(Boolean, default=False)


# --- Nutrición ------------------------------------------------------------------

class NutritionProfile(Base):
    __tablename__ = "nutrition_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    sex: Mapped[str] = mapped_column(String(1), default="m")  # m | f
    age: Mapped[int] = mapped_column(Integer, default=25)
    weight_kg: Mapped[float] = mapped_column(default=70)
    height_cm: Mapped[float] = mapped_column(default=170)
    activity: Mapped[str] = mapped_column(String(12), default="moderada")
    goal: Mapped[str] = mapped_column(String(12), default="mantener")  # perder | mantener | ganar
    vegetarian: Mapped[bool] = mapped_column(Boolean, default=False)
