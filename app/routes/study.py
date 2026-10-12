from datetime import date, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import StudySession, User
from ..points import WEEKDAYS, can_edit, week_start
from ..security import current_user, today_for
from .common import after_change, flash, redirect, render

router = APIRouter(prefix="/study")


@router.get("")
def study_page(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    today = today_for(user)
    monday = week_start(today)
    sunday = monday + timedelta(days=6)
    week = list(db.scalars(select(StudySession).where(
        StudySession.user_id == user.id, StudySession.day.between(monday, sunday))))
    per_day = [sum(s.minutes for s in week if s.day == monday + timedelta(days=i)) for i in range(7)]
    subjects: dict[str, int] = {}
    for s in week:
        subjects[s.subject] = subjects.get(s.subject, 0) + s.minutes
    known = list(db.scalars(select(StudySession.subject).where(StudySession.user_id == user.id)
                            .group_by(StudySession.subject).order_by(func.max(StudySession.id).desc()).limit(8)))
    recent = list(db.scalars(select(StudySession).where(StudySession.user_id == user.id)
                             .order_by(StudySession.day.desc(), StudySession.id.desc()).limit(15)))
    total = sum(per_day)
    return render(
        request, "study.html", user=user, today=today, weekdays=WEEKDAYS, per_day=per_day,
        max_day=max(per_day + [60]), total=total, goal=user.goal_study_min,
        pct=min(1.0, total / user.goal_study_min) if user.goal_study_min else 0,
        subjects=sorted(subjects.items(), key=lambda kv: -kv[1]), known=known, recent=recent,
        min_day=today - timedelta(days=2), can_edit=lambda d: can_edit(d, today), active="study",
    )


@router.post("")
def add_session(request: Request, subject: str = Form(...), hours: int = Form(0), minutes: int = Form(0),
                day: date = Form(...), note: str = Form(""), user: User = Depends(current_user),
                db: Session = Depends(get_db)):
    today = today_for(user)
    total = max(0, hours) * 60 + max(0, minutes)
    subject = subject.strip()[:60]
    if not subject or total <= 0 or total > 16 * 60:
        flash(request, "Revisá la materia y el tiempo (entre 1 minuto y 16 horas).")
        return redirect("/study")
    if not can_edit(day, today):
        flash(request, "Solo podés cargar hoy o hasta 2 días atrás.")
        return redirect("/study")
    db.add(StudySession(user_id=user.id, subject=subject, minutes=total, day=day, note=note.strip()[:500]))
    db.flush()
    after_change(request, db, user, day, today)
    flash(request, f"📚 {total} min de {subject} cargados")
    return redirect("/study")


@router.post("/{session_id}/delete")
def delete_session(request: Request, session_id: int, user: User = Depends(current_user),
                   db: Session = Depends(get_db)):
    s = db.get(StudySession, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(404)
    today = today_for(user)
    if not can_edit(s.day, today):
        flash(request, "Ese registro ya no se puede borrar.")
        return redirect("/study")
    day = s.day
    db.delete(s)
    db.flush()
    after_change(request, db, user, day, today)
    return redirect("/study")
