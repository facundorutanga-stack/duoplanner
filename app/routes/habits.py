from datetime import date, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Habit, HabitCheck, User
from ..points import EDIT_WINDOW_DAYS, WEEKDAYS, active_habits, can_edit, streak, week_start
from ..security import current_user, today_for
from .common import after_change, flash, redirect, render

router = APIRouter(prefix="/habits")


def _parse_day(d: str | None, today: date) -> date:
    try:
        day = date.fromisoformat(d) if d else today
    except ValueError:
        day = today
    return day if can_edit(day, today) else today


def _row_ctx(db: Session, user: User, habit: Habit, day: date) -> dict:
    monday = week_start(day)
    checks = set(db.scalars(select(HabitCheck.day).where(
        HabitCheck.habit_id == habit.id, HabitCheck.day.between(monday, monday + timedelta(days=6)))))
    return {"habit": habit, "done": day in checks, "week": [monday + timedelta(days=i) in checks for i in range(7)]}


@router.get("")
def habits_page(request: Request, d: str | None = None, user: User = Depends(current_user),
                db: Session = Depends(get_db)):
    today = today_for(user)
    day = _parse_day(d, today)
    rows = [_row_ctx(db, user, h, day) for h in active_habits(db, user.id)]
    return render(
        request, "habits.html", user=user, day=day, today=today, rows=rows, weekdays=WEEKDAYS,
        prev_day=day - timedelta(days=1) if can_edit(day - timedelta(days=1), today) else None,
        next_day=day + timedelta(days=1) if day < today else None,
        done=sum(r["done"] for r in rows), streak=streak(db, user, today),
        window=EDIT_WINDOW_DAYS, active="habits",
    )


@router.post("")
def create_habit(request: Request, name: str = Form(...), icon: str = Form("✅"),
                 user: User = Depends(current_user), db: Session = Depends(get_db)):
    name = name.strip()[:60]
    if name:
        db.add(Habit(user_id=user.id, name=name, icon=(icon.strip() or "✅")[:8]))
        db.commit()
        flash(request, f"Hábito agregado: {name}")
    return redirect("/habits")


def _own_habit(db: Session, user: User, habit_id: int) -> Habit:
    habit = db.get(Habit, habit_id)
    if not habit or habit.user_id != user.id:
        raise HTTPException(404)
    return habit


@router.post("/{habit_id}/toggle")
def toggle(request: Request, habit_id: int, d: str | None = None, user: User = Depends(current_user),
           db: Session = Depends(get_db)):
    today = today_for(user)
    day = _parse_day(d, today)
    habit = _own_habit(db, user, habit_id)
    check = db.scalar(select(HabitCheck).where(HabitCheck.habit_id == habit.id, HabitCheck.day == day))
    if check:
        db.delete(check)
    else:
        db.add(HabitCheck(habit_id=habit.id, user_id=user.id, day=day))
    db.flush()
    after_change(request, db, user, day, today)
    if not request.headers.get("HX-Request"):
        return redirect(f"/habits?d={day.isoformat()}")
    # Con HTMX devolvemos solo la fila; los logros nuevos se muestran como aviso.
    return render(request, "partials/habit_row.html", day=day, weekdays=WEEKDAYS, oob=True,
                  **_row_ctx(db, user, habit, day))


@router.post("/{habit_id}/delete")
def archive(request: Request, habit_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    habit = _own_habit(db, user, habit_id)
    habit.active = False
    today = today_for(user)
    after_change(request, db, user, today, today)
    flash(request, f"Hábito archivado: {habit.name}")
    return redirect("/habits")
