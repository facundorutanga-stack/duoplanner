from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import NutritionPrefs, NutritionProfile, User
from ..nutrition import (
    ACTIVITY, ALLERGIES, CATEGORIES, CONDITIONS, DIETS, FOODS, GOALS, INTOLERANCES, KCAL_FLOOR,
    MEALS_BY_COUNT, SOURCES, menu, restrictions, split, swaps, targets, warnings,
)
from ..security import current_user
from .common import flash, redirect, render

router = APIRouter(prefix="/nutricion")


def _profile(db: Session, user: User) -> NutritionProfile | None:
    return db.scalar(select(NutritionProfile).where(NutritionProfile.user_id == user.id))


def _prefs(db: Session, user: User, p: NutritionProfile | None, create: bool = False) -> NutritionPrefs:
    prefs = db.scalar(select(NutritionPrefs).where(NutritionPrefs.user_id == user.id))
    if prefs is None:
        # Quien ya tenía el plan de antes: se respeta lo que había marcado (vegetariano).
        prefs = NutritionPrefs(user_id=user.id, diet="vegetariana" if p and p.vegetarian else "omnivora",
                               meals_per_day=4, allergies="", intolerances="", conditions="", avoid="", other="")
        if create:
            db.add(prefs)
    return prefs


def _restr(prefs: NutritionPrefs):
    return restrictions(prefs.diet, split(prefs.allergies), split(prefs.intolerances),
                        split(prefs.conditions), split(prefs.avoid), prefs.other)


@router.get("")
def nutricion(request: Request, editar: bool = False, user: User = Depends(current_user),
              db: Session = Depends(get_db)):
    p = _profile(db, user)
    prefs = _prefs(db, user, p)
    r = _restr(prefs)
    ctx = dict(user=user, p=p, prefs=prefs, r=r, activity=ACTIVITY, goals=GOALS, sources=SOURCES,
               diets=DIETS, allergies=ALLERGIES, intolerances=INTOLERANCES, conditions=CONDITIONS,
               foods=FOODS, categories=CATEGORIES, meal_counts=MEALS_BY_COUNT, active="nutricion",
               editing=editar or p is None)
    if p:
        t = targets(p.sex, p.age, p.weight_kg, p.height_cm, p.activity, p.goal, r.conditions)
        meals, changes = menu(t, r, prefs.meals_per_day)
        by_protein, by_fiber = swaps(r)
        ctx.update(
            t=t, meals=meals, changes=changes, tips=warnings(r), by_protein=by_protein, by_fiber=by_fiber,
            floor=KCAL_FLOOR[p.sex], goal_label=GOALS[p.goal][3],
            total_kcal=round(sum(m.kcal for m in meals)), total_p=round(sum(m.protein for m in meals)),
            total_f=round(sum(m.fiber for m in meals)),
            avoided=[(k, FOODS[k][0]) for k in split(prefs.avoid) if k in FOODS],
        )
    return render(request, "nutricion.html", **ctx)


def _clean(values: list[str], allowed) -> str:
    return ",".join(dict.fromkeys(v for v in values if v in allowed))


@router.post("")
def save(request: Request, sex: str = Form("m"), age: int = Form(...), weight_kg: float = Form(...),
         height_cm: float = Form(...), activity: str = Form("moderada"), goal: str = Form("mantener"),
         diet: str = Form("omnivora"), meals_per_day: int = Form(4), allergies: list[str] = Form([]),
         intolerances: list[str] = Form([]), conditions: list[str] = Form([]), avoid: list[str] = Form([]),
         other: str = Form(""), user: User = Depends(current_user), db: Session = Depends(get_db)):
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
    prefs = _prefs(db, user, p, create=True)
    prefs.diet = diet if diet in DIETS else "omnivora"
    p.vegetarian = prefs.diet in ("vegetariana", "vegana")
    prefs.meals_per_day = meals_per_day if meals_per_day in MEALS_BY_COUNT else 4
    prefs.allergies = _clean(allergies, ALLERGIES)
    prefs.intolerances = _clean(intolerances, INTOLERANCES)
    prefs.conditions = _clean(conditions, CONDITIONS)
    prefs.avoid = _clean(avoid, FOODS)
    prefs.other = other.strip()[:300]
    db.commit()
    flash(request, "🥗 Plan calculado con tus datos y restricciones.")
    return redirect("/nutricion")


@router.post("/evitar")
def avoid_food(request: Request, key: str = Form(...), user: User = Depends(current_user),
               db: Session = Depends(get_db)):
    """Botón «me cae mal» en el menú: se saca ese alimento y el plan se rearma."""
    if key in FOODS:
        prefs = _prefs(db, user, _profile(db, user), create=True)
        prefs.avoid = _clean(split(prefs.avoid) + [key], FOODS)
        db.commit()
        flash(request, f"Listo, saqué {FOODS[key][0].lower()} de tu plan y lo reemplacé.")
    return redirect("/nutricion#menu")


@router.post("/permitir")
def allow_food(request: Request, key: str = Form(...), user: User = Depends(current_user),
               db: Session = Depends(get_db)):
    prefs = _prefs(db, user, _profile(db, user), create=True)
    prefs.avoid = _clean([k for k in split(prefs.avoid) if k != key], FOODS)
    db.commit()
    if key in FOODS:
        flash(request, f"{FOODS[key][0]} vuelve a estar en tu plan.")
    return redirect("/nutricion#menu")
