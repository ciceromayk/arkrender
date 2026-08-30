"""Autenticação e client do Supabase.

O JWT é decodificado LOCALMENTE com o JWT secret do projeto (HS256) — sem
round-trip de rede pro Supabase a cada request. Esse secret fica em
Settings → API → JWT Settings no painel do Supabase.
"""
from fastapi import Header, HTTPException
from jose import JWTError, jwt
from supabase import Client, create_client

from .config import settings

_supabase_admin: Client | None = None


def get_supabase() -> Client:
    """Client com a service_role key — ignora RLS. Só a API usa isto,
    nunca o navegador do usuário (a service_role key nunca vai pro Vue)."""
    global _supabase_admin
    if _supabase_admin is None:
        _supabase_admin = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    return _supabase_admin


def get_current_user(authorization: str = Header(default="")) -> str:
    """Extrai e valida o JWT do header Authorization: Bearer <token>.
    Devolve o user_id (sub do token) ou levanta 401."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "cabeçalho Authorization: Bearer <token> ausente")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as e:
        raise HTTPException(401, f"token inválido: {e}") from e

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "token sem 'sub'")
    return user_id
