"""ARKITEKT API — Fase B, Fatia 1.

Casca HTTP sobre core/: autentica o usuário (JWT do Supabase), confere
cota, chama core/pipeline.py, grava o resultado. Nenhuma lógica de render
mora aqui — mesmo princípio do app/streamlit_app.py, agora multi-usuário.

    uvicorn api.main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import render as render_router

app = FastAPI(title="ARKITEKT API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(render_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}
