"""
Recommendation Service — EduVerse
Gera recomendações personalizadas de conteúdo com explicação XAI.
Cache-Aside com Redis garante SLA de latência < 2s (ADR 0001, ADR 0003).
"""
import json
import os
import time
from typing import Optional

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

app = FastAPI(title="EduVerse — Recommendation Service", version="3.0.0")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "300"))

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------

class Recommendation(BaseModel):
    content_id: str
    title: str
    type: str
    topic: str
    score: float
    explanation: str  # XAI — justificativa da recomendação (RNF Usabilidade)


class RecommendationResponse(BaseModel):
    student_id: str
    recommendations: list[Recommendation]
    source: str  # "cache" | "model"
    latency_ms: float


# ---------------------------------------------------------------------------
# Mock recommendation engine
# Substituir por inferência ML real no Ciclo 4.
# ---------------------------------------------------------------------------

MOCK_CATALOG = {
    "1": [
        Recommendation(
            content_id="c001",
            title="Álgebra Linear para Machine Learning",
            type="video",
            topic="matematica",
            score=0.97,
            explanation="Você acertou menos de 60% nas questões de matrizes — este vídeo cobre exatamente esse gap.",
        ),
        Recommendation(
            content_id="c002",
            title="Exercícios de Derivadas — Nível Intermediário",
            type="exercicio",
            topic="calculo",
            score=0.88,
            explanation="Estudantes com seu histórico de acerto em Cálculo I costumam evoluir com esta lista.",
        ),
        Recommendation(
            content_id="c003",
            title="Introdução a Probabilidade e Estatística",
            type="texto",
            topic="estatistica",
            score=0.81,
            explanation="Baseado no seu progresso em Matemática Discreta, este material complementa sua trilha atual.",
        ),
    ],
}

DEFAULT_POPULAR = [
    Recommendation(
        content_id="p001",
        title="Fundamentos de Programação em Python",
        type="video",
        topic="programacao",
        score=0.75,
        explanation="Recomendação baseada em popularidade geral — perfil personalizado será restaurado em breve.",
    ),
    Recommendation(
        content_id="p002",
        title="Lógica de Programação — Exercícios",
        type="exercicio",
        topic="programacao",
        score=0.70,
        explanation="Recomendação baseada em popularidade geral — perfil personalizado será restaurado em breve.",
    ),
]


def _compute_recommendations(student_id: str) -> list[Recommendation]:
    """Mock: em produção, chama modelo ML (filtragem colaborativa + embeddings)."""
    return MOCK_CATALOG.get(student_id, DEFAULT_POPULAR)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    redis = await get_redis()
    try:
        await redis.ping()
        redis_ok = True
    except Exception:
        redis_ok = False
    return {"status": "ok", "service": "recommendation-service", "redis": redis_ok}


@app.get("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(student_id: str = Query(..., description="ID do estudante")):
    start = time.perf_counter()
    cache_key = f"rec:{student_id}"
    redis = await get_redis()

    # Cache-Aside: tenta Redis primeiro (ADR 0001 — tática de performance)
    cached = await redis.get(cache_key)
    if cached:
        recs = [Recommendation(**r) for r in json.loads(cached)]
        latency = (time.perf_counter() - start) * 1000
        return RecommendationResponse(
            student_id=student_id,
            recommendations=recs,
            source="cache",
            latency_ms=round(latency, 2),
        )

    # Cache MISS: computa via "modelo"
    recs = _compute_recommendations(student_id)

    # Persiste no cache
    await redis.setex(cache_key, CACHE_TTL, json.dumps([r.model_dump() for r in recs]))

    latency = (time.perf_counter() - start) * 1000
    return RecommendationResponse(
        student_id=student_id,
        recommendations=recs,
        source="model",
        latency_ms=round(latency, 2),
    )


@app.get("/popular", response_model=list[Recommendation])
async def get_popular():
    """Endpoint de fallback — retorna recomendações populares (usado pelo Circuit Breaker do Gateway)."""
    return DEFAULT_POPULAR
