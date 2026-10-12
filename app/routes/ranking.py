from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..points import (
    PTS_CHECKIN, PTS_HABIT, PTS_PERFECT_DAY, PTS_WEEKLY_GOAL, PTS_WORKOUT, STUDY_CAP_MIN, ranking, week_start,
)
from ..security import current_user, today_for
from .common import render

router = APIRouter()


@router.get("/ranking")
def ranking_page(request: Request, by: str = "points", user: User = Depends(current_user),
                 db: Session = Depends(get_db)):
    today = today_for(user)
    rows = ranking(db, user, today)
    if by == "pct":
        rows.sort(key=lambda r: r["stats"].overall_pct, reverse=True)
    rules = [
        ("Entrenamiento", f"{PTS_WORKOUT} pts (1 por día)"),
        ("Hora de estudio", f"30 pts (hasta {STUDY_CAP_MIN // 60} h por día)"),
        ("Hábito cumplido", f"{PTS_HABIT} pts"),
        ("Día perfecto", f"+{PTS_PERFECT_DAY} pts"),
        ("Check-in del tablero", f"{PTS_CHECKIN} pts"),
        ("Meta semanal cumplida", f"+{PTS_WEEKLY_GOAL} pts cada una"),
    ]
    return render(request, "ranking.html", user=user, rows=rows, by=by, monday=week_start(today),
                  today=today, rules=rules, active="ranking")
