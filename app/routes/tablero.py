import json
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Completion, DailyLog, MonthlySaving, User, WeeklyGoal, Workout
from ..points import can_edit, week_start
from ..security import current_user, today_for
from ..wellbeing import MIN_DAYS_FOR_PATTERNS, chart_data, days_range, patterns, summary
from .common import MESES, after_change, flash, redirect, render

router = APIRouter(prefix="/tablero")

QUOTE = "Lo que se mide, mejora; lo que se revisa periódicamente, mejora aún más."
RANGES = {30: "1 mes", 90: "3 meses", 180: "6 meses"}


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _clamp(v: int | None, lo=1, hi=10) -> int | None:
    return None if v is None else max(lo, min(hi, v))


@router.get("")
def tablero(request: Request, rango: int = 30, d: str | None = None,
            user: User = Depends(current_user), db: Session = Depends(get_db)):
    today = today_for(user)
    rango = rango if rango in RANGES else 30
    try:
        day = date.fromisoformat(d) if d else today
    except ValueError:
        day = today
    if not can_edit(day, today):
        day = today

    log = db.scalar(select(DailyLog).where(DailyLog.user_id == user.id, DailyLog.day == day))
    trained = db.scalar(select(func.count()).select_from(Workout).where(
        Workout.user_id == user.id, Workout.day == day)) or 0

    days = days_range(db, user, today - timedelta(days=rango - 1), today)
    last7 = summary(days[-7:])
    prev7 = summary(days[-14:-7]) if len(days) >= 14 else None
    found = patterns(days)
    logged_total = summary(days)["logged"]

    monday = week_start(today)
    goals = list(db.scalars(select(WeeklyGoal).where(
        WeeklyGoal.user_id == user.id, WeeklyGoal.week_start == monday).order_by(WeeklyGoal.id)))
    month = _month_start(today)
    savings = list(db.scalars(select(MonthlySaving).where(MonthlySaving.user_id == user.id)
                              .order_by(MonthlySaving.month.desc()).limit(6)))
    this_month = next((s.amount for s in savings if s.month == month), None)
    completions = list(db.scalars(select(Completion).where(Completion.user_id == user.id)
                                  .order_by(Completion.day.desc(), Completion.id.desc()).limit(20)))
    year_count = sum(1 for c in completions if c.day.year == today.year)

    return render(
        request, "tablero.html", user=user, today=today, day=day, log=log, trained=trained > 0,
        quote=QUOTE, rango=rango, ranges=RANGES, last7=last7, prev7=prev7, patterns=found,
        need_days=max(0, MIN_DAYS_FOR_PATTERNS - logged_total), logged_total=logged_total,
        chart=json.dumps(chart_data(days)), goals=goals, goals_done=sum(g.done for g in goals),
        savings=savings, this_month=this_month, max_saving=max([abs(s.amount) for s in savings] + [1]),
        month_label=f"{MESES[today.month - 1]} {today.year}", completions=completions, year_count=year_count,
        meses=MESES, can_edit=lambda x: can_edit(x, today), active="tablero",
        prev_day=day - timedelta(days=1) if can_edit(day - timedelta(days=1), today) else None,
        next_day=day + timedelta(days=1) if day < today else None,
    )


@router.post("/checkin")
def checkin(request: Request, day: date = Form(...), sleep_h: float | None = Form(None),
            exercised: bool = Form(False), mood: int | None = Form(None), energy: int | None = Form(None),
            family_h: float = Form(0), satisfaction: int | None = Form(None), note: str = Form(""),
            user: User = Depends(current_user), db: Session = Depends(get_db)):
    today = today_for(user)
    if not can_edit(day, today):
        flash(request, "Solo podés cargar hoy o hasta 2 días atrás.")
        return redirect("/tablero")
    log = db.scalar(select(DailyLog).where(DailyLog.user_id == user.id, DailyLog.day == day))
    if log is None:
        log = DailyLog(user_id=user.id, day=day)
        db.add(log)
    log.sleep_h = None if sleep_h is None else max(0.0, min(16.0, sleep_h))
    log.exercised = exercised
    log.mood, log.energy, log.satisfaction = _clamp(mood), _clamp(energy), _clamp(satisfaction)
    log.family_min = int(max(0.0, min(24.0, family_h)) * 60)
    log.note = note.strip()[:500]
    db.flush()
    after_change(request, db, user, day, today)
    flash(request, "📊 Check-in guardado. ¡Lo que se mide, mejora!")
    return redirect(f"/tablero?d={day.isoformat()}")


@router.post("/ahorro")
def save_saving(request: Request, month: str = Form(...), amount: float = Form(...),
                user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        m = date.fromisoformat(month + "-01")
    except ValueError:
        flash(request, "Mes inválido.")
        return redirect("/tablero#ahorro")
    row = db.scalar(select(MonthlySaving).where(MonthlySaving.user_id == user.id, MonthlySaving.month == m))
    if row is None:
        row = MonthlySaving(user_id=user.id, month=m)
        db.add(row)
    row.amount = amount
    db.commit()
    flash(request, "💰 Ahorro del mes guardado.")
    return redirect("/tablero#ahorro")


@router.post("/completado")
def add_completion(request: Request, kind: str = Form("libro"), title: str = Form(...),
                   user: User = Depends(current_user), db: Session = Depends(get_db)):
    title = title.strip()[:120]
    if title:
        db.add(Completion(user_id=user.id, day=today_for(user), kind="curso" if kind == "curso" else "libro",
                          title=title))
        db.commit()
        flash(request, f"🎉 ¡Terminaste {title}!")
    return redirect("/tablero#libros")


@router.post("/completado/{cid}/delete")
def delete_completion(request: Request, cid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = db.get(Completion, cid)
    if not c or c.user_id != user.id:
        raise HTTPException(404)
    db.delete(c)
    db.commit()
    return redirect("/tablero#libros")


@router.post("/objetivos")
def add_goal(request: Request, text: str = Form(...), user: User = Depends(current_user),
             db: Session = Depends(get_db)):
    text = text.strip()[:120]
    if text:
        db.add(WeeklyGoal(user_id=user.id, week_start=week_start(today_for(user)), text=text))
        db.commit()
    return redirect("/tablero#objetivos")


def _own_goal(db: Session, user: User, gid: int) -> WeeklyGoal:
    g = db.get(WeeklyGoal, gid)
    if not g or g.user_id != user.id:
        raise HTTPException(404)
    return g


@router.post("/objetivos/{gid}/toggle")
def toggle_goal(request: Request, gid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    g = _own_goal(db, user, gid)
    g.done = not g.done
    db.commit()
    return redirect("/tablero#objetivos")


@router.post("/objetivos/{gid}/delete")
def delete_goal(request: Request, gid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(_own_goal(db, user, gid))
    db.commit()
    return redirect("/tablero#objetivos")
