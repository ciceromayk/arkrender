"""Motor ComfyUI self-hosted (RunPod / Vast / máquina local com GPU).

Fala com a API HTTP do ComfyUI: POST /prompt, poll /history/<id>, GET /view.
O workflow em JSON fica em workflows/flux_depth.json — exporte pelo próprio
ComfyUI em "Save (API Format)".

Endereço: export ARKITEKT_COMFY_URL="http://127.0.0.1:8188"

Só faz sentido economicamente acima de ~1.500 imagens/mês. Antes disso, o
custo de manter a GPU e o pipeline supera o preço por uso da fal.
"""
import os
import io
import json
import time
import uuid
import pathlib
import urllib.request

from .base import Engine, RenderResult

COMFY_URL = os.environ.get("ARKITEKT_COMFY_URL", "").rstrip("/")
WORKFLOW = pathlib.Path(__file__).resolve().parents[2] / "workflows" / "flux_depth.json"

# nós do workflow que o runner sobrescreve (ajuste os ids ao seu JSON)
NODE = {
    "positive": "6",
    "negative": "7",
    "load_image": "10",
    "controlnet": "12",
    "sampler": "3",
}


class ComfyEngine(Engine):
    name = "comfyui_flux_depth"

    def available(self):
        if not COMFY_URL:
            return False, "ARKITEKT_COMFY_URL não definida (precisa de uma GPU rodando ComfyUI)"
        if not WORKFLOW.exists():
            return False, f"workflow ausente: {WORKFLOW}"
        try:
            urllib.request.urlopen(f"{COMFY_URL}/system_stats", timeout=5)
        except Exception as e:
            return False, f"ComfyUI inacessível em {COMFY_URL}: {e}"
        return True, ""

    def _post(self, payload: dict) -> str:
        req = urllib.request.Request(
            f"{COMFY_URL}/prompt",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)["prompt_id"]

    def _wait(self, prompt_id: str, timeout: int = 600) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            with urllib.request.urlopen(f"{COMFY_URL}/history/{prompt_id}", timeout=15) as r:
                hist = json.load(r)
            if prompt_id in hist:
                return hist[prompt_id]
            time.sleep(2)
        raise TimeoutError(f"ComfyUI não devolveu resultado em {timeout}s")

    def _upload(self, image_path: str) -> str:
        """multipart sem dependência externa."""
        boundary = uuid.uuid4().hex
        name = pathlib.Path(image_path).name
        body = io.BytesIO()
        body.write(f"--{boundary}\r\n".encode())
        body.write(f'Content-Disposition: form-data; name="image"; filename="{name}"\r\n'.encode())
        body.write(b"Content-Type: image/png\r\n\r\n")
        body.write(pathlib.Path(image_path).read_bytes())
        body.write(f"\r\n--{boundary}--\r\n".encode())

        req = urllib.request.Request(
            f"{COMFY_URL}/upload/image", data=body.getvalue(),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)["name"]

    def render(self, image_path, prompt, negative, strength, control_weight,
               seed, config_id, out_dir) -> RenderResult:
        t0 = time.time()
        params = dict(strength=strength, control_weight=control_weight, seed=seed)
        try:
            wf = json.loads(WORKFLOW.read_text())
            uploaded = self._upload(image_path)

            wf[NODE["load_image"]]["inputs"]["image"] = uploaded
            wf[NODE["positive"]]["inputs"]["text"] = prompt
            wf[NODE["negative"]]["inputs"]["text"] = negative
            wf[NODE["controlnet"]]["inputs"]["strength"] = control_weight
            wf[NODE["sampler"]]["inputs"]["seed"] = seed
            wf[NODE["sampler"]]["inputs"]["denoise"] = strength

            pid = self._post({"prompt": wf, "client_id": f"arkitekt-{uuid.uuid4().hex[:8]}"})
            hist = self._wait(pid)

            img = next(
                i for o in hist["outputs"].values() for i in o.get("images", [])
            )
            q = f"filename={img['filename']}&subfolder={img.get('subfolder','')}&type={img['type']}"
            dest = pathlib.Path(out_dir) / f"{self.name}__{config_id}.png"
            urllib.request.urlretrieve(f"{COMFY_URL}/view?{q}", dest)

            # custo real = tempo de GPU, não por imagem
            gpu_hour = float(os.environ.get("ARKITEKT_GPU_USD_HOUR", "0.60"))
            cost = round((time.time() - t0) / 3600 * gpu_hour, 4)

            return RenderResult(self.name, config_id, True, str(dest), None,
                                round(time.time() - t0, 1), cost, params)
        except Exception as e:
            return RenderResult(self.name, config_id, False, None, None,
                                round(time.time() - t0, 1), None, params, str(e))
