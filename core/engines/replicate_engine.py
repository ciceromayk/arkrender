"""Motor Replicate — Flux ControlNet (rota de controle/segunda opinião).

Requer:  pip install replicate
Chave :  export REPLICATE_API_TOKEN="..."

O slug do modelo muda com frequência no Replicate; deixe-o configurável em vez
de hardcoded, para não quebrar o benchmark quando a versão for atualizada.
"""
import os
import time
import pathlib
import urllib.request

from .base import Engine, RenderResult

DEFAULT_MODEL = os.environ.get(
    "ARKITEKT_REPLICATE_MODEL",
    "black-forest-labs/flux-depth-dev",
)
COST_PER_IMAGE = 0.03


class ReplicateEngine(Engine):
    name = "replicate_flux_depth"

    def __init__(self, model: str = DEFAULT_MODEL, steps: int = 30, guidance: float = 3.5):
        self.model = model
        self.steps = steps
        self.guidance = guidance

    def available(self):
        if not os.environ.get("REPLICATE_API_TOKEN"):
            return False, "REPLICATE_API_TOKEN não definida no ambiente"
        try:
            import replicate  # noqa: F401
        except ImportError:
            return False, "pacote replicate não instalado (pip install replicate)"
        return True, ""

    def render(self, image_path, prompt, negative, strength, control_weight,
               seed, config_id, out_dir) -> RenderResult:
        import replicate
        t0 = time.time()
        params = dict(model=self.model, strength=strength, control_weight=control_weight,
                      seed=seed, steps=self.steps, guidance=self.guidance)
        try:
            with open(image_path, "rb") as fh:
                out = replicate.run(self.model, input={
                    "prompt": prompt,
                    "control_image": fh,
                    # flux-depth-dev usa guidance para modular aderência ao depth
                    "guidance": self.guidance + (control_weight * 7.0),
                    "num_inference_steps": self.steps,
                    "seed": seed,
                    "output_format": "png",
                })

            url = out[0] if isinstance(out, list) else str(out)
            dest = pathlib.Path(out_dir) / f"{self.name}__{config_id}.png"
            urllib.request.urlretrieve(url, dest)

            return RenderResult(self.name, config_id, True, str(dest), None,
                                round(time.time() - t0, 1), COST_PER_IMAGE, params)
        except Exception as e:
            return RenderResult(self.name, config_id, False, None, None,
                                round(time.time() - t0, 1), None, params, str(e))
