"""Objetivos nutricionales y un menú de ejemplo, basados en evidencia.

Fuentes (también se muestran en la app):
- Gasto en reposo: ecuación de Mifflin-St Jeor (1990), la más precisa en adultos sanos.
- Proteína: Morton et al. 2018 (BJSM, meta-análisis): el beneficio en masa muscular se
  estabiliza cerca de 1,6 g/kg/día, con límite superior de confianza ~2,2 g/kg.
  ISSN 2017: 1,4-2,0 g/kg/día para quien entrena; en déficit calórico, más alto (hasta 2,2+).
  Schoenfeld y Aragon 2018: repartirla en 4 comidas de ~0,4 g/kg.
- Fibra: OMS 2023 (al menos 25 g/día) y 14 g por cada 1000 kcal (Guías Alimentarias de EE. UU.).
- Grasas, azúcar, sal, frutas y verduras: OMS, "Healthy diet" (≤30 % grasas, <10 % saturadas,
  <10 % azúcares libres, <5 g de sal, ≥400 g de frutas y verduras).
- Agua: EFSA 2010 (2,0 L/día mujeres y 2,5 L/día hombres en total; ~80 % viene de bebidas).
- Valores de alimentos: aproximados de USDA FoodData Central.

No reemplaza a un profesional: no aplica a embarazo, lactancia, menores ni enfermedades.
"""
from dataclasses import dataclass, field

ACTIVITY = {
    "sedentaria": (1.2, "Sedentaria (casi sin ejercicio)"),
    "ligera": (1.375, "Ligera (1-3 días por semana)"),
    "moderada": (1.55, "Moderada (3-5 días por semana)"),
    "alta": (1.725, "Alta (6-7 días por semana)"),
    "muy_alta": (1.9, "Muy alta (doble turno o trabajo físico)"),
}
GOALS = {
    "perder": (0.80, 2.0, (1.8, 2.2), "Perder grasa"),
    "mantener": (1.00, 1.6, (1.4, 1.8), "Mantener y mejorar salud"),
    "ganar": (1.10, 1.8, (1.6, 2.2), "Ganar músculo"),
}
SOURCES = [
    ("Mifflin-St Jeor 1990, gasto en reposo", "https://pubmed.ncbi.nlm.nih.gov/2305711/"),
    ("Morton et al. 2018, proteína y masa muscular (BJSM)", "https://pubmed.ncbi.nlm.nih.gov/28698222/"),
    ("Jäger et al. 2017, posición de la ISSN sobre proteína", "https://pubmed.ncbi.nlm.nih.gov/28642676/"),
    ("Schoenfeld y Aragon 2018, proteína por comida", "https://pubmed.ncbi.nlm.nih.gov/29497353/"),
    ("Reynolds et al. 2019, fibra y salud (The Lancet)", "https://pubmed.ncbi.nlm.nih.gov/30638909/"),
    ("OMS, alimentación saludable", "https://www.who.int/news-room/fact-sheets/detail/healthy-diet"),
    ("EFSA 2010, ingesta de agua", "https://www.efsa.europa.eu/en/efsajournal/pub/1459"),
    ("Guías de alergias alimentarias (NIAID 2010 / EAACI 2014)", "https://pubmed.ncbi.nlm.nih.gov/21134576/"),
    ("Intolerancia a la lactosa: hasta ~12 g por toma suele tolerarse (Shaukat 2010)", "https://pubmed.ncbi.nlm.nih.gov/20404262/"),
    ("KDIGO 2024, proteína en enfermedad renal crónica", "https://kdigo.org/guidelines/ckd-evaluation-and-management/"),
    ("Dieta DASH para presión alta (NIH)", "https://www.nhlbi.nih.gov/education/dash-eating-plan"),
    ("USDA FoodData Central, composición de alimentos", "https://fdc.nal.usda.gov/"),
]


KCAL_FLOOR = {"m": 1500, "f": 1200}


@dataclass
class Targets:
    bmr: int
    tdee: int
    kcal: int
    protein_g: int
    protein_range: tuple[int, int]
    protein_per_meal: int
    fiber_g: int
    fat_g: int
    sat_fat_max_g: int
    carbs_g: int
    sugar_max_g: int
    water_l: float
    salt_max_g: int = 5
    fruit_veg_g: int = 400


def targets(sex: str, age: int, weight: float, height: float, activity: str, goal: str,
            conditions: frozenset = frozenset()) -> Targets:
    bmr = 10 * weight + 6.25 * height - 5 * age + (5 if sex == "m" else -161)
    factor = ACTIVITY.get(activity, ACTIVITY["moderada"])[0]
    tdee = bmr * factor
    kcal_factor, g_per_kg, (lo, hi), _ = GOALS.get(goal, GOALS["mantener"])
    if "embarazo" in conditions:
        kcal_factor = 1.0  # nunca déficit ni superávit sin un profesional
    if "renal" in conditions:
        # Con enfermedad renal crónica no se aumenta la proteína (KDIGO 2024: ~0,8 g/kg).
        g_per_kg, lo, hi = 0.8, 0.6, 0.8
    # Piso de seguridad: por debajo de esto, solo con seguimiento profesional.
    kcal = max(tdee * kcal_factor, KCAL_FLOOR[sex])
    # Con IMC ≥ 30 la proteína se calcula sobre el peso de IMC 25 (si no, sale inflada).
    h_m = height / 100
    ref_weight = min(weight, 25 * h_m * h_m) if weight / (h_m * h_m) >= 30 else weight
    protein = g_per_kg * ref_weight
    fat = 0.27 * kcal / 9
    carbs = max(0, (kcal - protein * 4 - fat * 9) / 4)
    return Targets(
        bmr=round(bmr), tdee=round(tdee), kcal=round(kcal / 10) * 10,
        protein_g=round(protein), protein_range=(round(lo * ref_weight), round(hi * ref_weight)),
        protein_per_meal=round(0.4 * ref_weight),
        fiber_g=round(max(25, 14 * kcal / 1000)),
        fat_g=round(fat), sat_fat_max_g=round((0.07 if "colesterol" in conditions else 0.10) * kcal / 9),
        carbs_g=round(carbs), sugar_max_g=round(0.10 * kcal / 4),
        water_l=2.0 if sex == "m" else 1.6,
    )


# nombre, gramos o ml por porción (o None), unidad, kcal, proteína g, fibra g, categoría
FOODS = {
    "pollo": ("Pechuga de pollo cocida", 100, "porción", 165, 31, 0, "Carnes, pescado y huevo"),
    "carne": ("Carne vacuna magra cocida", 100, "porción", 215, 26, 0, "Carnes, pescado y huevo"),
    "merluza": ("Merluza cocida", 100, "porción", 105, 22, 0, "Carnes, pescado y huevo"),
    "salmon": ("Salmón cocido", 100, "porción", 206, 25, 0, "Carnes, pescado y huevo"),
    "atun": ("Atún al natural escurrido", 100, "porción", 116, 25, 0, "Carnes, pescado y huevo"),
    "huevo": ("Huevo", None, "huevo", 72, 6.3, 0, "Carnes, pescado y huevo"),
    "yogur": ("Yogur griego natural descremado", 170, "pote", 100, 17, 0, "Lácteos y bebidas"),
    "yogur_sl": ("Yogur griego sin lactosa", 170, "pote", 100, 17, 0, "Lácteos y bebidas"),
    "cottage": ("Queso cottage", 100, "porción", 98, 11, 0, "Lácteos y bebidas"),
    "leche": ("Leche", 250, "vaso", 120, 8, 0, "Lácteos y bebidas"),
    "leche_sl": ("Leche deslactosada", 250, "vaso", 120, 8, 0, "Lácteos y bebidas"),
    "bebida_soja": ("Bebida de soja fortificada", 250, "vaso", 100, 7, 1, "Lácteos y bebidas"),
    "bebida_arroz": ("Bebida de arroz fortificada", 250, "vaso", 115, 0.7, 0.7, "Lácteos y bebidas"),
    "yogur_soja": ("Yogur de soja natural", 150, "pote", 80, 6, 1, "Lácteos y bebidas"),
    "seitan": ("Seitán", 100, "porción", 140, 25, 1, "Legumbres y soja"),
    "tofu": ("Tofu firme", 100, "porción", 144, 17, 2.3, "Legumbres y soja"),
    "lentejas": ("Lentejas cocidas", 198, "taza", 230, 18, 15.6, "Legumbres y soja"),
    "garbanzos": ("Garbanzos cocidos", 164, "taza", 269, 14.5, 12.5, "Legumbres y soja"),
    "porotos": ("Porotos negros cocidos", 172, "taza", 227, 15, 15, "Legumbres y soja"),
    "avena": ("Avena", 40, "porción", 152, 5.3, 4, "Cereales y tubérculos"),
    "avena_sin_tacc": ("Avena certificada sin TACC", 40, "porción", 152, 5.3, 4, "Cereales y tubérculos"),
    "pan": ("Pan integral", 64, "2 rebanadas", 160, 8, 4, "Cereales y tubérculos"),
    "pan_sin_tacc": ("Pan sin TACC", 64, "2 rebanadas", 160, 3, 3, "Cereales y tubérculos"),
    "arroz": ("Arroz integral cocido", 195, "taza", 218, 5, 3.5, "Cereales y tubérculos"),
    "quinoa": ("Quinoa cocida", 185, "taza", 222, 8.1, 5.2, "Cereales y tubérculos"),
    "fideos": ("Fideos integrales cocidos", 140, "taza", 174, 7.5, 6.3, "Cereales y tubérculos"),
    "papa": ("Papa con cáscara", 173, "mediana", 161, 4.3, 3.8, "Cereales y tubérculos"),
    "batata": ("Batata", 130, "mediana", 112, 2, 3.9, "Cereales y tubérculos"),
    "banana": ("Banana", 118, "mediana", 105, 1.3, 3.1, "Frutas"),
    "manzana": ("Manzana", 182, "mediana", 95, 0.5, 4.4, "Frutas"),
    "pera": ("Pera", 178, "mediana", 101, 0.6, 5.5, "Frutas"),
    "naranja": ("Naranja", 131, "mediana", 62, 1.2, 3.1, "Frutas"),
    "frutillas": ("Frutillas", 152, "taza", 49, 1, 3, "Frutas"),
    "brocoli": ("Brócoli cocido", 156, "taza", 55, 3.7, 5.1, "Verduras"),
    "chauchas": ("Chauchas cocidas", 125, "taza", 44, 2.4, 4, "Verduras"),
    "zapallito": ("Zapallitos cocidos", 180, "taza", 27, 2, 1.8, "Verduras"),
    "ensalada": ("Ensalada de lechuga y tomate", 150, "plato", 25, 1.3, 1.8, "Verduras"),
    "zanahoria": ("Zanahoria", 61, "mediana", 25, 0.6, 1.7, "Verduras"),
    "palta": ("Palta", 100, "media", 160, 2, 6.7, "Frutos secos, semillas y grasas"),
    "almendras": ("Almendras", 28, "puñado", 164, 6, 3.5, "Frutos secos, semillas y grasas"),
    "mani": ("Maní", 28, "puñado", 161, 7, 2.4, "Frutos secos, semillas y grasas"),
    "semillas_zapallo": ("Semillas de zapallo", 28, "puñado", 158, 8.5, 1.7, "Frutos secos, semillas y grasas"),
    "chia": ("Semillas de chía", 28, "2 cucharadas", 138, 4.7, 9.8, "Frutos secos, semillas y grasas"),
    "whey": ("Proteína whey (según marca)", 30, "scoop", 120, 24, 0, "Suplementos"),
    "proteina_vegetal": ("Proteína vegetal en polvo (arveja)", 30, "scoop", 115, 24, 1, "Suplementos"),
}
LIQUIDS = {"leche", "leche_sl", "bebida_soja", "bebida_arroz"}
CATEGORIES = list(dict.fromkeys(f[6] for f in FOODS.values()))

# Qué contiene cada alimento (para alergias, intolerancias y tipo de dieta).
TAGS = {
    "pollo": {"ave"}, "carne": {"carne"}, "merluza": {"pescado"}, "salmon": {"pescado"},
    "atun": {"pescado"}, "huevo": {"huevo"},
    "yogur": {"lacteo", "lactosa"}, "cottage": {"lacteo", "lactosa"}, "leche": {"lacteo", "lactosa"},
    "whey": {"lacteo", "lactosa"}, "yogur_sl": {"lacteo"}, "leche_sl": {"lacteo"},
    "tofu": {"soja"}, "bebida_soja": {"soja"}, "yogur_soja": {"soja"},
    "lentejas": {"legumbre"}, "garbanzos": {"legumbre"}, "porotos": {"legumbre"},
    "avena": {"gluten"}, "seitan": {"gluten"}, "pan": {"gluten"}, "fideos": {"gluten"},
    "brocoli": {"crucifera"}, "almendras": {"frutos_secos"}, "mani": {"mani"},
}

DIETS = {
    "omnivora": ("Como de todo", set()),
    "pescetariana": ("Pescetariana (sin carne ni pollo)", {"carne", "ave"}),
    "vegetariana": ("Vegetariana (con huevo y lácteos)", {"carne", "ave", "pescado", "mariscos"}),
    "vegana": ("Vegana", {"carne", "ave", "pescado", "mariscos", "huevo", "lacteo"}),
}
# clave: (lo que ve en el formulario, cómo se nombra en las explicaciones, qué excluye)
ALLERGIES = {
    "gluten": ("Celiaquía (gluten / TACC)", "celiaquía", {"gluten"}),
    "leche": ("Leche de vaca (proteína)", "alergia a la leche", {"lacteo"}),
    "huevo": ("Huevo", "alergia al huevo", {"huevo"}),
    "mani": ("Maní", "alergia al maní", {"mani"}),
    "frutos_secos": ("Frutos secos", "alergia a los frutos secos", {"frutos_secos"}),
    "pescado": ("Pescado", "alergia al pescado", {"pescado"}),
    "mariscos": ("Mariscos", "alergia a los mariscos", {"mariscos"}),
    "soja": ("Soja", "alergia a la soja", {"soja"}),
    "sesamo": ("Sésamo", "alergia al sésamo", {"sesamo"}),
}
INTOLERANCES = {
    "lactosa": ("Lactosa", "intolerancia a la lactosa", {"lactosa"}),
    "gluten": ("Gluten (sin ser celíaco)", "sensibilidad al gluten", {"gluten"}),
    "legumbres": ("Legumbres (gases, hinchazón)", "molestia con las legumbres", {"legumbre"}),
    "cruciferas": ("Brócoli, coliflor, repollo", "molestia con el brócoli y similares", {"crucifera"}),
}
CONDITIONS = {
    "diabetes": "Diabetes o prediabetes",
    "hipertension": "Presión alta",
    "colesterol": "Colesterol alto",
    "renal": "Enfermedad renal",
    "embarazo": "Embarazo o lactancia",
}
HEALTH_TIPS = {
    "diabetes": "Repartí los carbohidratos en todas las comidas, elegí integrales y llegá a la fibra. "
                "Si usás insulina u otros remedios, no bajes calorías sin hablar con tu médico.",
    "hipertension": "Sal: menos de 5 g por día (una cucharadita), y revisá el sodio de los productos. "
                    "Frutas, verduras y legumbres ayudan a bajar la presión (dieta DASH).",
    "colesterol": "Bajamos el límite de grasas saturadas al 7 %. La avena y las legumbres (fibra soluble) "
                  "ayudan a bajar el LDL.",
    "renal": "Con enfermedad renal no conviene comer mucha proteína: calculamos 0,8 g por kg y sacamos los "
             "suplementos. El potasio y el fósforo los tiene que ajustar tu nefrólogo o nutricionista.",
    "embarazo": "En embarazo o lactancia las necesidades cambian: no aplicamos déficit. Usá esto solo como "
                "referencia y seguí lo que te indique tu médico u obstetra.",
}
ALLERGY_WARNING = ("Leé siempre las etiquetas: muchos productos tienen trazas. Si la alergia es grave, "
                   "consultá con un alergista.")
CELIAC_WARNING = ("Celiaquía: usá solo productos con el logo sin TACC y cuidá la contaminación cruzada "
                  "(tostadora, tabla, aceite de freír).")
LACTOSE_TIP = ("Con intolerancia a la lactosa, el yogur y los quesos duros suelen caer mejor que la leche; "
               "hasta ~12 g de lactosa por toma (un vaso de leche) muchas personas lo toleran.")


def split(text: str | None) -> list[str]:
    return [x for x in (text or "").split(",") if x]


def _norm(text: str) -> str:
    import unicodedata
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


STOPWORDS = {"sin", "con", "de", "del", "la", "el", "los", "las", "y", "o", "me", "cae", "caen", "mal",
             "muy", "no", "gusta", "gustan", "nada", "un", "una", "al", "en", "por", "que"}


def match_foods(text: str) -> set[str]:
    """Busca alimentos de la lista nombrados en el texto libre ("no me gusta el brócoli")."""
    import re
    tokens = {t for t in re.findall(r"[a-zñ]+", _norm(text)) if t not in STOPWORDS and len(t) >= 3}
    found = set()
    for key, f in FOODS.items():
        words = re.findall(r"[a-zñ]+", _norm(f[0]))
        for t in tokens:
            for w in words:
                if w == t or (len(t) >= 4 and len(w) >= 4 and (w.startswith(t) or t.startswith(w))):
                    found.add(key)
    return found


@dataclass
class Restrictions:
    diet: str = "omnivora"
    allergies: frozenset = frozenset()
    intolerances: frozenset = frozenset()
    conditions: frozenset = frozenset()
    avoid: frozenset = frozenset()
    other: str = ""
    blocked: dict = field(default_factory=dict)  # alimento -> motivo

    def ok(self, key: str) -> bool:
        return key not in self.blocked


def restrictions(diet="omnivora", allergies=(), intolerances=(), conditions=(), avoid=(), other="") -> Restrictions:
    r = Restrictions(diet if diet in DIETS else "omnivora", frozenset(allergies), frozenset(intolerances),
                     frozenset(conditions), frozenset(avoid), other or "")
    by_text = match_foods(r.other) if r.other else set()
    for key in FOODS:
        tags = TAGS.get(key, set())
        reason = None
        if key in r.avoid:
            reason = "lo marcaste para evitar"
        elif key in by_text:
            reason = "lo escribiste en «otras cosas»"
        for table, chosen in ((ALLERGIES, r.allergies), (INTOLERANCES, r.intolerances)):
            for k in chosen:
                if not reason and k in table and tags & table[k][2]:
                    reason = f"por tu {table[k][1]}"
        if not reason and tags & DIETS[r.diet][1]:
            reason = f"por tu dieta {r.diet}"
        if not reason and "renal" in r.conditions and FOODS[key][6] == "Suplementos":
            reason = "por tu salud renal"
        if reason:
            r.blocked[key] = reason
    return r


# Cada comida tiene "lugares"; en cada uno va el primer alimento permitido de la lista.
# Rol: protein = se ajusta para llegar a la proteína; flex = se agranda o achica por calorías;
# flexopt = igual que flex pero se saca si hay que comer poco; fixed = cantidad fija.
MEAL_SLOTS = {
    "Desayuno": [
        ("flex", ["avena", "avena_sin_tacc", "pan", "pan_sin_tacc", "batata"]),
        ("flexopt", ["banana", "frutillas", "manzana", "naranja", "pera"]),
        ("fixed", ["leche", "leche_sl", "bebida_soja", "bebida_arroz"]),
        ("protein", ["yogur", "yogur_sl", "yogur_soja", "huevo", "tofu", "proteina_vegetal"]),
    ],
    "Media mañana": [
        ("fixed", ["naranja", "manzana", "frutillas", "pera", "banana"]),
        ("protein", ["yogur", "yogur_sl", "yogur_soja", "huevo", "cottage", "proteina_vegetal"]),
    ],
    "Almuerzo": [
        ("flex", ["arroz", "quinoa", "papa", "fideos", "batata"]),
        ("fixed", ["brocoli", "chauchas", "ensalada", "zapallito"]),
        ("protein", ["pollo", "merluza", "atun", "lentejas", "garbanzos", "tofu", "seitan", "huevo",
                     "proteina_vegetal"]),
    ],
    "Merienda": [
        ("flex", ["pan", "pan_sin_tacc", "avena", "avena_sin_tacc"]),
        ("fixed", ["manzana", "pera", "naranja", "banana", "frutillas"]),
        ("flexopt", ["almendras", "mani", "semillas_zapallo"]),
        ("protein", ["cottage", "yogur", "yogur_sl", "yogur_soja", "huevo", "proteina_vegetal",
                     "semillas_zapallo"]),
    ],
    "Cena": [
        ("flex", ["papa", "batata", "arroz", "quinoa"]),
        ("fixed", ["zanahoria", "ensalada", "zapallito", "chauchas"]),
        ("flexopt", ["palta"]),
        ("protein", ["carne", "salmon", "merluza", "tofu", "seitan", "porotos", "garbanzos", "lentejas",
                     "huevo", "proteina_vegetal"]),
    ],
}
MEALS_BY_COUNT = {
    3: ["Desayuno", "Almuerzo", "Cena"],
    4: ["Desayuno", "Almuerzo", "Merienda", "Cena"],
    5: ["Desayuno", "Media mañana", "Almuerzo", "Merienda", "Cena"],
}
BASE_QTY = {"palta": 0.5}
ANCHOR_MIN = {"pollo": 1, "carne": 1, "merluza": 1, "salmon": 1, "atun": 1, "tofu": 1, "seitan": 1, "huevo": 1,
              "proteina_vegetal": 1, "whey": 1}
ANCHOR_MAX = {"huevo": 4, "cottage": 2, "yogur": 2, "yogur_sl": 2, "yogur_soja": 2, "proteina_vegetal": 1}
SNACK_SLOTS = [["mani", "almendras", "semillas_zapallo"], ["banana", "manzana", "naranja", "pera"]]
POWDERS = ["whey", "proteina_vegetal"]
FIBER_EXTRAS = ["chia", "pera", "naranja", "manzana", "frutillas"]


@dataclass
class Item:
    key: str
    qty: float

    @property
    def food(self):
        return FOODS[self.key]

    @property
    def name(self) -> str:
        return self.food[0]

    @property
    def amount(self) -> str:
        grams, unit = self.food[1], self.food[2]
        if self.key == "huevo":
            n = round(self.qty)
            return f"{n} {'huevo' if n == 1 else 'huevos'}"
        if grams:
            return f"{round(self.qty * grams / 5) * 5} {'ml' if self.key in LIQUIDS else 'g'}"
        return f"{self.qty:g} {unit}"

    kcal = property(lambda self: self.food[3] * self.qty)
    protein = property(lambda self: self.food[4] * self.qty)
    fiber = property(lambda self: self.food[5] * self.qty)


@dataclass
class Meal:
    name: str
    items: list[Item] = field(default_factory=list)
    kcal = property(lambda self: sum(i.kcal for i in self.items))
    protein = property(lambda self: sum(i.protein for i in self.items))
    fiber = property(lambda self: sum(i.fiber for i in self.items))


def _pick(cands: list[str], r: Restrictions, used: set[str]) -> str | None:
    # La proteína en polvo va como mucho una vez por día.
    allowed = [k for k in cands if r.ok(k) and not (k in POWDERS and k in used)]
    fresh = [k for k in allowed if k not in used]
    return (fresh or allowed or [None])[0]


def menu(t: Targets, r: Restrictions, meals_per_day: int = 4) -> tuple[list[Meal], list[str]]:
    """Arma un día de ejemplo respetando las restricciones; devuelve también qué se cambió y por qué."""
    names = MEALS_BY_COUNT.get(meals_per_day, MEALS_BY_COUNT[4])
    notes: dict[str, str] = {}

    def note_swap(first: str, chosen: str | None):
        if first in r.blocked and first not in notes:
            to = f"usamos {_lower(FOODS[chosen][0])}" if chosen else "lo sacamos"
            notes[first] = f"{FOODS[first][0]}: {to}, {r.blocked[first]}."

    flex, snack = 1.0, 0.0
    for _ in range(5):
        meals, used = [], set()
        for name in names:
            items, anchor = [], None
            for role, cands in MEAL_SLOTS[name]:
                key = _pick(cands, r, used)
                note_swap(cands[0], key)
                if key is None:
                    continue
                used.add(key)
                if role == "protein":
                    anchor = key
                elif role == "flexopt" and flex < 0.5:
                    continue
                else:
                    scale = max(flex, 0.5) if role in ("flex", "flexopt") else 1.0
                    items.append(Item(key, BASE_QTY.get(key, 1.0) * scale))
            if anchor:
                need = (t.protein_g / len(names) - sum(i.protein for i in items)) / FOODS[anchor][4]
                step = 1 if anchor == "huevo" else 0.5
                q = round(need / step) * step
                q = max(ANCHOR_MIN.get(anchor, step), min(ANCHOR_MAX.get(anchor, 3), q))
                items.append(Item(anchor, q))
            if items:
                meals.append(Meal(name, items))
        if snack:
            extra = [k for k in (_pick(c, r, set()) for c in SNACK_SLOTS) if k]
            if extra:
                pos = next((n for n, m in enumerate(meals) if m.name == "Merienda"), len(meals) - 1)
                meals.insert(max(pos, 0), Meal("Colación extra", [Item(k, snack) for k in extra]))
        total = sum(m.kcal for m in meals)
        flex_kcal = sum(i.kcal for m in meals for i in m.items
                        if m.name != "Colación extra" and _is_flex(m.name, i.key))
        if flex_kcal:
            wanted = (t.kcal - (total - flex_kcal)) / (flex_kcal / max(flex, 0.5))
            flex = min(2.0, max(0.25, round(wanted * 4) / 4))
        if flex == 2.0:  # ni agrandando porciones se llega: se suma una colación
            gap = t.kcal - total
            snack_kcal = sum(FOODS[k][3] for k in (_pick(c, r, set()) for c in SNACK_SLOTS) if k)
            if snack_kcal:
                snack = min(2.0, max(0.0, snack + round(gap / snack_kcal * 2) / 2))

    if not meals:
        return meals, list(notes.values())
    used = {i.key for m in meals for i in m.items}
    # Si falta proteína (pasa con muchas restricciones), un scoop de proteína en polvo.
    protein = sum(m.protein for m in meals)
    if protein < 0.9 * t.protein_g:
        powder = _pick(POWDERS, r, set())
        if powder and powder not in used:
            target = next((m for m in meals if m.name == "Merienda"), meals[-1])
            target.items.append(Item(powder, 1))
            notes["_powder"] = (f"Con tus restricciones cuesta llegar a la proteína: sumamos un scoop de "
                                f"{_lower(FOODS[powder][0])} en {target.name.lower()}.")
    fiber = sum(m.fiber for m in meals)
    for key in FIBER_EXTRAS:
        if fiber >= t.fiber_g:
            break
        if r.ok(key) and key not in used:
            (meals[0] if key == "chia" else meals[-1 if len(meals) < 3 else -2]).items.append(Item(key, 1))
            used.add(key)
            fiber += FOODS[key][5]
    return meals, list(notes.values())


def _lower(name: str) -> str:
    return name[0].lower() + name[1:]


def _is_flex(meal: str, key: str) -> bool:
    return any(role in ("flex", "flexopt") and key in cands for role, cands in MEAL_SLOTS.get(meal, []))


def swaps(r: Restrictions) -> tuple[list, list]:
    """Alimentos para cambiar (solo los permitidos), ordenados por proteína y fibra por porción."""
    rows = [(k, *v) for k, v in FOODS.items() if r.ok(k)]
    by_protein = sorted(rows, key=lambda row: -row[5] / max(row[4], 1))[:10]
    by_fiber = sorted([row for row in rows if row[6] > 0], key=lambda row: -row[6])[:8]
    return by_protein, by_fiber


def warnings(r: Restrictions) -> list[str]:
    out = []
    if r.allergies:
        out.append(ALLERGY_WARNING)
    if "gluten" in r.allergies:
        out.append(CELIAC_WARNING)
    if "lactosa" in r.intolerances and "leche" not in r.allergies and r.diet != "vegana":
        out.append(LACTOSE_TIP)
    if r.diet == "vegana":
        out.append("Dieta vegana: tomá vitamina B12 sí o sí (no hay en vegetales) y sumá alimentos "
                   "fortificados con calcio.")
    out += [HEALTH_TIPS[c] for c in CONDITIONS if c in r.conditions]
    return out
