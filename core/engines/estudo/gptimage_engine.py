"""Motor de ESTUDO — OpenAI GPT Image, editor multimodal.

Reinterpreta a cena a partir do screenshot de referência — SEM ControlNet,
sem trava de geometria. Uso correto: moodboard, teste de atmosfera, estudo
preliminar. NUNCA para material aprovado — ver golden rule do README e
core/estudo.py (aprovado_para_venda é sempre False neste módulo).

Requer:  pip install openai
Chave :  export OPENAI_API_KEY="..."

Não testado contra a API real nesta sessão (sem chave disponível). O
endpoint images.edit da OpenAI não tem parâmetro de seed hoje — ele é
aceito na assinatura por uniformidade com os outros motores de estudo,
mas fica só registrado no log, não enviado à API.
"""
import base64
import os
import pathlib
import time

from ..base import StudyEngine, StudyResult

MODEL = os.environ.get("ARKITEKT_OPENAI_IMAGE_MODEL", "gpt-image-1")
COST_PER_IMAGE = 0.07  # ordem de grandeza, varia com resolução/qualidade — conferir no painel da OpenAI


class GptImageEngine(StudyEngine):
    name = "openai_gpt_image"

    def available(self):
        if not os.environ.get("OPENAI_API_KEY"):
            return False, "OPENAI_API_KEY não definida no ambiente"
        try:
            import openai  # noqa: F401
        except ImportError:
            return False, "pacote openai não instalado (pip install openai)"
        return True, ""

    def gerar(self, image_path, prompt, seed, config_id, out_dir) -> StudyResult:
        t0 = time.time()
        params = dict(model=MODEL, seed=seed)
        try:
            from openai import OpenAI

            client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
            with open(image_path, "rb") as f:
                res = client.images.edit(model=MODEL, image=f, prompt=prompt)

            dest = pathlib.Path(out_dir) / f"{self.name}__{config_id}.png"
            dest.write_bytes(base64.b64decode(res.data[0].b64_json))

            return StudyResult(self.name, config_id, True, str(dest),
                                round(time.time() - t0, 1), COST_PER_IMAGE, params)
        except Exception as e:
            return StudyResult(self.name, config_id, False, None,
                                round(time.time() - t0, 1), None, params, str(e))
