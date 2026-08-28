"""ARKITEKT — pipeline híbrido de dois estágios.

    Estágio 1 — ESTRUTURA   Flux + ControlNet depth, control_weight alto
                            → volumetria correta, material mediano
    Estágio 2 — ACABAMENTO  img2img com strength BAIXO
                            → material, vegetação, céu; não pode mexer na forma

O ponto: o estágio 2 só refina porque a estrutura já foi fixada no estágio 1.
Rodar apenas o estágio 2 sobre o screenshot cru é o que as ferramentas de
prateleira fazem — e é de onde vem a deriva de geometria.

Uso:

    from core.pipeline import Projeto, render

    p = Projeto(nome="garden-praia-torre-a", seed=1974,
                estilo="alto_padrao_litoraneo", iluminacao="golden_hour",
                camera="pedestre", control_weight=0.90, strength=0.75)
    r = render(p, "fachada_leste.png", out_dir="out")
    print(r["aderencia"], r["final"])

    p.salvar("projetos/garden-praia-torre-a.json")   # identidade visual do projeto
"""
from dataclasses import dataclass, asdict, field
from typing import Optional
import json
import pathlib
import time

from . import presets, fidelity
from .engines.fal_engine import FalEngine, RENDER_ENDPOINT


# --------------------------------------------------------------------------
# A identidade visual de um empreendimento.
#
# Guardar isto (e não só a imagem) é o que transforma renders soltos num book
# coerente: qualquer ângulo novo da mesma torre, meses depois, sai igual aos
# anteriores porque seed + preset + pesos são os mesmos.
# --------------------------------------------------------------------------
@dataclass
class Projeto:
    nome: str
    seed: int
    estilo: str
    iluminacao: str
    camera: str
    control_weight: float = 0.90
    strength: float = 0.75
    refino: bool = True
    refino_strength: float = 0.25          # acima de ~0.35 o refino começa a mexer na forma
    prompt_extra: str = ""
    notas: str = ""
    aprovados: list = field(default_factory=list)

    def prompt(self) -> str:
        return presets.build_prompt(self.estilo, self.iluminacao, self.camera, self.prompt_extra)

    def salvar(self, path: str):
        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        return str(p)

    @classmethod
    def carregar(cls, path: str) -> "Projeto":
        return cls(**json.loads(pathlib.Path(path).read_text(encoding="utf-8")))


# --------------------------------------------------------------------------
# Estágio 2: refino sem ControlNet, strength baixo.
# --------------------------------------------------------------------------
def _refinar(eng: FalEngine, image_path: str, prompt: str, strength: float,
             seed: int, dest: pathlib.Path) -> str:
    import urllib.request
    url = eng._upload(image_path)
    res = eng._c().subscribe(RENDER_ENDPOINT, arguments={
        "prompt": prompt + ", refined materials, crisp reflections, natural foliage detail",
        "negative_prompt": presets.NEGATIVE,
        "image_url": url,
        "strength": strength,
        "num_inference_steps": 24,
        "guidance_scale": 3.0,
        "seed": seed,
        "output_format": "png",
    })
    urllib.request.urlretrieve(res["images"][0]["url"], dest)
    return str(dest)


def render(projeto: Projeto, screenshot: str, out_dir: str = "out",
           engine: Optional[FalEngine] = None, tau: int = 4) -> dict:
    """Roda o pipeline completo e devolve o log da geração.

    Mede aderência nos DOIS estágios: se o refino derrubar a aderência, o
    refino_strength está alto demais para este projeto.
    """
    eng = engine or FalEngine()
    ok, why = eng.available()
    if not ok:
        raise RuntimeError(f"motor indisponível: {why}")

    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = pathlib.Path(screenshot).stem
    tag = f"{projeto.nome}__{stem}"
    t0 = time.time()

    # --- estágio 1 -------------------------------------------------------
    r1 = eng.render(screenshot, projeto.prompt(), presets.NEGATIVE,
                    projeto.strength, projeto.control_weight,
                    projeto.seed, f"{tag}__e1", str(out))
    if not r1.ok:
        raise RuntimeError(f"estágio 1 falhou: {r1.error}")

    f1 = fidelity.score(screenshot, r1.image_path, tau=tau)
    log = {
        "projeto": projeto.nome,
        "origem": screenshot,
        "control_map": r1.control_map_path,
        "estrutura": r1.image_path,
        "aderencia_estrutura": f1["aderencia"],
        "custo_usd": r1.cost_usd or 0.0,
    }

    final = r1.image_path
    # --- estágio 2 -------------------------------------------------------
    if projeto.refino:
        dest = out / f"{tag}__e2_refino.png"
        final = _refinar(eng, r1.image_path, projeto.prompt(),
                         projeto.refino_strength, projeto.seed, dest)
        f2 = fidelity.score(screenshot, final, tau=tau)
        log["refino"] = final
        log["aderencia_refino"] = f2["aderencia"]
        log["delta_refino"] = round(f2["aderencia"] - f1["aderencia"], 3)
        log["custo_usd"] = round(log["custo_usd"] + 0.04, 4)

        # guarda-corpo: refino não pode custar geometria
        if log["delta_refino"] < -0.08:
            log["alerta"] = (f"o refino derrubou a aderência em "
                             f"{abs(log['delta_refino']):.2f} — baixe refino_strength "
                             f"(atual {projeto.refino_strength})")

    log["final"] = final
    log["aderencia"] = log.get("aderencia_refino", log["aderencia_estrutura"])
    log["veredito"] = fidelity.classify(log["aderencia"])
    log["segundos"] = round(time.time() - t0, 1)
    log["prompt"] = projeto.prompt()
    log["params"] = {"seed": projeto.seed, "strength": projeto.strength,
                     "control_weight": projeto.control_weight,
                     "refino_strength": projeto.refino_strength if projeto.refino else None}

    (out / f"{tag}.json").write_text(json.dumps(log, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    return log
