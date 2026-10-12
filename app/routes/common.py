from datetime import date
from pathlib import Path

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..achievements import evaluate
from ..models import User
from ..points import recompute_day

templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def fecha_corta(d: date) -> str:
    return f"{d.day} {MESES[d.month - 1]}"


def fecha_larga(d: date) -> str:
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}"


templates.env.filters["fecha_corta"] = fecha_corta
templates.env.filters["fecha_larga"] = fecha_larga
templates.env.filters["pct"] = lambda x: f"{round(x * 100)}%"
templates.env.filters["horas"] = lambda m: f"{m // 60}h {m % 60:02d}m" if m % 60 else f"{m // 60}h"


def flash(request: Request, message: str) -> None:
    request.session.setdefault("flash", []).append(message)


def render(request: Request, name: str, **ctx):
    ctx.setdefault("flashes", request.session.pop("flash", []))
    return templates.TemplateResponse(request, name, ctx)


def redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


def after_change(request: Request, db: Session, user: User, day: date, today: date) -> None:
    """Recalcula puntos del día, revisa logros y guarda."""
    recompute_day(db, user, day)
    for a in evaluate(db, user, today):
        flash(request, f"{a.icon} ¡Logro desbloqueado! {a.title}")
    db.commit()
