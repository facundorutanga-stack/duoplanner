import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response
from starlette.middleware.sessions import SessionMiddleware

from .db import Base, engine
from .routes import auth, group, gym, habits, home, nutricion, profile, ranking, study, tablero
from .security import LoginRequired


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crea las tablas que falten. Para cambios de columnas más adelante, usá Alembic.
    Base.metadata.create_all(engine)
    yield


SECRET_KEY = os.getenv("SECRET_KEY", "")
if os.getenv("VERCEL") and len(SECRET_KEY) < 16:
    # Sin una clave propia cualquiera podría falsificar sesiones: mejor no arrancar.
    raise RuntimeError("Falta la variable SECRET_KEY en Vercel (mínimo 16 caracteres).")

app = FastAPI(title="DuoPlanner", lifespan=lifespan, docs_url=None, redoc_url=None)
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY or "solo-para-probar-en-tu-compu",
    max_age=60 * 60 * 24 * 60,  # 60 días logueado
    same_site="lax",
    https_only=bool(os.getenv("VERCEL")),
)


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
