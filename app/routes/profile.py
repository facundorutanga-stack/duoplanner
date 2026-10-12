from zoneinfo import available_timezones

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..achievements import ACHIEVEMENTS
from ..db import get_db
from ..models import User, UserAchievement
from ..points import best_streak, group_members, recompute_day, streak
from ..security import current_user, today_for
from .common import flash, redirect, render
from .home import achievement_feed

router = APIRouter()

AVATARS = ["🙂", "😎", "🦊", "🐼", "🦁", "🐸", "🐺", "🦉", "🐯", "🐨", "👾", "🤖"]


@router.get("/profile")
def profile_page(request: Request, user: User = Depends(current_user)):
    return render(request, "profile.html", user=user, avatars=AVATARS, active="profile")


@router.post("/profile")
def save_profile(request: Request, name: str = Form(...), avatar: str = Form("🙂"),
                 goal_study_hours: float = Form(10), goal_workouts: int = Form(3),
                 tz: str = Form("America/Argentina/Buenos_Aires"),
                 user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.name = name.strip()[:40] or user.name
    user.avatar = avatar if avatar in AVATARS else user.avatar
    user.goal_study_min = max(0, min(int(goal_study_hours * 60), 100 * 60))
    user.goal_workouts = max(0, min(goal_workouts, 14))
    if tz in available_timezones():
        user.tz = tz
    recompute_day(db, user, today_for(user))  # las metas cambian el bonus de la semana
    db.commit()
    flash(request, "Perfil guardado.")
    return redirect("/profile")


@router.get("/logros")
def achievements_page(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    today = today_for(user)
    mine = set(db.scalars(select(UserAchievement.code).where(UserAchievement.user_id == user.id)))
    return render(
        request, "achievements.html", user=user, all=ACHIEVEMENTS, mine=mine,
        feed=achievement_feed(db, group_members(db, user)), streak=streak(db, user, today),
        best=best_streak(db, user, today), active="logros",
    )
