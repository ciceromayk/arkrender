"""ARKITEKT API — configuração.

Chaves de terceiro (fal.ai etc.) moram aqui, no servidor — não mais no
navegador do usuário como no app/streamlit_app.py. É esse deslocamento
que torna a geração "grátis" do ponto de vista do cliente: quem paga a
API é o operador, bancado pela assinatura (Fatia 2).
"""
import pathlib

from pydantic_settings import BaseSettings, SettingsConfigDict

# os imports relativos do pacote api/ (from .config import ...) só funcionam
# rodando `uvicorn api.main:app` a partir da RAIZ do repo — mas isso faz
# env_file=".env" resolver contra a raiz, não contra api/.env. Ancora no
# diretório deste arquivo pra funcionar independente de onde o uvicorn roda.
_ENV_FILE = pathlib.Path(__file__).resolve().parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str

    # CORS — URL do web/ em dev e produção, separadas por vírgula
    CORS_ORIGINS: str = "http://localhost:5173"

    # motor de render (Fatia 1: só fal.ai)
    FAL_KEY: str = ""

    # cota — plano free, valor de teste (mude no Supabase Studio pra ajustar de verdade)
    ARKITEKT_STORAGE_BUCKET: str = "geracoes"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
