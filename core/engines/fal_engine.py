"""Motor fal.ai — Flux.1 [dev] + ControlNet Union (depth).

Rota principal do ARKITEKT: o depth map extraído do screenshot 3D é o que
impede o modelo de reinventar a volumetria.

Requer:  pip install fal-client
Chave :  export FAL_KEY="..."
"""
import os
import time
import pathlib
import urllib.request

from .base import Engine, RenderResult

DEPTH_ENDPOINT = "fal-ai/image-preprocessors/depth-anything/v2"
LINEART_ENDPOINT = "fal-ai/image-preprocessors/lineart"
RENDER_ENDPOINT = "fal-ai/flux-general/image-to-image"

# ControlNet Union para Flux — control_mode 2 = depth
CN_UNION_PATH = "InstantX/FLUX.1-dev-Controlnet-Union"
CN_MODE_DEPTH = 2

# ordem de grandeza; conferir no painel da fal
COST_PER_IMAGE = 0.05


class FalEngine(Engine):
    name = "fal_flux_controlnet_depth"

    def __init__(self, steps: int = 30, guidance: float = 3.5):
        self.steps = steps
        self.guidance = guidance
        self._client = None
        self._depth_cache: dict[str, str] = {}

    def available(self):
        if not os.environ.get("FAL_KEY"):
            return False, "FAL_KEY não definida no ambiente"
        try:
            import fal_client  # noqa: F401
        except ImportError:
            return False, "pacote fal-client não instalado (pip install fal-client)"
        return True, ""

    def _c(self):
        if self._client is None:
            import fal_client
            self._client = fal_client
        return self._client

    def _upload(self, path: str) -> str:
        return self._c().upload_file(path)

    def depth_map(self, image_path: str, out_dir: str) -> str:
        """Extrai o mapa de profundidade. Cacheado: é a parte cara de repetir e
        NÃO muda entre as configurações do benchmark."""
        if image_path in self._depth_cache:
            return self._depth_cache[image_path]

        url = self._upload(image_path)
        res = self._c().subscribe(DEPTH_ENDPOINT, arguments={"image_url": url})
        depth_url = res["image"]["url"]

        dest = pathlib.Path(out_dir) / f"{pathlib.Path(image_path).stem}__depth.png"
        urllib.request.urlretrieve(depth_url, dest)
        self._depth_cache[image_path] = depth_url
        self._depth_local = str(dest)
        return depth_url

    def render(self, image_path, prompt, negative, strength, control_weight,
               seed, config_id, out_dir) -> RenderResult:
        t0 = time.time()
        params = dict(strength=strength, control_weight=control_weight, seed=seed,
                      steps=self.steps, guidance=self.guidance)
        try:
            depth_url = self.depth_map(image_path, out_dir)
            src_url = self._upload(image_path)

            res = self._c().subscribe(RENDER_ENDPOINT, arguments={
                "prompt": prompt,
                "negative_prompt": negative,
                "image_url": src_url,
                "strength": strength,
                "num_inference_steps": self.steps,
                "guidance_scale": self.guidance,
                "seed": seed,
                "output_format": "png",
                "controlnet_unions": [{
                    "path": CN_UNION_PATH,
                    "controls": [{
                        "control_image_url": depth_url,
                        "control_mode": CN_MODE_DEPTH,
                        "conditioning_scale": control_weight,
                        "start_percentage": 0.0,
                        # soltar o controle no fim deixa o modelo trabalhar
                        # textura sem mexer mais na forma
                        "end_percentage": 0.85,
                    }],
                }],
            })

            out_url = res["images"][0]["url"]
            dest = pathlib.Path(out_dir) / f"{self.name}__{config_id}.png"
            urllib.request.urlretrieve(out_url, dest)

            return RenderResult(self.name, config_id, True, str(dest),
                                getattr(self, "_depth_local", None),
                                round(time.time() - t0, 1), COST_PER_IMAGE, params)
        except Exception as e:
            return RenderResult(self.name, config_id, False, None, None,
                                round(time.time() - t0, 1), None, params, str(e))
