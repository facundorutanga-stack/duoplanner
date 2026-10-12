from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Habit, User
from ..security import hash_password, verify_password
from .common import redirect, render

router = APIRouter()

DEFAULT_HABITS = [("💧", "Tomar 2 L de agua"), ("😴", "Dormir 8 horas"), ("📖", "Leer 20 minutos")]


@router.get("/login")
def login_form(request: Request):
    return render(request, "login.html")


@router.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))
    if not user or not verify_password(password, user.password_hash):
        return render(request, "login.html", error="Email o contraseña incorrectos.", email=email)
    request.session["user_id"] = user.id
    return redirect("/")


@router.get("/register")
def register_form(request: Request):
    return render(request, "register.html")


@router.post("/register")
def register(request: Request, name: str = Form(...), email: str = Form(...),
             password: str = Form(...), db: Session = Depends(get_db)):
    email = email.strip().lower()
    name = name.strip()[:40]
    error = None
    if len(password) < 8:
        error = "La contraseña tiene que tener al menos 8 caracteres."
    elif db.scalar(select(User).where(func.lower(User.email) == email)):
        error = "Ya hay una cuenta con ese email."
    elif not name:
        error = "Poné tu nombre."
    if error:
        return render(request, "register.html", error=error, name=name, email=email)
    user = User(name=name, email=email, password_hash=hash_password(password))
    db.add(user)
    db.flush()
    for icon, habit in DEFAULT_HABITS:
        db.add(Habit(user_id=user.id, name=habit, icon=icon))
    db.commit()
    request.session["user_id"] = user.id
    return redirect("/group")


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return redirect("/login")
