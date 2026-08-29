"""Motor de ESTUDO — xAI Grok Imagine, editor multimodal.

Reinterpreta a cena a partir do PROMPT — SEM ControlNet, sem trava de
geometria. Uso correto: moodboard, teste de atmosfera, estudo preliminar.
NUNCA para material aprovado — ver golden rule do README e core/estudo.py
(aprovado_para_venda é sempre False neste módulo).

Requer:  pip install openai   (a API da xAI é compatível com o SDK da OpenAI)
Chave :  export XAI_API_KEY="..."

IMPORTANTE — diferença dos outros dois motores de estudo: até onde este
código foi escrito, o modelo grok-2-image da xAI é texto→imagem, sem
endpoint de edição com imagem de referência. Isso significa que
`image_path` aqui NÃO é enviado à API — o screenshot não influencia a
geração, só o texto do prompt. Se a xAI abrir um endpoint de edição com
imagem, atualize esta função pra usá-lo; até lá, deixe claro pro usuário
que este motor específico ignora o screenshot.

Não testado contra a API real nesta sessão (sem chave disponível).
"""
import base64
import os
import pathlib
import time

from ..base import StudyEngine, StudyResult

MODEL = os.environ.get("ARKITEKT_GROK_MODEL", "grok-2-image")
COST_PER_IMAGE = 0.07  # ordem de grandeza — conferir no painel da xAI
BASE_URL = "https://api.x.ai/v1"


class GrokEngine(StudyEngine):
    name = "xai_grok_imagine"

    def available(self):
        if not os.environ.get("XAI_API_KEY"):
            return False, "XAI_API_KEY não definida no ambiente"
        try:
            import openai  # noqa: F401
        except ImportError:
            return False, "pacote openai não instalado (pip install openai)"
        return True, ""

    def gerar(self, image_path, prompt, seed, config_id, out_dir) -> StudyResult:
        t0 = time.time()
        params = dict(model=MODEL, seed=seed, screenshot_usado=False)
        try:
            from openai import OpenAI

            client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url=BASE_URL)
            res = client.images.generate(model=MODEL, prompt=prompt, n=1,
                                          response_format="b64_json")

            dest = pathlib.Path(out_dir) / f"{self.name}__{config_id}.png"
            dest.write_bytes(base64.b64decode(res.data[0].b64_json))

            return StudyResult(self.name, config_id, True, str(dest),
                                round(time.time() - t0, 1), COST_PER_IMAGE, params)
        except Exception as e:
            return StudyResult(self.name, config_id, False, None,
                                round(time.time() - t0, 1), None, params, str(e))
