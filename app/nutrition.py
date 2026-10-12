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


def targets(sex: str, age: int, weight: float, height: float, activity: str, goal: str) -> Targets:
    bmr = 10 * weight + 6.25 * height - 5 * age + (5 if sex == "m" else -161)
    factor = ACTIVITY.get(activity, ACTIVITY["moderada"])[0]
    tdee = bmr * factor
    kcal_factor, g_per_kg, (lo, hi), _ = GOALS.get(goal, GOALS["mantener"])
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
        fat_g=round(fat), sat_fat_max_g=round(0.10 * kcal / 9),
        carbs_g=round(carbs), sugar_max_g=round(0.10 * kcal / 4),
        water_l=2.0 if sex == "m" else 1.6,
    )


# nombre, gramos por porción (o None), unidad, kcal, proteína g, fibra g, apto vegetariano
FOODS = {
    "pollo": ("Pechuga de pollo cocida", 100, "porción", 165, 31, 0, False),
    "carne": ("Carne vacuna magra cocida", 100, "porción", 215, 26, 0, False),
    "salmon": ("Salmón cocido", 100, "porción", 206, 25, 0, False),
    "atun": ("Atún al natural escurrido", 100, "porción", 116, 25, 0, False),
    "huevo": ("Huevo", None, "huevo", 72, 6.3, 0, True),
    "yogur": ("Yogur griego natural descremado", 170, "pote", 100, 17, 0, True),
    "cottage": ("Queso cottage", 100, "porción", 98, 11, 0, True),
    "leche": ("Leche", 250, "vaso", 120, 8, 0, True),
    "tofu": ("Tofu firme", 100, "porción", 144, 17, 2.3, True),
    "lentejas": ("Lentejas cocidas", 198, "taza", 230, 18, 15.6, True),
    "garbanzos": ("Garbanzos cocidos", 164, "taza", 269, 14.5, 12.5, True),
    "porotos": ("Porotos negros cocidos", 172, "taza", 227, 15, 15, True),
    "avena": ("Avena", 40, "porción", 152, 5.3, 4, True),
    "pan": ("Pan integral", 64, "2 rebanadas", 160, 8, 4, True),
    "arroz": ("Arroz integral cocido", 195, "taza", 218, 5, 3.5, True),
    "fideos": ("Fideos integrales cocidos", 140, "taza", 174, 7.5, 6.3, True),
    "papa": ("Papa con cáscara", 173, "mediana", 161, 4.3, 3.8, True),
    "banana": ("Banana", 118, "mediana", 105, 1.3, 3.1, True),
    "manzana": ("Manzana", 182, "mediana", 95, 0.5, 4.4, True),
    "pera": ("Pera", 178, "mediana", 101, 0.6, 5.5, True),
    "frutillas": ("Frutillas", 152, "taza", 49, 1, 3, True),
    "brocoli": ("Brócoli cocido", 156, "taza", 55, 3.7, 5.1, True),
    "zanahoria": ("Zanahoria", 61, "mediana", 25, 0.6, 1.7, True),
    "palta": ("Palta", 100, "media", 160, 2, 6.7, True),
    "almendras": ("Almendras", 28, "puñado", 164, 6, 3.5, True),
    "mani": ("Maní", 28, "puñado", 161, 7, 2.4, True),
    "chia": ("Semillas de chía", 28, "2 cucharadas", 138, 4.7, 9.8, True),
    "whey": ("Proteína whey (según marca)", 30, "scoop", 120, 24, 0, True),
}

# Comidas del menú: (nombre, alimentos fijos, alimento "ancla" de proteína carnívoro, vegetariano)
MEALS = [
    ("Desayuno", ["avena", "banana", "leche"], "yogur", "yogur"),
    ("Almuerzo", ["arroz", "brocoli"], "pollo", "lentejas"),
    ("Merienda", ["pan", "manzana", "almendras"], "cottage", "cottage"),
    ("Cena", ["papa", "zanahoria", "palta"], "carne", "tofu"),
]
# Alimentos "flexibles": se agrandan o achican juntos para llegar a las calorías.
FLEX = {"avena", "arroz", "pan", "papa", "banana", "almendras", "palta"}
BASE_QTY = {"palta": 0.5}
ANCHOR_MIN = {"pollo": 1, "carne": 1, "salmon": 1, "atun": 1, "tofu": 1, "huevo": 1}
ANCHOR_MAX = {"huevo": 4, "cottage": 2}
SNACK = ["mani", "banana"]
OPTIONAL = {"almendras", "palta", "banana"}  # se sacan si hay que comer menos
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
            return f"{round(self.qty * grams / 5) * 5} g"
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


def _half(x: float) -> float:
    return round(x * 2) / 2


def menu(t: Targets, vegetarian: bool) -> list[Meal]:
    """Arma un día de ejemplo que llega a la proteína y la fibra, y se acerca a las calorías."""
    flex = 1.0
    snack = 0.0
    for _ in range(4):
        meals = []
        for name, fixed, anchor_meat, anchor_veg in MEALS:
            anchor = anchor_veg if vegetarian else anchor_meat
            items = [Item(k, BASE_QTY.get(k, 1.0) * (max(flex, 0.5) if k in FLEX else 1.0))
                     for k in fixed if not (flex < 0.5 and k in OPTIONAL)]
            base_p = sum(i.protein for i in items)
            need = (t.protein_g / len(MEALS) - base_p) / FOODS[anchor][4]
            step = 1 if anchor == "huevo" else 0.5
            q = round(need / step) * step
            q = max(ANCHOR_MIN.get(anchor, step), min(ANCHOR_MAX.get(anchor, 3), q))
            items.append(Item(anchor, q))
            meals.append(Meal(name, items))
        if snack:
            meals.insert(2, Meal("Colación", [Item(k, snack) for k in SNACK]))
        total = sum(m.kcal for m in meals)
        flex_kcal = sum(i.kcal for m in meals for i in m.items if i.key in FLEX and m.name != "Colación")
        if flex_kcal:
            wanted = (t.kcal - (total - flex_kcal)) / (flex_kcal / flex)
            flex = min(2.0, max(0.25, round(wanted * 4) / 4))
        # Si ni agrandando las porciones se llega, se suma una colación.
        if flex == 2.0:
            gap = t.kcal - sum(m.kcal for m in meals)
            snack_kcal = sum(FOODS[k][3] for k in SNACK)
            snack = min(2.0, max(0.0, snack + round(gap / snack_kcal * 2) / 2))
    fiber = sum(m.fiber for m in meals)
    if fiber < t.fiber_g:
        meals[0].items.append(Item("chia", 1))
        fiber += FOODS["chia"][5]
    if fiber < t.fiber_g:
        meals[-2].items.append(Item("pera", 1))
    return meals


def swaps(vegetarian: bool) -> list[tuple]:
    """Alimentos para cambiar, ordenados por proteína y fibra por porción."""
    rows = [(k, *v) for k, v in FOODS.items() if v[6] or not vegetarian]
    by_protein = sorted(rows, key=lambda r: -r[5] / max(r[4], 1))[:10]
    by_fiber = sorted([r for r in rows if r[6] > 0], key=lambda r: -r[6])[:8]
    return by_protein, by_fiber
