from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..achievements import BY_CODE
from ..db import get_db
from ..models import DailyLog, HabitCheck, User, UserAchievement
from ..points import WEEKDAYS, active_habits, group_members, ranking, week_start
from ..security import current_user, today_for
from .common import render

router = APIRouter()


def achievement_feed(db: Session, members: list[User], limit: int = 20) -> list[dict]:
    by_id = {m.id: m for m in members}
    rows = db.scalars(
        select(UserAchievement).where(UserAchievement.user_id.in_(by_id))
        .order_by(UserAchievement.unlocked_at.desc()).limit(limit)
    )
    return [{"user": by_id[r.user_id], "a": BY_CODE[r.code], "when": r.unlocked_at}
            for r in rows if r.code in BY_CODE]


@router.get("/")
def home(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    today = today_for(user)
    rows = ranking(db, user, today)
    me = next(r for r in rows if r["me"])
    # Vos primero, después el resto por puntos
    people = [me] + [r for r in rows if not r["me"]]
    habits = active_habits(db, user.id)
    done_today = len(list(db.scalars(select(HabitCheck.id).where(
        HabitCheck.user_id == user.id, HabitCheck.day == today))))
    checked_in = db.scalar(select(DailyLog.id).where(DailyLog.user_id == user.id, DailyLog.day == today))
    return render(
        request, "home.html", checked_in=checked_in is not None, user=user, today=today, monday=week_start(today), weekdays=WEEKDAYS,
        people=people, rows=rows, me=me["stats"], n_habits=len(habits), done_today=done_today,
        feed=achievement_feed(db, group_members(db, user), limit=5), active="home",
    )
