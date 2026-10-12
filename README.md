# DuoPlanner

Hábitos, estudio y gimnasio con ranking semanal y logros entre amigos.
Hecho en Python (FastAPI + HTMX), base de datos Postgres en Neon y hosting en Vercel. Todo gratis.

---

## 1. Probarla en tu compu (5 minutos)

Necesitás Python 3.11 o más nuevo.

```bash
cd duoplanner
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Abrí http://localhost:8000, creá una cuenta y listo. Sin configurar nada usa un archivo
`duoplanner.db` (SQLite) en la carpeta. Para probar el ranking, abrí una ventana de
incógnito y creá una segunda cuenta que se una con el código del grupo.

---

## 2. Subir el código a GitHub

1. Creá una cuenta en https://github.com si no tenés.
2. Arriba a la derecha: **+ → New repository**. Nombre: `duoplanner`. Dejalo **Private** si querés.
   No marques "Add a README". Tocá **Create repository**.
3. En la carpeta del proyecto:

```bash
git init
git add .
git commit -m "DuoPlanner MVP"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/duoplanner.git
git push -u origin main
```

(Si no usás la terminal, en la página del repo vacío tocá "uploading an existing file" y arrastrá
todo el contenido de la carpeta, menos `.venv` y `duoplanner.db`.)

---

## 3. Crear la base de datos en Neon

1. Entrá a https://neon.tech y registrate con tu cuenta de GitHub (plan **Free**, sin tarjeta).
2. **Create project**. Nombre: `duoplanner`. Región: la más cercana (por ejemplo `AWS São Paulo` si está, si no `US East`).
3. En el panel del proyecto tocá **Connect**. Activá **Connection pooling** y copiá la cadena
   que empieza con `postgresql://` y tiene **`-pooler`** en el medio. Guardala, la usás en el paso 4.

Las tablas se crean solas la primera vez que la app arranca.

---

## 4. Publicarla en Vercel

1. Entrá a https://vercel.com y registrate con GitHub (plan **Hobby**, gratis).
2. **Add New → Project** y elegí el repo `duoplanner` → **Import**.
3. Antes de tocar Deploy, abrí **Environment Variables** y agregá dos:

   | Nombre | Valor |
   | --- | --- |
   | `DATABASE_URL` | la cadena de Neon del paso 3 |
   | `SECRET_KEY` | una frase larga inventada, por ejemplo `mi-perro-come-fideos-los-martes-2026` |

4. Tocá **Deploy**. En uno o dos minutos te da una dirección tipo `https://duoplanner-xxxx.vercel.app`.
   En **Settings → Domains** podés cambiarla a algo como `duoplanner-tuyo.vercel.app` gratis.

Desde ahora, cada `git push` publica la versión nueva sola.

---

## 5. Instalarla en el celular e invitar a tus amigos

- **Android (Chrome):** abrí la dirección, menú ⋮ → **Instalar app**.
- **iPhone (Safari):** abrí la dirección, botón Compartir → **Agregar a inicio**.

Creá tu cuenta, después **Crear grupo**, y tocá **Compartir invitación**: les manda el link y el
código de 6 letras. Ellos se registran y ponen el código en **Unirme a un grupo**.

---

## Cómo funciona

| Qué | Puntos |
| --- | --- |
| Entrenamiento | 50 (1 por día) |
| Hora de estudio | 30 (se cuentan hasta 4 h por día) |
| Hábito cumplido | 10 |
| Día perfecto (todos los hábitos) | +20 |
| Check-in del tablero | 10 |
| Meta semanal cumplida (estudio, gimnasio, hábitos al 80 %) | +100 cada una |

- El **ranking** es semanal (lunes a domingo) y tiene dos vistas: puntos y % de cumplimiento de tus propias metas.
- La **racha** suma un día si cumpliste el 70 % de tus hábitos o cargaste estudio o gimnasio.
- Se puede cargar o borrar hasta **2 días hacia atrás**.
- **Mi tablero** (📊 en la barra de abajo): check-in diario de sueño, ejercicio, ánimo, energía, tiempo con
  familia y satisfacción con la vida. Suma estudio y ejercicio solos desde sus módulos, y además registrás
  ahorro mensual, libros o cursos terminados y objetivos de la semana. Muestra gráficos de 1, 3 y 6 meses y,
  con 14 check-ins o más, los patrones que encuentra (por ejemplo, cuánta más energía tenés cuando dormís 7 h).
  Es privado: tus amigos no lo ven.
- **Nutrición** (desde el inicio o el perfil): con tu edad, peso, altura, actividad y objetivo calcula
  calorías, proteína, fibra, grasas, carbohidratos y agua, y arma un día de ejemplo con porciones en gramos.
  Las fuentes científicas están en la misma pantalla y en `app/nutrition.py`. Es una guía para adultos
  sanos, no reemplaza a un nutricionista.
- Las metas semanales y el avatar se cambian en **Perfil** (tocá tu avatar arriba a la derecha).

Para cambiar las reglas, editá las constantes al principio de `app/points.py`.
Para agregar un logro, sumá una línea en `app/achievements.py`.

## Estructura

```
app/
  main.py           arranque de FastAPI, sesión y rutas
  db.py             conexión (SQLite local o Neon)
  models.py         tablas
  security.py       contraseñas y usuario logueado
  points.py         puntos, metas, rachas y ranking
  achievements.py   logros
  wellbeing.py      tablero personal: resúmenes y patrones
  nutrition.py      cálculos de nutrición, alimentos y menú
  routes/           una página por archivo
  templates/        HTML (Jinja2 + HTMX)
public/             CSS, íconos, manifest y service worker (Vercel los sirve directo)
```

## Si cambiás el diseño

Los estilos de Tailwind están precompilados en `public/tw.css`. Si agregás clases nuevas en las
plantillas, regeneralo (necesitás Node instalado):

```bash
npx tailwindcss@3.4.17 -i styles.css -o public/tw.css --minify
```

## Problemas comunes

- **"Internal Server Error" en Vercel:** revisá que `DATABASE_URL` esté bien copiada (Vercel → tu proyecto → Logs muestra el error).
- **Me deslogueó:** si cambiás `SECRET_KEY`, todas las sesiones se cierran. Es normal.
- **El primer acceso del día tarda un par de segundos:** es la base de Neon despertándose. Después va rápido.

## Próximos pasos (fase 2 del plan)

Recordatorios para el check-in, muro de logros con reacciones, gráficos de varias semanas, series y kg con récords en gimnasio,
tareas por materia, comodín de racha, módulos personalizados y notificaciones.
