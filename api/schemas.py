"""Modelos Pydantic da API.

RenderRequest espelha o dataclass Projeto de core/pipeline.py — mesmos
campos, mesmos defaults. Vem como multipart/form-data (o screenshot é um
arquivo), então o router recebe os campos individualmente via Form(...)
em vez de parsear este modelo direto do corpo — RenderRequest documenta
o contrato e é usado internamente para montar o dict que vira Projeto.
"""
from typing import Optional

from pydantic import BaseModel


class RenderRequest(BaseModel):
    nome: str
    seed: int
    estilo: str
    iluminacao: str
    camera: str
    control_weight: float = 0.90
    strength: float = 0.75
    refino: bool = True
    refino_strength: float = 0.25
    prompt_extra: str = ""
    notas: str = ""
    projeto_id: Optional[str] = None  # se enviado, associa a geração a um projeto salvo


class RenderResponse(BaseModel):
    geracao_id: str
    aderencia: float
    veredito: str
    aprovado_para_venda: bool
    imagem_final_path: str    # path no bucket Storage — o Vue gera a signed URL
    custo_usd: float
    segundos: float
    cota_usada: int
    cota_total: int
