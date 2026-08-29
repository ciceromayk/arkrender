"""Motor de ESTUDO — xAI Grok Imagine, editor multimodal.

Reinterpreta a cena a partir do screenshot de referência — SEM ControlNet,
sem trava de geometria. Uso correto: moodboard, teste de atmosfera, estudo
preliminar. NUNCA para material aprovado — ver golden rule do README e
core/estudo.py (aprovado_para_venda é sempre False neste módulo).

Chave :  export XAI_API_KEY="..."

⚠️ FORMATO DE REQUEST NÃO VERIFICADO CONTRA A DOCUMENTAÇÃO REAL. A xAI tem
um endpoint de edição de imagem com referência (POST /v1/images/edits,
modelo grok-imagine-image-2.0, aceita um image_url) — confirmado por busca
na web nesta sessão — mas `docs.x.ai` está bloqueado pelo proxy de egress
deste ambiente de desenvolvimento, então não consegui ler a documentação
oficial pra confirmar o formato exato do corpo da requisição (nome exato
do campo, se aceita data URI base64 ou só URL hospedada, se via SDK da
OpenAI ou só HTTP cru). O código abaixo é a melhor tentativa fundamentada:
POST cru com o screenshot como data URI em `image_url`. Se falhar, o erro
da API vem em StudyResult.error — confira contra
https://docs.x.ai/developers/model-capabilities/images/editing e ajuste.

Não testado contra a API real nesta sessão (sem chave disponível).
"""
import base64
import json
import mimetypes
import os
import pathlib
import time
import urllib.error
import urllib.request

from ..base import StudyEngine, StudyResult

MODEL = os.environ.get("ARKITEKT_GROK_MODEL", "grok-imagine-image-2.0")
COST_PER_IMAGE = 0.07  # ordem de grandeza — conferir no painel da xAI
EDIT_URL = "https://api.x.ai/v1/images/edits"


class GrokEngine(StudyEngine):
    name = "xai_grok_imagine"

    def available(self):
        if not os.environ.get("XAI_API_KEY"):
            return False, "XAI_API_KEY não definida no ambiente"
        return True, ""

    def gerar(self, image_path, prompt, seed, config_id, out_dir) -> StudyResult:
        t0 = time.time()
        params = dict(model=MODEL, seed=seed, screenshot_usado=True)
        try:
            dados = pathlib.Path(image_path).read_bytes()
            mime = mimetypes.guess_type(image_path)[0] or "image/png"
            data_uri = f"data:{mime};base64,{base64.b64encode(dados).decode()}"

            req = urllib.request.Request(
                EDIT_URL,
                data=json.dumps({
                    "model": MODEL,
                    "prompt": prompt,
                    "image_url": data_uri,
                    "response_format": "b64_json",
                }).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {os.environ['XAI_API_KEY']}",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    res = json.loads(r.read())
            except urllib.error.HTTPError as e:
                corpo = e.read().decode(errors="replace")[:800]
                raise RuntimeError(f"xAI recusou a requisição (HTTP {e.code}): {corpo}") from e

            dest = pathlib.Path(out_dir) / f"{self.name}__{config_id}.png"
            dest.write_bytes(base64.b64decode(res["data"][0]["b64_json"]))

            return StudyResult(self.name, config_id, True, str(dest),
                                round(time.time() - t0, 1), COST_PER_IMAGE, params)
        except Exception as e:
            return StudyResult(self.name, config_id, False, None,
                                round(time.time() - t0, 1), None, params, str(e))
