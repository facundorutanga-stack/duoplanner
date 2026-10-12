"""Logros. Para agregar uno: sumá una entrada a ACHIEVEMENTS con su condición."""
from dataclasses import dataclass
from datetime import date
from typing import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import HabitCheck, PointEvent, StudySession, User, UserAchievement, Workout
from .points import best_streak


@dataclass
class Stats:
    checks: int
    study_min: int
    workouts: int
    best_streak: int
    perfect_days: int


@dataclass
class Achievement:
    code: str
    icon: str
    title: str
    description: str
    check: Callable[[Stats], bool]


ACHIEVEMENTS = [
    Achievement("primer_paso", "🌱", "Primer paso", "Cargaste tu primer registro",
                lambda s: s.checks + s.study_min + s.workouts > 0),
    Achievement("dia_perfecto", "✨", "Día perfecto", "Cumpliste todos tus hábitos en un día",
                lambda s: s.perfect_days >= 1),
    Achievement("racha_7", "🔥", "Racha de 7", "7 días seguidos activo", lambda s: s.best_streak >= 7),
    Achievement("racha_30", "🌋", "Racha de 30", "30 días seguidos activo", lambda s: s.best_streak >= 30),
    Achievement("racha_100", "💎", "Racha de 100", "100 días seguidos activo", lambda s: s.best_streak >= 100),
    Achievement("estudio_20h", "📚", "20 horas de estudio", "Sumaste 20 h de estudio", lambda s: s.study_min >= 20 * 60),
    Achievement("estudio_100h", "🎓", "100 horas de estudio", "Sumaste 100 h de estudio", lambda s: s.study_min >= 100 * 60),
    Achievement("gym_10", "💪", "10 entrenamientos", "Registraste 10 entrenamientos", lambda s: s.workouts >= 10),
    Achievement("gym_30", "🏋️", "30 entrenamientos", "Registraste 30 entrenamientos", lambda s: s.workouts >= 30),
    Achievement("habitos_100", "✅", "100 hábitos", "Tildaste 100 hábitos", lambda s: s.checks >= 100),
]
BY_CODE = {a.code: a for a in ACHIEVEMENTS}


def _stats(db: Session, user: User, today: date) -> Stats:
    def scalar(q):
        return int(db.scalar(q) or 0)

    return Stats(
        checks=scalar(select(func.count()).select_from(HabitCheck).where(HabitCheck.user_id == user.id)),
        study_min=scalar(select(func.coalesce(func.sum(StudySession.minutes), 0)).where(StudySession.user_id == user.id)),
        workouts=scalar(select(func.count()).select_from(Workout).where(Workout.user_id == user.id)),
        best_streak=best_streak(db, user, today),
        perfect_days=scalar(select(func.count()).select_from(PointEvent).where(
            PointEvent.user_id == user.id, PointEvent.source == "perfect_day")),
    )


def evaluate(db: Session, user: User, today: date) -> list[Achievement]:
    """Desbloquea los logros nuevos y los devuelve."""
    have = set(db.scalars(select(UserAchievement.code).where(UserAchievement.user_id == user.id)))
    stats = _stats(db, user, today)
    new = [a for a in ACHIEVEMENTS if a.code not in have and a.check(stats)]
    for a in new:
        db.add(UserAchievement(user_id=user.id, code=a.code))
    return new
