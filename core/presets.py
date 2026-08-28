"""ARKITEKT — presets de estilo, iluminação e câmera.

Três eixos independentes. O prompt final é a composição dos três + o negativo
comum. Guardados como dados para poderem virar tabela no Supabase depois.
"""

BASE = (
    "professional architectural visualization, photorealistic render, "
    "physically correct materials, accurate proportions, sharp architectural detail, "
    "shot on full frame camera, 35mm lens, two-point perspective, vertical lines perfectly vertical"
)

NEGATIVE = (
    "distorted geometry, extra floors, extra windows, missing windows, warped facade, "
    "curved straight lines, fisheye, illustration, painting, cartoon, cgi plastic look, "
    "oversaturated, watermark, text, signage, blurry, low detail"
)

ESTILO = {
    "contemporaneo_br": "contemporary Brazilian architecture, exposed concrete and white plaster, "
                        "brise-soleil, generous glazing, warm wood accents",
    "alto_padrao_litoraneo": "high-end coastal residential architecture, travertine and white stone, "
                             "large frameless glazing, infinity pool, tropical landscaping",
    "corporativo": "corporate office building, unitized glass curtain wall, aluminum mullions, "
                   "clean podium, granite paving",
    "retrofit": "heritage building retrofit, restored masonry and original openings, "
                "discreet contemporary metal insertions",
    "logistico": "industrial logistics facility, metal cladding, loading docks, wide concrete apron",
    "nordico": "nordic minimalist architecture, muted palette, matte surfaces, restrained detailing",
    "tropical_modernista": "Brazilian modernist architecture, cobogó screens, pilotis, "
                           "lush tropical vegetation, strong shadow play",
    "noturno_comercial": "retail ground floor, illuminated storefronts, warm interior spill light",
}

ILUMINACAO = {
    "manha": "early morning light, low warm sun from the left, long soft shadows, clear sky",
    "meio_dia": "midday sun, high contrast, short hard shadows, deep blue sky",
    "golden_hour": "golden hour, warm raking sunlight, long dramatic shadows, glowing facade",
    "blue_hour": "blue hour, deep blue sky, warm interior lights on, balanced exposure",
    "noturno": "night, facade lighting and interior glow, dark blue sky, wet reflective paving",
    # nublado é o melhor para AVALIAR volumetria: sem sombra dramática escondendo erro
    "nublado": "overcast diffuse daylight, soft even shadows, neutral white balance",
    "pos_chuva": "after rain, wet reflective surfaces, broken clouds, crisp air",
}

CAMERA = {
    "pedestre": "eye level view from the sidewalk, 1.6m camera height",
    "drone_baixo": "low aerial view, 15 meters altitude, slight downward tilt",
    "esquina": "corner view showing two facades, slight upward angle",
    "com_pessoas": "a few people walking, natural scale reference, motion blur on figures",
    "sem_pessoas": "no people, no vehicles, empty clean scene",
    "veg_madura": "mature established landscaping, full grown trees",
    # crítico para incorporadora: mostra o que é entregue, não o que existe em 10 anos
    "veg_entrega": "newly planted landscaping as delivered, young trees, fresh turf",
}


def build_prompt(estilo: str, iluminacao: str, camera: str, extra: str = "") -> str:
    parts = [BASE, ESTILO[estilo], ILUMINACAO[iluminacao], CAMERA[camera]]
    if extra:
        parts.append(extra)
    return ", ".join(parts)


# Matriz do benchmark: mesma imagem, configurações variando UM eixo por vez.
# Objetivo não é "achar a mais bonita" e sim medir quanto cada botão realmente controla.
MATRIZ = [
    # id                      strength  control_weight  preset
    ("cn_forte_fiel",          0.75,     0.90,  ("contemporaneo_br", "nublado",     "sem_pessoas")),
    ("cn_medio",               0.85,     0.65,  ("contemporaneo_br", "nublado",     "sem_pessoas")),
    ("cn_fraco_livre",         0.95,     0.35,  ("contemporaneo_br", "nublado",     "sem_pessoas")),
    ("cn_forte_golden",        0.75,     0.90,  ("contemporaneo_br", "golden_hour", "com_pessoas")),
    ("cn_forte_noturno",       0.75,     0.90,  ("noturno_comercial", "noturno",    "com_pessoas")),
    ("cn_forte_litoraneo",     0.75,     0.90,  ("alto_padrao_litoraneo", "manha",  "veg_entrega")),
    ("cn_forte_drone",         0.75,     0.90,  ("contemporaneo_br", "meio_dia",    "drone_baixo")),
    ("cn_max_travado",         0.65,     1.00,  ("contemporaneo_br", "nublado",     "sem_pessoas")),
]
