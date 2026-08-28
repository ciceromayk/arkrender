#!/usr/bin/env python3
"""Fixture sintética — valida a métrica de fidelidade sem gastar crédito.

Gera um "screenshot hidden-line" de torre e dois "renders":
  · fiel    — mesma geometria, com textura e ruído  → aderência deve dar ~1.00
  · infiel  — volume deslocado e 4 pavimentos a mais → aderência deve cair p/ ~0.57

Se esses números mudarem, alguém quebrou core/fidelity.py.

    python bench/demo_fixture.py
"""
import pathlib
import sys

import numpy as np
import cv2

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core import fidelity  # noqa: E402

W, H = 1280, 800


def massing(shift: int = 0, floors: int = 12) -> np.ndarray:
    img = np.full((H, W, 3), 245, np.uint8)
    cv2.rectangle(img, (0, 620), (W, H), (232, 232, 232), -1)          # chão
    x0, x1, y0, y1 = 380 + shift, 900 + shift, 90, 620
    cv2.rectangle(img, (x0, y0), (x1, y1), (255, 255, 255), -1)
    cv2.rectangle(img, (x0, y0), (x1, y1), (40, 40, 40), 2)
    lado = np.array([[x1, y0], [x1 + 150, y0 + 70],
                     [x1 + 150, y1 - 40], [x1, y1]], np.int32)
    cv2.fillPoly(img, [lado], (238, 238, 238))
    cv2.polylines(img, [lado], True, (40, 40, 40), 2)

    step = (y1 - y0) / floors
    for i in range(1, floors):
        y = int(y0 + i * step)
        cv2.line(img, (x0, y), (x1, y), (40, 40, 40), 1)
        cv2.line(img, (x1, y), (x1 + 150, int(y + 70 - i * 70 / floors)), (40, 40, 40), 1)
        for j in range(4):
            wx = x0 + 18 + j * 126
            cv2.rectangle(img, (wx, y + 6), (wx + 96, y + int(step) - 6), (120, 120, 120), 1)
    return img


def _texturizar(img: np.ndarray, k: float) -> np.ndarray:
    ruido = np.random.default_rng(7).integers(0, int(80 * k) + 1, img.shape, dtype=np.uint8)
    return cv2.addWeighted(cv2.GaussianBlur(img, (3, 3), 0), 1 - k, ruido, k, 0)


def main() -> int:
    src_dir, out_dir = ROOT / "bench" / "in", ROOT / "bench" / "out"
    src_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    src = src_dir / "torre_hidden_line.png"
    cv2.imwrite(str(src), massing())
    fiel = out_dir / "FAKE__fiel.png"
    infiel = out_dir / "FAKE__infiel.png"
    cv2.imwrite(str(fiel), _texturizar(massing(), 0.15))
    cv2.imwrite(str(infiel), _texturizar(massing(shift=60, floors=16), 0.20))

    esperado = {"fiel": 1.00, "infiel": 0.57}
    falhou = False
    print()
    for nome, path in (("fiel", fiel), ("infiel", infiel)):
        s = fidelity.score(str(src), str(path))
        ok = abs(s["aderencia"] - esperado[nome]) <= 0.08
        falhou |= not ok
        print(f"  {'OK  ' if ok else 'FALHA'} {nome:7s} aderência {s['aderencia']:.2f} "
              f"(esperado ~{esperado[nome]:.2f})  invenção {s['invencao']:.2f}")
        print(f"        → {fidelity.classify(s['aderencia'])}")
    print()
    if falhou:
        print("  A métrica saiu da calibração. Confira core/fidelity.py.\n")
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
