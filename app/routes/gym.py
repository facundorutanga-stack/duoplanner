from datetime import date, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User, Workout
from ..points import WEEKDAYS, can_edit, week_start
from ..security import current_user, today_for
from .common import after_change, flash, redirect, render

router = APIRouter(prefix="/gym")


@router.get("")
def gym_page(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    today = today_for(user)
    monday = week_start(today)
    week_days = set(db.scalars(select(Workout.day).where(
        Workout.user_id == user.id, Workout.day.between(monday, monday + timedelta(days=6)))))
    count = len(list(db.scalars(select(Workout.id).where(
        Workout.user_id == user.id, Workout.day.between(monday, monday + timedelta(days=6))))))
    recent = list(db.scalars(select(Workout).where(Workout.user_id == user.id)
                             .order_by(Workout.day.desc(), Workout.id.desc()).limit(20)))
    return render(
        request, "gym.html", user=user, today=today, weekdays=WEEKDAYS, monday=monday,
        week=[monday + timedelta(days=i) in week_days for i in range(7)], count=count,
        goal=user.goal_workouts, pct=min(1.0, count / user.goal_workouts) if user.goal_workouts else 0,
        recent=recent, min_day=today - timedelta(days=2), can_edit=lambda d: can_edit(d, today), active="gym",
    )


@router.post("")
def add_workout(request: Request, name: str = Form(...), day: date = Form(...), detail: str = Form(""),
                user: User = Depends(current_user), db: Session = Depends(get_db)):
    today = today_for(user)
    name = name.strip()[:60]
    if not name:
        flash(request, "Ponele un nombre al entrenamiento.")
        return redirect("/gym")
    if not can_edit(day, today):
        flash(request, "Solo podés cargar hoy o hasta 2 días atrás.")
        return redirect("/gym")
    db.add(Workout(user_id=user.id, name=name, day=day, detail=detail.strip()[:2000]))
    db.flush()
    after_change(request, db, user, day, today)
    flash(request, f"💪 Entrenamiento guardado: {name}")
    return redirect("/gym")


@router.post("/{workout_id}/delete")
def delete_workout(request: Request, workout_id: int, user: User = Depends(current_user),
                   db: Session = Depends(get_db)):
    w = db.get(Workout, workout_id)
    if not w or w.user_id != user.id:
        raise HTTPException(404)
    today = today_for(user)
    if not can_edit(w.day, today):
        flash(request, "Ese registro ya no se puede borrar.")
        return redirect("/gym")
    day = w.day
    db.delete(w)
    db.flush()
    after_change(request, db, user, day, today)
    return redirect("/gym")
