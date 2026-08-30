"""Cota de geração — sem ledger mutável.

Cada geração bem-sucedida vira uma linha em `geracoes`; "quanto o usuário
já usou" é uma contagem dessas linhas, não um contador que alguém precisa
incrementar/decrementar à mão em algum outro lugar. Elimina uma classe
inteira de bug de concorrência/dessincronia.
"""
import datetime as dt

from fastapi import HTTPException

from .deps import get_supabase


def _period_start(ciclo_inicio: str | None) -> dt.datetime:
    """Fatia 1: sem assinatura Stripe, o período é sempre o mês calendário
    corrente. Fatia 2: profiles.ciclo_inicio (setado pelo webhook do
    Stripe a partir de subscription.current_period_start) manda, quando
    existir."""
    if ciclo_inicio:
        return dt.datetime.fromisoformat(ciclo_inicio)
    agora = dt.datetime.now(dt.timezone.utc)
    return agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def usage_this_cycle(user_id: str) -> tuple[int, int, dt.datetime]:
    """(gerações usadas, cota do plano, início do ciclo) para o usuário."""
    sb = get_supabase()

    perfil = (
        sb.table("profiles")
        .select("plano_id, ciclo_inicio, planos(cota_geracoes_mes)")
        .eq("id", user_id)
        .single()
        .execute()
    )
    if not perfil.data:
        raise HTTPException(404, "perfil não encontrado — faça login de novo")

    cota = perfil.data["planos"]["cota_geracoes_mes"]
    inicio = _period_start(perfil.data.get("ciclo_inicio"))

    contagem = (
        sb.table("geracoes")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .gte("created_at", inicio.isoformat())
        .execute()
    )
    usados = contagem.count or 0
    return usados, cota, inicio


def check_quota(user_id: str) -> None:
    """Levanta HTTP 402 se a cota do ciclo já estourou."""
    usados, cota, _ = usage_this_cycle(user_id)
    if usados >= cota:
        raise HTTPException(
            402,
            f"cota do plano esgotada ({usados}/{cota} gerações neste ciclo) — "
            "aguarde o próximo ciclo ou faça upgrade de plano",
        )
