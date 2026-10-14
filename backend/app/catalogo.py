"""Catálogo sanitario para pollos de engorde.

Valores de referencia de uso habitual en la avicultura de engorde. La dosis, la vía y los días de carencia
definitivos son los de la etiqueta del producto y los confirma el médico veterinario.
"""

VACUNAS = [
    {"nombre": "Marek (HVT)", "via": "Subcutánea", "dia": 0, "nota": "Se aplica en la incubadora."},
    {"nombre": "Newcastle + Bronquitis (B1 + H120)", "via": "Ocular o spray", "dia": 1, "nota": "Primera dosis en granja."},
    {"nombre": "Newcastle oleosa (inactivada)", "via": "Subcutánea", "dia": 1, "nota": "Protección de larga duración."},
    {"nombre": "Coccidiosis (vacuna viva)", "via": "Spray o agua de bebida", "dia": 1, "nota": "No usar anticoccidiales en el alimento."},
    {"nombre": "Viruela aviar", "via": "Punción alar", "dia": 7, "nota": "Solo en zonas con antecedentes."},
    {"nombre": "Gumboro (cepa intermedia)", "via": "Agua de bebida", "dia": 14, "nota": "Bursitis infecciosa, primera dosis."},
    {"nombre": "Bronquitis infecciosa (H120 refuerzo)", "via": "Agua de bebida o spray", "dia": 14, "nota": "Refuerzo respiratorio."},
    {"nombre": "Newcastle La Sota (refuerzo)", "via": "Agua de bebida", "dia": 18, "nota": "Refuerzo de Newcastle."},
    {"nombre": "Gumboro (intermedia plus)", "via": "Agua de bebida", "dia": 21, "nota": "Segunda dosis en zonas de riesgo."},
]

MEDICAMENTOS = [
    {"nombre": "Enrofloxacina 10 %", "uso": "Infecciones respiratorias y digestivas (E. coli, Mycoplasma)",
     "dosis": ["10 mg/kg", "0,5 ml/L de agua"], "vias": ["Agua de bebida"], "dias": 5, "carencia": 7},
    {"nombre": "Amoxicilina", "uso": "Infecciones bacterianas (E. coli, Clostridium)",
     "dosis": ["15 mg/kg", "20 mg/kg"], "vias": ["Agua de bebida"], "dias": 5, "carencia": 3},
    {"nombre": "Doxiciclina", "uso": "Enfermedad respiratoria crónica (Mycoplasma)",
     "dosis": ["10 mg/kg", "20 mg/kg"], "vias": ["Agua de bebida"], "dias": 5, "carencia": 7},
    {"nombre": "Oxitetraciclina", "uso": "Infecciones respiratorias y entéricas",
     "dosis": ["20 mg/kg", "50 mg/kg"], "vias": ["Agua de bebida", "Alimento"], "dias": 5, "carencia": 7},
    {"nombre": "Tilosina", "uso": "Mycoplasma y enteritis necrótica",
     "dosis": ["75 mg/kg", "0,5 g/L de agua"], "vias": ["Agua de bebida"], "dias": 3, "carencia": 5},
    {"nombre": "Florfenicol", "uso": "Infecciones respiratorias (E. coli, Pasteurella)",
     "dosis": ["20 mg/kg"], "vias": ["Agua de bebida"], "dias": 5, "carencia": 5},
    {"nombre": "Trimetoprima + sulfametoxazol", "uso": "Coriza, cólera aviar e infecciones entéricas",
     "dosis": ["30 mg/kg"], "vias": ["Agua de bebida"], "dias": 5, "carencia": 10},
    {"nombre": "Amprolio", "uso": "Tratamiento de coccidiosis",
     "dosis": ["125 ppm en agua", "250 ppm en agua"], "vias": ["Agua de bebida"], "dias": 5, "carencia": 1},
    {"nombre": "Toltrazuril", "uso": "Coccidiosis clínica",
     "dosis": ["7 mg/kg", "25 mg/L de agua"], "vias": ["Agua de bebida"], "dias": 2, "carencia": 18},
    {"nombre": "Vitaminas AD3E + electrolitos", "uso": "Apoyo en estrés por calor, vacunación o tratamiento",
     "dosis": ["1 ml/L de agua", "0,5 g/L de agua"], "vias": ["Agua de bebida"], "dias": 3, "carencia": 0},
]

_VACUNAS = {v["nombre"]: v for v in VACUNAS}
_MEDICAMENTOS = {m["nombre"]: m for m in MEDICAMENTOS}


def vacuna(nombre: str) -> dict | None:
    return _VACUNAS.get(nombre)


def medicamento(nombre: str) -> dict | None:
    return _MEDICAMENTOS.get(nombre)
