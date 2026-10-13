import html
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from starlette.middleware.sessions import SessionMiddleware

from .db import Base, SessionLocal, engine
from .points import purge_archived_habits
from .routes import auth, group, gym, habits, home, nutricion, profile, ranking, study, tablero
from .security import LoginRequired


ON_VERCEL = bool(os.getenv("VERCEL"))
SECRET_KEY = os.getenv("SECRET_KEY", "")

# Si falta configuración, en vez de caerse la app muestra una página que dice qué arreglar.
PROBLEMS: list[str] = []
if ON_VERCEL and len(SECRET_KEY) < 16:
    PROBLEMS.append("Falta la variable SECRET_KEY en Vercel (o tiene menos de 16 caracteres).")
if ON_VERCEL and not os.getenv("DATABASE_URL"):
    PROBLEMS.append("Falta la variable DATABASE_URL en Vercel (la dirección de Neon).")


def _hide_password(text: str) -> str:
    return re.sub(r"(postgres(?:ql)?(?:\+\w+)?://[^:/@\s]+):[^@\s]+@", r"\1:****@", text)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not PROBLEMS:
        try:
            # Crea las tablas que falten. Para cambios de columnas más adelante, usá Alembic.
            Base.metadata.create_all(engine)
            with SessionLocal() as db:
                purge_archived_habits(db)
        except Exception as exc:  # noqa: BLE001 - queremos mostrar cualquier error de conexión
            PROBLEMS.append("No me pude conectar a la base de datos: "
                            + _hide_password(f"{type(exc).__name__}: {exc}")[:600])
    for p in PROBLEMS:
        print("CONFIGURACION:", p)
    yield

app = FastAPI(title="DuoPlanner", lifespan=lifespan, docs_url=None, redoc_url=None)
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY if len(SECRET_KEY) >= 16 else "solo-para-probar-en-tu-compu",
    max_age=60 * 60 * 24 * 60,  # 60 días logueado
    same_site="lax",
    https_only=bool(os.getenv("VERCEL")),
)


@app.middleware("http")
async def _config_check(request: Request, call_next):
    if not PROBLEMS:
        return await call_next(request)
    items = "".join(f"<li>{html.escape(p)}</li>" for p in PROBLEMS)
    page = f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DuoPlanner: falta configurar</title>
<body style="font-family:system-ui;background:#0b0b1a;color:#e2e8f0;max-width:640px;margin:40px auto;padding:0 16px">
<h1>🛠️ DuoPlanner todavía no puede arrancar</h1><ul>{items}</ul>
<p>Arreglalo en Vercel → Settings → Environment Variables y después hacé <b>Redeploy</b>.</p>
<p style="color:#94a3b8">Variables que ve la app: SECRET_KEY {"✅" if SECRET_KEY else "❌"} ·
DATABASE_URL {"✅" if os.getenv("DATABASE_URL") else "❌"}</p></body>"""
    return HTMLResponse(page, status_code=503)


@app.exception_handler(LoginRequired)
async def _login_required(request: Request, exc: LoginRequired):
    if request.headers.get("HX-Request"):
        return Response(status_code=200, headers={"HX-Redirect": "/login"})
    return RedirectResponse("/login", status_code=303)


for module in (auth, home, habits, study, gym, ranking, group, profile, tablero, nutricion):
    app.include_router(module.router)

# En Vercel, la carpeta public/ se sirve sola desde el CDN. En tu compu la servimos acá.
if not os.getenv("VERCEL"):
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=Path(__file__).resolve().parent.parent / "public"), name="public")
