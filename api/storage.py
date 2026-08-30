"""Upload dos arquivos gerados pro Supabase Storage.

Bucket privado, um por usuário (path {user_id}/{geracao_id}/...). Só a
API escreve aqui (client service_role); o dono lê os próprios arquivos
direto via supabase-js no Vue, sem passar pela API de novo — a policy de
Storage em supabase/migrations/0001_init.sql garante isso.
"""
import mimetypes
import pathlib
import re

from .config import settings
from .deps import get_supabase


def safe_filename(name: str, fallback: str = "arquivo") -> str:
    """Nome de arquivo seguro pra usar em Path(tmpdir) / nome — sem
    componentes de diretório, sem caracteres que permitam path traversal
    (../../etc/passwd) ou substituir a base inteira (um filename absoluto
    tipo /etc/cron.d/x faz Path(tmpdir) / nome IGNORAR tmpdir por completo
    — comportamento documentado do próprio pathlib)."""
    base = pathlib.Path(name or "").name  # descarta qualquer componente de diretório
    base = re.sub(r"[^A-Za-z0-9_.-]", "_", base).strip("._")
    return base or fallback


def upload_geracao(user_id: str, geracao_id: str, local_path: str) -> str:
    """Sobe um arquivo local pro bucket e devolve o PATH dentro dele — não
    uma URL. O Vue gera a signed URL do próprio path via supabase-js
    (storage.from('geracoes').createSignedUrl(path, ...)), usando a
    sessão do usuário — a API não precisa gerar/expor URLs assinadas."""
    sb = get_supabase()
    nome = pathlib.Path(local_path).name
    destino = f"{user_id}/{geracao_id}/{nome}"
    content_type = mimetypes.guess_type(local_path)[0] or "application/octet-stream"

    with open(local_path, "rb") as f:
        sb.storage.from_(settings.ARKITEKT_STORAGE_BUCKET).upload(
            destino, f.read(), {"content-type": content_type}
        )
    return destino
