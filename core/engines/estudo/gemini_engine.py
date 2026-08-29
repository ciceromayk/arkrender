"""Motor de ESTUDO — Google Gemini (Nano Banana), editor multimodal.

Reinterpreta a cena a partir do screenshot de referência — SEM ControlNet,
sem trava de geometria. Uso correto: moodboard, teste de atmosfera, estudo
preliminar. NUNCA para material aprovado — ver golden rule do README e
core/estudo.py (aprovado_para_venda é sempre False neste módulo).

Requer:  pip install google-genai
Chave :  export GEMINI_API_KEY="..."

Não testado contra a API real nesta sessão (sem chave disponível) — a
forma da resposta (candidates[].content.parts[].inline_data) segue a
documentação pública do SDK google-genai; confira se mudou caso quebre.
"""
import mimetypes
import os
import pathlib
import time

from ..base import StudyEngine, StudyResult

MODEL = os.environ.get("ARKITEKT_GEMINI_MODEL", "gemini-2.5-flash-image")
COST_PER_IMAGE = 0.04  # ordem de grandeza; conferir no console do Google AI


class GeminiEngine(StudyEngine):
    name = "gemini_nano_banana"

    def available(self):
        if not os.environ.get("GEMINI_API_KEY"):
            return False, "GEMINI_API_KEY não definida no ambiente"
        try:
            import google.genai  # noqa: F401
        except ImportError:
            return False, "pacote google-genai não instalado (pip install google-genai)"
        return True, ""

    def gerar(self, image_path, prompt, seed, config_id, out_dir) -> StudyResult:
        t0 = time.time()
        params = dict(model=MODEL, seed=seed)
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
            dados = pathlib.Path(image_path).read_bytes()
            # mimetypes cobre .png/.jpg/.jpeg/.webp corretamente — antes disso
            # todo não-PNG (inclusive .webp) virava image/jpeg por engano.
            mime = mimetypes.guess_type(image_path)[0] or "image/jpeg"

            res = client.models.generate_content(
                model=MODEL,
                contents=[types.Part.from_bytes(data=dados, mime_type=mime), prompt],
            )

            imagens = [
                p.inline_data.data
                for c in res.candidates
                for p in c.content.parts
                if getattr(p, "inline_data", None)
            ]
            if not imagens:
                texto = " ".join(
                    p.text for c in res.candidates for p in c.content.parts
                    if getattr(p, "text", None)
                )
                raise RuntimeError(f"Gemini não devolveu imagem — resposta: {texto[:300] or '(vazia)'}")

            dest = pathlib.Path(out_dir) / f"{self.name}__{config_id}.png"
            dest.write_bytes(imagens[0])

            return StudyResult(self.name, config_id, True, str(dest),
                                round(time.time() - t0, 1), COST_PER_IMAGE, params)
        except Exception as e:
            return StudyResult(self.name, config_id, False, None,
                                round(time.time() - t0, 1), None, params, str(e))
