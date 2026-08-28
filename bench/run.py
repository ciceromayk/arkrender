#!/usr/bin/env python3
"""ARKITEKT — benchmark de motores de renderização arquitetônica.

Roda a MESMA imagem de entrada pela mesma matriz de configurações em todos os
motores disponíveis, mede fidelidade geométrica, tempo e custo, e gera uma
grade comparativa em HTML.

    export FAL_KEY="..."                  # rota principal
    export REPLICATE_API_TOKEN="..."      # opcional
    export ARKITEKT_COMFY_URL="http://..."# opcional

    python bench/run.py --in in/ --out out/
    python bench/run.py --in in/fachada.png --engines fal --limit 3

Sem chave nenhuma o script não falha: lista o que está indisponível e por quê.
"""
import argparse
import json
import pathlib
import sys
import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from core import presets, fidelity
from core.engines.fal_engine import FalEngine
from core.engines.replicate_engine import ReplicateEngine
from core.engines.comfy_engine import ComfyEngine
import report

SEED = 20260828  # fixa: só assim as configurações são comparáveis entre si

REGISTRY = {
    "fal": FalEngine,
    "replicate": ReplicateEngine,
    "comfy": ComfyEngine,
}


def collect_inputs(path: pathlib.Path) -> list[pathlib.Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    exts = {".png", ".jpg", ".jpeg", ".webp"}
    return sorted(p for p in path.iterdir() if p.suffix.lower() in exts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="in", help="imagem ou pasta de screenshots 3D")
    ap.add_argument("--out", dest="out", default="out")
    ap.add_argument("--engines", default="fal,replicate,comfy")
    ap.add_argument("--limit", type=int, default=0, help="usar só as N primeiras configurações")
    ap.add_argument("--tau", type=int, default=4, help="tolerância em px da métrica de fidelidade")
    args = ap.parse_args()

    inp = pathlib.Path(args.inp)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    images = collect_inputs(inp)
    if not images:
        sys.exit(f"nenhuma imagem em {inp} — coloque os screenshots do SketchUp/Revit lá")

    matriz = presets.MATRIZ[: args.limit] if args.limit else presets.MATRIZ

    engines, skipped = [], []
    for key in args.engines.split(","):
        key = key.strip()
        if key not in REGISTRY:
            continue
        eng = REGISTRY[key]()
        ok, why = eng.available()
        (engines if ok else skipped).append(eng if ok else (eng.name, why))

    print(f"\n  ARKITEKT bench — {len(images)} imagem(ns) × {len(matriz)} config × "
          f"{len(engines)} motor(es) = {len(images)*len(matriz)*len(engines)} render(s)\n")
    for name, why in skipped:
        print(f"  [indisponível] {name}: {why}")
    if not engines:
        print("\n  Nenhum motor disponível. Defina ao menos FAL_KEY e rode de novo.\n")
        sys.exit(1)
    print()

    results = []
    for img in images:
        for cfg_id, strength, cw, (estilo, luz, cam) in matriz:
            prompt = presets.build_prompt(estilo, luz, cam)
            for eng in engines:
                tag = f"{img.stem}__{cfg_id}"
                print(f"  → {eng.name:32s} {tag}", flush=True)
                r = eng.render(str(img), prompt, presets.NEGATIVE,
                               strength, cw, SEED, tag, str(out))
                rec = r.to_dict()
                rec["source"] = str(img)
                rec["preset"] = {"estilo": estilo, "iluminacao": luz, "camera": cam}
                rec["prompt"] = prompt

                if r.ok and r.image_path:
                    try:
                        f = fidelity.score(str(img), r.image_path, tau=args.tau)
                        rec["fidelidade"] = f
                        rec["veredito"] = fidelity.classify(f["aderencia"])
                        print(f"     aderência {f['aderencia']:.2f}  "
                              f"invenção {f['invencao']:.2f}  "
                              f"{r.seconds}s  ${r.cost_usd}")
                    except Exception as e:
                        rec["fidelidade_erro"] = str(e)
                else:
                    print(f"     FALHOU: {r.error}")
                results.append(rec)

    meta = {
        "gerado_em": datetime.datetime.now().isoformat(timespec="seconds"),
        "seed": SEED,
        "tau": args.tau,
        "indisponiveis": [{"motor": n, "motivo": w} for n, w in skipped],
        "resultados": results,
    }
    (out / "resultados.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    html = report.build(meta, out)
    print(f"\n  ✓ {out/'resultados.json'}\n  ✓ {html}\n")


if __name__ == "__main__":
    main()
