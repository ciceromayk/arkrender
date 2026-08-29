"""ARKITEKT — modo ESTUDO / moodboard.

Editores multimodais (Gemini, GPT Image, Grok) reinterpretam a cena a
partir do screenshot — SEM ControlNet, sem trava de geometria. Correto
para: teste de atmosfera, moodboard, concurso, brainstorm rápido.

NUNCA usar pra material aprovado. Esses motores não têm control_weight
nem strength — não existe "quanto pode inventar" pra travar — então não
faz sentido medir aderência aqui (ver README, seção "Regra de ouro do
repo"). O log de saída marca isso explicitamente com
aprovado_para_venda=False; nenhuma função deste módulo calcula aderência,
de propósito, pra não sugerir uma garantia que esses motores não dão.

Uso:

    from core.estudo import gerar_estudo
    from core.engines.estudo.gemini_engine import GeminiEngine

    log = gerar_estudo(GeminiEngine(), "fachada.png",
                        "torre litorânea ao entardecer, luz dourada")
"""
import json
import pathlib
import time
from typing import Optional

from .engines.base import StudyEngine


def gerar_estudo(engine: StudyEngine, screenshot: str, prompt: str,
                  seed: Optional[int] = None, out_dir: str = "out") -> dict:
    ok, why = engine.available()
    if not ok:
        raise RuntimeError(f"motor indisponível: {why}")

    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = pathlib.Path(screenshot).stem
    tag = f"estudo__{engine.name}__{stem}__{int(time.time())}"

    r = engine.gerar(screenshot, prompt, seed, tag, str(out))
    if not r.ok:
        raise RuntimeError(f"{engine.name} falhou: {r.error}")

    log = {
        "modo": "estudo",
        "aprovado_para_venda": False,
        "motivo": ("editor multimodal sem ControlNet — geometria não é travada, "
                   "sirva só de referência de atmosfera/moodboard"),
        "engine": r.engine,
        "origem": screenshot,
        "prompt": prompt,
        "seed": seed,
        "imagem": r.image_path,
        "custo_usd": r.cost_usd or 0.0,
        "segundos": r.seconds,
    }
    (out / f"{tag}.json").write_text(json.dumps(log, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    return log
