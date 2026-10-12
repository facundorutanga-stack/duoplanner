"""Tablero personal: arma las series para los gráficos y busca patrones.

"Lo que se mide, mejora; lo que se revisa periódicamente, mejora aún más."
"""
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import DailyLog, StudySession, User, Workout

MIN_DAYS_FOR_PATTERNS = 14   # con menos datos los promedios engañan
MIN_GROUP = 3                # días mínimos de cada lado de una comparación
MIN_DIFF = 0.5               # diferencia mínima (en puntos de 1 a 10) para mostrarla


@dataclass
class Day:
    day: date
    sleep_h: float | None
    exercised: bool
    mood: int | None
    energy: int | None
    family_min: int
    satisfaction: int | None
    study_min: int
    logged: bool


def days_range(db: Session, user: User, start: date, end: date) -> list[Day]:
    logs = {l.day: l for l in db.scalars(select(DailyLog).where(
        DailyLog.user_id == user.id, DailyLog.day.between(start, end)))}
    study = dict(db.execute(select(StudySession.day, func.sum(StudySession.minutes)).where(
        StudySession.user_id == user.id, StudySession.day.between(start, end)).group_by(StudySession.day)).all())
    workouts = set(db.scalars(select(Workout.day).where(
        Workout.user_id == user.id, Workout.day.between(start, end))))
    out = []
    d = start
    while d <= end:
        l = logs.get(d)
        out.append(Day(
            day=d,
            sleep_h=l.sleep_h if l else None,
            exercised=(d in workouts) or bool(l and l.exercised),
            mood=l.mood if l else None,
            energy=l.energy if l else None,
            family_min=l.family_min if l else 0,
            satisfaction=l.satisfaction if l else None,
            study_min=int(study.get(d, 0) or 0),
            logged=l is not None,
        ))
        d += timedelta(days=1)
    return out


def _avg(values) -> float | None:
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def summary(days: list[Day]) -> dict:
    logged = [d for d in days if d.logged]
    return {
        "logged": len(logged),
        "sleep": _avg(d.sleep_h for d in logged),
        "mood": _avg(d.mood for d in logged),
        "energy": _avg(d.energy for d in logged),
        "satisfaction": _avg(d.satisfaction for d in logged),
        "family_h": _avg(d.family_min / 60 for d in logged),
        "study_h": sum(d.study_min for d in days) / 60,
        "exercise_days": sum(d.exercised for d in days),
        "days": len(days),
    }


def _compare(days, split, metric, yes_label, no_label, what):
    yes = [metric(d) for d in days if split(d) and metric(d) is not None]
    no = [metric(d) for d in days if not split(d) and metric(d) is not None]
    if len(yes) < MIN_GROUP or len(no) < MIN_GROUP:
        return None
    a, b = sum(yes) / len(yes), sum(no) / len(no)
    if abs(a - b) < MIN_DIFF:
        return None
    better = a > b
    return {
        "text": f"{what}: {a:.1f} los días {yes_label} contra {b:.1f} los días {no_label}.",
        "good": better,
        "diff": abs(a - b),
        "n": len(yes) + len(no),
    }


def patterns(days: list[Day]) -> list[dict]:
    """Compara días con y sin cada hábito. Solo usa días con check-in."""
    logged = [d for d in days if d.logged]
    if len(logged) < MIN_DAYS_FOR_PATTERNS:
        return []
    checks = [
        (lambda d: (d.sleep_h or 0) >= 7, lambda d: d.energy, "en que dormís 7 h o más", "con menos sueño", "Tu energía promedio"),
        (lambda d: (d.sleep_h or 0) >= 7, lambda d: d.mood, "en que dormís 7 h o más", "con menos sueño", "Tu ánimo promedio"),
        (lambda d: d.exercised, lambda d: d.mood, "que entrenás", "sin ejercicio", "Tu ánimo promedio"),
        (lambda d: d.exercised, lambda d: d.energy, "que entrenás", "sin ejercicio", "Tu energía promedio"),
        (lambda d: d.family_min >= 60, lambda d: d.mood, "con 1 h o más con tu familia", "con menos", "Tu ánimo promedio"),
        (lambda d: d.family_min >= 60, lambda d: d.satisfaction, "con 1 h o más con tu familia", "con menos", "Tu satisfacción"),
        (lambda d: d.study_min >= 120, lambda d: d.satisfaction, "que estudiás 2 h o más", "con menos estudio", "Tu satisfacción"),
        (lambda d: d.study_min >= 120, lambda d: d.energy, "que estudiás 2 h o más", "con menos estudio", "Tu energía"),
    ]
    found = [p for c in checks if (p := _compare(logged, *c))]
    found.sort(key=lambda p: -p["diff"])
    return found[:5]


def chart_data(days: list[Day]) -> dict:
    return {
        "labels": [f"{d.day.day}/{d.day.month}" for d in days],
        "sleep": [d.sleep_h for d in days],
        "mood": [d.mood for d in days],
        "energy": [d.energy for d in days],
        "satisfaction": [d.satisfaction for d in days],
        "study_h": [round(d.study_min / 60, 2) for d in days],
        "family_h": [round(d.family_min / 60, 2) if d.logged else None for d in days],
        "exercised": [1 if d.exercised else 0 for d in days],
    }
