#!/usr/bin/env python3
"""ARKITEKT — valida workflows/flux_depth.json contra um ComfyUI real.

Três camadas, da mais barata para a mais cara:

  1. servidor (sempre roda): o ComfyUI responde e tem GPU? Avisa se a VRAM
     livre for pouca pra Flux fp8 (< 14 GB costuma dar OOM).

  2. grafo (sempre roda): bate cada nó do workflow contra /object_info do
     ComfyUI — classe existe (custom node instalado)? input obrigatório
     faltando? input desconhecido? valor fixo (checkpoint/modelo) dentro
     das opções válidas? Não gasta GPU nem carrega modelo nenhum.

  3. renderização de verdade (--render): roda o grafo completo na fixture
     sintética de bench/in/ via core.engines.comfy_engine.ComfyEngine —
     a mesma classe usada pelo app e pelo bench/run.py. Gasta GPU e tempo
     de carregar o modelo na primeira vez.

Rode de DENTRO do Colab (célula nova, depois do servidor subir) — o
egress de alguns ambientes de execução bloqueia domínios como
trycloudflare.com, então rodar de fora costuma falhar por rede, não por
bug no workflow.

    python tools/comfy_check.py                 # só as checagens 1 e 2
    python tools/comfy_check.py --render         # 1, 2 e render real
    python tools/comfy_check.py --url http://127.0.0.1:8188 --render
"""
import argparse
import json
import os
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

WORKFLOW = ROOT / "workflows" / "flux_depth.json"


def checar_servidor(url: str) -> None:
    with urllib.request.urlopen(f"{url}/system_stats", timeout=15) as r:
        stats = json.loads(r.read())

    versao = stats.get("system", {}).get("comfyui_version", "?")
    print(f"servidor no ar — ComfyUI {versao}")

    devices = stats.get("devices") or []
    if not devices:
        print("[AVISO] nenhuma GPU listada — vai rodar em CPU (inviavelmente lento)")
    for d in devices:
        livre = d.get("vram_free", 0) / 1e9
        total = d.get("vram_total", 0) / 1e9
        print(f"  {d.get('name', '?')} — {livre:.1f} de {total:.1f} GB de VRAM livres")
        if total and total < 14:
            print("  [AVISO] menos de 14 GB de VRAM: Flux fp8 pode dar OOM")


def checar_grafo(url: str) -> int:
    wf = json.loads(WORKFLOW.read_text())
    with urllib.request.urlopen(f"{url}/object_info", timeout=180) as r:
        info = json.loads(r.read())

    falhas = 0
    for nid, node in sorted(wf.items(), key=lambda kv: int(kv[0])):
        ct = node["class_type"]
        if ct not in info:
            print(f"[FALHA] nó {nid}: classe '{ct}' não existe neste ComfyUI "
                  f"(custom node não instalado?)")
            falhas += 1
            continue

        spec = info[ct]["input"]
        obrigatorios = set(spec.get("required", {}))
        conhecidos = obrigatorios | set(spec.get("optional", {})) | {"upload"}

        extras = set(node["inputs"]) - conhecidos
        faltando = obrigatorios - set(node["inputs"])
        if extras:
            print(f"[FALHA] nó {nid} ({ct}): inputs não reconhecidos {sorted(extras)}")
            falhas += 1
        if faltando:
            print(f"[FALHA] nó {nid} ({ct}): inputs obrigatórios ausentes {sorted(faltando)}")
            falhas += 1

        for k, v in node["inputs"].items():
            if isinstance(v, list):
                continue  # ligação a outro nó, não um valor fixo
            spec_input = spec.get("required", {}).get(k) or spec.get("optional", {}).get(k)
            if not spec_input:
                continue
            opcoes = spec_input[0]
            if isinstance(opcoes, list) and v not in opcoes:
                amostra = opcoes[:5]
                sufixo = "..." if len(opcoes) > 5 else ""
                print(f"[FALHA] nó {nid} ({ct}): {k}={v!r} não está nas opções "
                      f"válidas (ex.: {amostra}{sufixo})")
                falhas += 1

    print(f"\n{falhas} problema(s) — corrija workflows/flux_depth.json antes de renderizar"
          if falhas else "\ngrafo OK — todos os nós e valores fixos existem neste ComfyUI")
    return falhas


def renderizar_fixture(url: str) -> int:
    os.environ["ARKITEKT_COMFY_URL"] = url
    from core import fidelity, presets
    from core.engines.comfy_engine import ComfyEngine

    fixture = ROOT / "bench" / "in" / "torre_hidden_line.png"
    if not fixture.exists():
        print(f"fixture ausente: {fixture} — rode 'python bench/demo_fixture.py' primeiro")
        return 1

    eng = ComfyEngine()
    ok, why = eng.available()
    if not ok:
        print(f"motor indisponível: {why}")
        return 1

    out_dir = ROOT / "bench" / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt = presets.build_prompt("contemporaneo_br", "nublado", "sem_pessoas")

    print("renderizando a fixture — 1ª execução carrega o modelo, conte alguns minutos...")
    r = eng.render(str(fixture), prompt, presets.NEGATIVE,
                   strength=0.75, control_weight=0.90, seed=1974,
                   config_id="comfy_check", out_dir=str(out_dir))

    if not r.ok:
        print(f"FALHOU: {r.error}")
        return 1

    print(f"OK — {r.seconds}s — imagem salva em {r.image_path}")
    f = fidelity.score(str(fixture), r.image_path)
    print(f"aderência {f['aderencia']:.2f} — {fidelity.classify(f['aderencia'])}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=os.environ.get("ARKITEKT_COMFY_URL", "http://127.0.0.1:8188"))
    ap.add_argument("--render", action="store_true",
                     help="depois da checagem de grafo, renderiza de verdade (gasta GPU)")
    args = ap.parse_args()

    print(f"checando {args.url} ...\n")
    try:
        checar_servidor(args.url)
    except Exception as e:
        sys.exit(f"servidor inacessível: {e}")

    print()
    if checar_grafo(args.url):
        sys.exit(1)

    if args.render:
        sys.exit(renderizar_fixture(args.url))


if __name__ == "__main__":
    main()
