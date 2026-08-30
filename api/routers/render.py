"""POST /render — expõe core.pipeline.render() como serviço multi-usuário.

Rota SÍNCRONA de propósito (`def`, não `async def`): core.pipeline.render()
é bloqueante — chamadas de rede via urllib, sem await em lugar nenhum.
Numa rota async, isso travaria o event loop inteiro do FastAPI durante
toda a renderização (dezenas de segundos), serializando requisições
concorrentes de usuários diferentes. Com `def`, o FastAPI roda a função
inteira numa threadpool automaticamente — resolve sem plumbing extra.
"""
import pathlib
import shutil
import sys
import tempfile
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.engines.fal_engine import FalEngine  # noqa: E402
from core.pipeline import Projeto, render  # noqa: E402

from ..deps import get_current_user, get_supabase
from ..quota import check_quota, usage_this_cycle
from ..schemas import RenderResponse
from ..storage import upload_geracao

router = APIRouter()


@router.post("/render", response_model=RenderResponse)
def render_endpoint(
    screenshot: UploadFile = File(...),
    nome: str = Form(...),
    seed: int = Form(...),
    estilo: str = Form(...),
    iluminacao: str = Form(...),
    camera: str = Form(...),
    control_weight: float = Form(0.90),
    strength: float = Form(0.75),
    refino: bool = Form(True),
    refino_strength: float = Form(0.25),
    prompt_extra: str = Form(""),
    notas: str = Form(""),
    projeto_id: Optional[str] = Form(None),
    user_id: str = Depends(get_current_user),
) -> RenderResponse:
    check_quota(user_id)

    tmpdir = tempfile.mkdtemp(prefix="arkitekt_api_")
    try:
        src_path = pathlib.Path(tmpdir) / (screenshot.filename or "screenshot.png")
        src_path.write_bytes(screenshot.file.read())

        projeto = Projeto(
            nome=nome, seed=seed, estilo=estilo, iluminacao=iluminacao, camera=camera,
            control_weight=control_weight, strength=strength,
            refino=refino, refino_strength=refino_strength,
            prompt_extra=prompt_extra, notas=notas,
        )

        engine = FalEngine()
        try:
            log = render(projeto, str(src_path), out_dir=tmpdir, engine=engine)
        except RuntimeError as e:
            # "motor indisponível" (chave ausente) ou "estágio 1/2 falhou"
            # (erro do fal.ai) — ambos vêm de core/pipeline.py como RuntimeError.
            raise HTTPException(502, str(e)) from e

        geracao_id = str(uuid.uuid4())
        screenshot_path = upload_geracao(user_id, geracao_id, str(src_path))
        imagem_final_path = upload_geracao(user_id, geracao_id, log["final"])
        control_map_path = (
            upload_geracao(user_id, geracao_id, log["control_map"])
            if log.get("control_map") else None
        )

        aprovado = log["aderencia"] >= 0.80

        sb = get_supabase()
        sb.table("geracoes").insert({
            "id": geracao_id,
            "user_id": user_id,
            "projeto_id": projeto_id,
            "modo": "render",
            "engine": engine.name,
            "screenshot_path": screenshot_path,
            "imagem_final_path": imagem_final_path,
            "control_map_path": control_map_path,
            "aderencia": log["aderencia"],
            "veredito": log["veredito"],
            "aprovado_para_venda": aprovado,
            "custo_usd": log["custo_usd"],
            "segundos": log["segundos"],
            "prompt": log["prompt"],
            "params": log["params"],
            "log": log,
        }).execute()

        usados, cota, _ = usage_this_cycle(user_id)

        return RenderResponse(
            geracao_id=geracao_id,
            aderencia=log["aderencia"],
            veredito=log["veredito"],
            aprovado_para_venda=aprovado,
            imagem_final_path=imagem_final_path,
            custo_usd=log["custo_usd"],
            segundos=log["segundos"],
            cota_usada=usados,
            cota_total=cota,
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
