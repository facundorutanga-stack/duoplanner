"""Reglas de puntos, cumplimiento, rachas y ranking.

Los puntos de un día se recalculan desde cero cada vez que cambia algo de ese
día (tildar un hábito, cargar o borrar estudio o un entrenamiento). Así los
topes se respetan siempre y borrar un registro descuenta sus puntos solo.
"""
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .models import DailyLog, Habit, HabitCheck, PointEvent, StudySession, User, Workout

# --- Reglas (cambialas acá) -------------------------------------------------
PTS_HABIT = 10                # por hábito cumplido
PTS_PERFECT_DAY = 20          # bonus por tildar todos los hábitos del día
PTS_STUDY_PER_MIN = 0.5       # 30 puntos por hora
STUDY_CAP_MIN = 240           # se cuentan hasta 4 h de estudio por día
PTS_WORKOUT = 50              # 1 entrenamiento con puntos por día
PTS_CHECKIN = 10              # por completar el check-in del tablero
PTS_WEEKLY_GOAL = 100         # por cada meta semanal cumplida
HABIT_WEEK_GOAL_PCT = 0.8     # meta semanal de hábitos: 80 % de cumplimiento
ACTIVE_DAY_HABIT_PCT = 0.7    # un día cuenta para la racha con 70 % de hábitos
EDIT_WINDOW_DAYS = 2          # se puede cargar hasta 2 días hacia atrás

DAILY_SOURCES = ("habits", "perfect_day", "study", "workout", "checkin")
WEEKDAYS = ["L", "M", "M", "J", "V", "S", "D"]


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def can_edit(day: date, today: date) -> bool:
    return today - timedelta(days=EDIT_WINDOW_DAYS) <= day <= today


def active_habits(db: Session, user_id: int) -> list[Habit]:
    return list(db.scalars(
        select(Habit).where(Habit.user_id == user_id, Habit.active.is_(True)).order_by(Habit.id)
    ))


def _sum(db: Session, column, *where) -> int:
    return int(db.scalar(select(func.coalesce(func.sum(column), 0)).where(*where)) or 0)


def _count(db: Session, model, *where) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(*where)) or 0)


def recompute_day(db: Session, user: User, day: date) -> None:
    db.execute(delete(PointEvent).where(
        PointEvent.user_id == user.id, PointEvent.day == day, PointEvent.source.in_(DAILY_SOURCES)
    ))
    n_habits = len(active_habits(db, user.id))
    checks = _count(db, HabitCheck, HabitCheck.user_id == user.id, HabitCheck.day == day)
    if checks:
        db.add(PointEvent(user_id=user.id, day=day, source="habits", points=checks * PTS_HABIT,
                          reason=f"{checks} hábitos cumplidos"))
    if n_habits and checks >= n_habits:
        db.add(PointEvent(user_id=user.id, day=day, source="perfect_day", points=PTS_PERFECT_DAY,
                          reason="Día perfecto"))
    minutes = _sum(db, StudySession.minutes, StudySession.user_id == user.id, StudySession.day == day)
    if minutes:
        pts = int(min(minutes, STUDY_CAP_MIN) * PTS_STUDY_PER_MIN)
        db.add(PointEvent(user_id=user.id, day=day, source="study", points=pts,
                          reason=f"{minutes} min de estudio"))
    if _count(db, Workout, Workout.user_id == user.id, Workout.day == day):
        db.add(PointEvent(user_id=user.id, day=day, source="workout", points=PTS_WORKOUT,
                          reason="Entrenamiento"))
    if _count(db, DailyLog, DailyLog.user_id == user.id, DailyLog.day == day):
        db.add(PointEvent(user_id=user.id, day=day, source="checkin", points=PTS_CHECKIN,
                          reason="Check-in del tablero"))
    _recompute_week_bonus(db, user, week_start(day))
    db.flush()


def _recompute_week_bonus(db: Session, user: User, monday: date) -> None:
    db.execute(delete(PointEvent).where(
        PointEvent.user_id == user.id, PointEvent.day == monday, PointEvent.source == "bonus"
    ))
    db.flush()
    s = week_stats(db, user, monday, days_elapsed=7)
    if s.study_min >= user.goal_study_min > 0:
        db.add(PointEvent(user_id=user.id, day=monday, source="bonus", points=PTS_WEEKLY_GOAL,
                          reason="Meta semanal de estudio"))
    if s.workouts >= user.goal_workouts > 0:
        db.add(PointEvent(user_id=user.id, day=monday, source="bonus", points=PTS_WEEKLY_GOAL,
                          reason="Meta semanal de gimnasio"))
    if s.n_habits and s.habit_checks >= HABIT_WEEK_GOAL_PCT * s.n_habits * 7:
        db.add(PointEvent(user_id=user.id, day=monday, source="bonus", points=PTS_WEEKLY_GOAL,
                          reason="Meta semanal de hábitos"))


@dataclass
class WeekStats:
    monday: date
    n_habits: int = 0
    habit_checks: int = 0
    study_min: int = 0
    workouts: int = 0
    points: int = 0
    habits_pct: float = 0.0
    study_pct: float = 0.0
    gym_pct: float = 0.0
    overall_pct: float = 0.0
    active_days: list[bool] = field(default_factory=list)


def week_stats(db: Session, user: User, monday: date, days_elapsed: int = 7) -> WeekStats:
    """Estadísticas de una semana. days_elapsed = cuántos días de la semana ya pasaron
    (incluido hoy), para que el % de hábitos sea justo a mitad de semana."""
    sunday = monday + timedelta(days=6)
    s = WeekStats(monday=monday)
    s.n_habits = len(active_habits(db, user.id))
    s.habit_checks = _count(db, HabitCheck, HabitCheck.user_id == user.id,
                            HabitCheck.day.between(monday, sunday))
    s.study_min = _sum(db, StudySession.minutes, StudySession.user_id == user.id,
                       StudySession.day.between(monday, sunday))
    s.workouts = _count(db, Workout, Workout.user_id == user.id, Workout.day.between(monday, sunday))
    s.points = _sum(db, PointEvent.points, PointEvent.user_id == user.id,
                    PointEvent.day.between(monday, sunday))

    parts = []
    if s.n_habits:
        s.habits_pct = min(1.0, s.habit_checks / (s.n_habits * max(1, days_elapsed)))
        parts.append(s.habits_pct)
    if user.goal_study_min:
        s.study_pct = min(1.0, s.study_min / user.goal_study_min)
        parts.append(s.study_pct)
    if user.goal_workouts:
        s.gym_pct = min(1.0, s.workouts / user.goal_workouts)
        parts.append(s.gym_pct)
    s.overall_pct = sum(parts) / len(parts) if parts else 0.0

    active = _active_days(db, user, monday, sunday, s.n_habits)
    s.active_days = [monday + timedelta(days=i) in active for i in range(7)]
    return s


def _active_days(db: Session, user: User, start: date, end: date, n_habits: int) -> set[date]:
    """Días que cuentan para la racha: 70 % de los hábitos, o algo de estudio o gimnasio."""
    days: set[date] = set()
    rows = db.execute(
        select(HabitCheck.day, func.count()).where(
            HabitCheck.user_id == user.id, HabitCheck.day.between(start, end)
        ).group_by(HabitCheck.day)
    ).all()
    for day, n in rows:
        if n_habits and n >= ACTIVE_DAY_HABIT_PCT * n_habits:
            days.add(day)
    days.update(db.scalars(select(StudySession.day).where(
        StudySession.user_id == user.id, StudySession.day.between(start, end))))
    days.update(db.scalars(select(Workout.day).where(
        Workout.user_id == user.id, Workout.day.between(start, end))))
    return days


def streak(db: Session, user: User, today: date) -> int:
    """Días seguidos activos. Si hoy todavía no hiciste nada, cuenta desde ayer."""
    n_habits = len(active_habits(db, user.id))
    active = _active_days(db, user, today - timedelta(days=400), today, n_habits)
    day = today if today in active else today - timedelta(days=1)
    count = 0
    while day in active:
        count += 1
        day -= timedelta(days=1)
    return count


def best_streak(db: Session, user: User, today: date) -> int:
    n_habits = len(active_habits(db, user.id))
    active = sorted(_active_days(db, user, today - timedelta(days=400), today, n_habits))
    best = run = 0
    prev = None
    for d in active:
        run = run + 1 if prev and d - prev == timedelta(days=1) else 1
        best = max(best, run)
        prev = d
    return best


def group_members(db: Session, user: User) -> list[User]:
    if user.group_id is None:
        return [user]
    return list(db.scalars(select(User).where(User.group_id == user.group_id).order_by(User.id)))


def ranking(db: Session, user: User, today: date) -> list[dict]:
    monday = week_start(today)
    elapsed = (today - monday).days + 1
    rows = []
    for m in group_members(db, user):
        s = week_stats(db, m, monday, elapsed)
        rows.append({"user": m, "stats": s, "streak": streak(db, m, today), "me": m.id == user.id})
    rows.sort(key=lambda r: r["stats"].points, reverse=True)
    return rows
