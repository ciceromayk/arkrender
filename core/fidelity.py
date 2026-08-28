"""Medida objetiva de fidelidade geométrica.

O julgamento final é seu olho. Mas "esse ficou mais bonito" não escala para 8
configurações × 2 imagens. Este módulo dá um número comparável.

Método: mapa de bordas (Canny) da origem e do render; para cada borda da origem,
distância até a borda mais próxima do render (chamfer via distance transform).

  ADERENCIA (recall)  = % das arestas do projeto original que sobreviveram
                        → é ESTE o número que importa. Baixo = o modelo apagou
                          ou moveu geometria: pavimento a mais, esquadria trocada.

  INVENCAO (1-precisão)= % das arestas do render que não existem na origem
                        → sempre alto e isso é NORMAL: vegetação, pessoas, céu,
                          reflexo e detalhe de material são arestas novas legítimas.
                          Só serve para comparar configurações entre si, nunca em
                          termos absolutos.

Tolerância τ em pixels: uma aresta deslocada até τ conta como preservada.
"""
import numpy as np
import cv2


def _edges(path_or_arr, size, blur=3, lo=60, hi=160):
    img = cv2.imread(path_or_arr, cv2.IMREAD_GRAYSCALE) if isinstance(path_or_arr, str) else path_or_arr
    if img is None:
        raise FileNotFoundError(path_or_arr)
    img = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
    img = cv2.GaussianBlur(img, (blur, blur), 0)
    return cv2.Canny(img, lo, hi)


def score(source_path: str, render_path: str, tau: int = 4, size=(1024, 1024)) -> dict:
    e_src = _edges(source_path, size)
    e_ren = _edges(render_path, size)

    # distance transform: para cada pixel, distância até a borda mais próxima
    d_to_ren = cv2.distanceTransform((e_ren == 0).astype(np.uint8), cv2.DIST_L2, 3)
    d_to_src = cv2.distanceTransform((e_src == 0).astype(np.uint8), cv2.DIST_L2, 3)

    src_px = e_src > 0
    ren_px = e_ren > 0
    if src_px.sum() == 0 or ren_px.sum() == 0:
        return {"aderencia": 0.0, "invencao": 1.0, "f1": 0.0, "arestas_origem": int(src_px.sum())}

    aderencia = float((d_to_ren[src_px] <= tau).mean())      # recall
    precisao = float((d_to_src[ren_px] <= tau).mean())
    f1 = 0.0 if (aderencia + precisao) == 0 else 2 * aderencia * precisao / (aderencia + precisao)

    return {
        "aderencia": round(aderencia, 3),
        "invencao": round(1 - precisao, 3),
        "f1": round(f1, 3),
        "arestas_origem": int(src_px.sum()),
    }


def classify(aderencia: float) -> str:
    """Faixas calibradas para screenshot de modelo 3D → render."""
    if aderencia >= 0.80:
        return "travado — geometria preservada, seguro para material aprovado"
    if aderencia >= 0.65:
        return "fiel — desvios pequenos, revisar esquadria e n.º de pavimentos"
    if aderencia >= 0.45:
        return "livre — reinterpretou o volume, só para estudo preliminar"
    return "descolado — não corresponde ao projeto"
