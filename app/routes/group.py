import secrets

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Group, User
from ..points import group_members
from ..security import current_user
from .common import flash, redirect, render

router = APIRouter(prefix="/group")

# Sin letras que se confunden (0/O, 1/I)
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _new_code(db: Session) -> str:
    while True:
        code = "".join(secrets.choice(_ALPHABET) for _ in range(6))
        if not db.scalar(select(Group).where(Group.invite_code == code)):
            return code


@router.get("")
def group_page(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return render(request, "group.html", user=user, group=user.group, members=group_members(db, user),
                  active="group")


@router.post("/create")
def create(request: Request, name: str = Form(...), user: User = Depends(current_user),
           db: Session = Depends(get_db)):
    group = Group(name=name.strip()[:60] or "Mi grupo", invite_code=_new_code(db))
    db.add(group)
    db.flush()
    user.group_id = group.id
    db.commit()
    flash(request, f"Grupo creado. Pasale el código {group.invite_code} a tus amigos.")
    return redirect("/group")


@router.post("/join")
def join(request: Request, code: str = Form(...), user: User = Depends(current_user),
         db: Session = Depends(get_db)):
    group = db.scalar(select(Group).where(Group.invite_code == code.strip().upper()))
    if not group:
        flash(request, "No encontré un grupo con ese código.")
        return redirect("/group")
    user.group_id = group.id
    db.commit()
    flash(request, f"¡Entraste a {group.name}!")
    return redirect("/")


@router.post("/leave")
def leave(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.group_id = None
    db.commit()
    flash(request, "Saliste del grupo.")
    return redirect("/group")
