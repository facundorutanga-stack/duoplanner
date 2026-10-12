from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import NutritionProfile, User
from ..nutrition import ACTIVITY, FOODS, GOALS, KCAL_FLOOR, SOURCES, menu, swaps, targets
from ..security import current_user
from .common import flash, redirect, render

router = APIRouter(prefix="/nutricion")


def _profile(db: Session, user: User) -> NutritionProfile | None:
    return db.scalar(select(NutritionProfile).where(NutritionProfile.user_id == user.id))


@router.get("")
def nutricion(request: Request, editar: bool = False, user: User = Depends(current_user),
              db: Session = Depends(get_db)):
    p = _profile(db, user)
    ctx = dict(user=user, p=p, activity=ACTIVITY, goals=GOALS, sources=SOURCES, active="nutricion",
               editing=editar or p is None)
    if p:
        t = targets(p.sex, p.age, p.weight_kg, p.height_cm, p.activity, p.goal)
        meals = menu(t, p.vegetarian)
        by_protein, by_fiber = swaps(p.vegetarian)
        ctx.update(
            t=t, meals=meals, by_protein=by_protein, by_fiber=by_fiber, floor=KCAL_FLOOR[p.sex],
            total_kcal=round(sum(m.kcal for m in meals)), total_p=round(sum(m.protein for m in meals)),
            total_f=round(sum(m.fiber for m in meals)), goal_label=GOALS[p.goal][3],
        )
    return render(request, "nutricion.html", **ctx)


@router.post("")
def save(request: Request, sex: str = Form("m"), age: int = Form(...), weight_kg: float = Form(...),
         height_cm: float = Form(...), activity: str = Form("moderada"), goal: str = Form("mantener"),
         vegetarian: bool = Form(False), user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not (16 <= age <= 90 and 30 <= weight_kg <= 300 and 120 <= height_cm <= 230):
        flash(request, "Revisá los datos: edad 16-90, peso 30-300 kg, altura 120-230 cm.")
        return redirect("/nutricion?editar=1")
    p = _profile(db, user)
    if p is None:
        p = NutritionProfile(user_id=user.id)
        db.add(p)
    p.sex = "f" if sex == "f" else "m"
    p.age, p.weight_kg, p.height_cm = age, weight_kg, height_cm
    p.activity = activity if activity in ACTIVITY else "moderada"
    p.goal = goal if goal in GOALS else "mantener"
    p.vegetarian = vegetarian
    db.commit()
    flash(request, "🥗 Plan calculado con tus datos.")
    return redirect("/nutricion")
