"""ARKITEKT API — configuração.

Chaves de terceiro (fal.ai etc.) moram aqui, no servidor — não mais no
navegador do usuário como no app/streamlit_app.py. É esse deslocamento
que torna a geração "grátis" do ponto de vista do cliente: quem paga a
API é o operador, bancado pela assinatura (Fatia 2).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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
