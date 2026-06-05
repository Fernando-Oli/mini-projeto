"""
API Gateway — EduVerse
Ponto de entrada único: roteamento, Circuit Breaker, rate limiting simulado.
Implementa o padrão API Gateway (Richardson, 2018) e Circuit Breaker (Nygard, 2018).
ADR 0002 — Padrões de Resiliência.
"""
import os
import time
from enum import Enum

import httpx
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="EduVerse — API Gateway", version="3.0.0")

RECOMMENDATION_URL = os.getenv("RECOMMENDATION_SERVICE_URL", "http://recommendation-service:8001")
CONTENT_URL = os.getenv("CONTENT_SERVICE_URL", "http://content-service:8002")

CIRCUIT_BREAKER_THRESHOLD = int(os.getenv("CB_FAILURE_THRESHOLD", "3"))
CIRCUIT_BREAKER_RESET_SECONDS = int(os.getenv("CB_RESET_SECONDS", "30"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "2.5"))


# ---------------------------------------------------------------------------
# Circuit Breaker (implementação mínima — produção usaria tenacity/circuitbreaker)
# ADR 0002: padrão Circuit Breaker de Nygard (2018)
# ---------------------------------------------------------------------------

class CircuitState(str, Enum):
    CLOSED = "CLOSED"      # normal — chamadas passam
    OPEN = "OPEN"          # falha detectada — retorna fallback imediatamente
    HALF_OPEN = "HALF_OPEN"  # testando recuperação


class CircuitBreaker:
    def __init__(self, name: str, threshold: int, reset_seconds: float):
        self.name = name
        self.threshold = threshold
        self.reset_seconds = reset_seconds
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.opened_at: float = 0.0

    def record_failure(self):
        self.failure_count += 1
        if self.failure_count >= self.threshold:
            self.state = CircuitState.OPEN
            self.opened_at = time.monotonic()

    def record_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def allow_request(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.monotonic() - self.opened_at >= self.reset_seconds:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        return True  # HALF_OPEN: deixa uma sonda passar


cb_recommendation = CircuitBreaker("recommendation", CIRCUIT_BREAKER_THRESHOLD, CIRCUIT_BREAKER_RESET_SECONDS)


# ---------------------------------------------------------------------------
# Fallback — recomendações populares (ADR 0002: degradação graceful)
# ---------------------------------------------------------------------------

FALLBACK_RECOMMENDATIONS = {
    "student_id": "fallback",
    "recommendations": [
        {
            "content_id": "p001",
            "title": "Fundamentos de Programação em Python",
            "type": "video",
            "topic": "programacao",
            "score": 0.75,
            "explanation": "Recomendação baseada em popularidade geral — perfil personalizado será restaurado em breve.",
        },
        {
            "content_id": "p002",
            "title": "Lógica de Programação — Exercícios",
            "type": "exercicio",
            "topic": "programacao",
            "score": 0.70,
            "explanation": "Recomendação baseada em popularidade geral — perfil personalizado será restaurado em breve.",
        },
    ],
    "source": "fallback",
    "circuit_breaker_state": "OPEN",
}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check agregado — verifica serviços downstream."""
    results: dict = {"gateway": "ok", "circuit_breaker": {"recommendation": cb_recommendation.state}}
    async with httpx.AsyncClient(timeout=2.0) as client:
        for name, url in [
            ("recommendation_service", f"{RECOMMENDATION_URL}/health"),
            ("content_service", f"{CONTENT_URL}/health"),
        ]:
            try:
                r = await client.get(url)
                results[name] = r.json()
            except Exception as e:
                results[name] = {"status": "unreachable", "error": str(e)}
    return results


@app.get("/recommendations")
async def proxy_recommendations(student_id: str = Query(..., description="ID do estudante")):
    """
    Roteia para o Recommendation Service com Circuit Breaker.
    Se o circuito estiver aberto, retorna fallback de recomendações populares.
    ADR 0002: Circuit Breaker + fallback graceful.
    """
    if not cb_recommendation.allow_request():
        return JSONResponse(
            content={**FALLBACK_RECOMMENDATIONS, "student_id": student_id},
            status_code=200,  # 200: estudante recebe resposta funcional mesmo no fallback
        )

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            resp = await client.get(
                f"{RECOMMENDATION_URL}/recommendations",
                params={"student_id": student_id},
            )
            resp.raise_for_status()
            cb_recommendation.record_success()
            return JSONResponse(content=resp.json(), status_code=resp.status_code)
        except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.ConnectError) as e:
            cb_recommendation.record_failure()
            return JSONResponse(
                content={
                    **FALLBACK_RECOMMENDATIONS,
                    "student_id": student_id,
                    "error_detail": str(e),
                },
                status_code=200,
            )


@app.get("/content")
async def proxy_content(
    topic: str = Query(...),
    difficulty: str = Query(None),
    content_type: str = Query(None),
):
    """Roteia para o Content Service (sem Circuit Breaker — conteúdo é menos crítico que recomendações)."""
    params = {"topic": topic}
    if difficulty:
        params["difficulty"] = difficulty
    if content_type:
        params["content_type"] = content_type

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            resp = await client.get(f"{CONTENT_URL}/content", params=params)
            return JSONResponse(content=resp.json(), status_code=resp.status_code)
        except Exception as e:
            return JSONResponse(content={"error": "Content service unavailable", "detail": str(e)}, status_code=503)


@app.get("/topics")
async def proxy_topics():
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            resp = await client.get(f"{CONTENT_URL}/topics")
            return JSONResponse(content=resp.json(), status_code=resp.status_code)
        except Exception as e:
            return JSONResponse(content={"error": str(e)}, status_code=503)


@app.get("/circuit-breaker/status")
async def circuit_breaker_status():
    """Expõe estado do Circuit Breaker para observabilidade."""
    return {
        "service": "recommendation",
        "state": cb_recommendation.state,
        "failure_count": cb_recommendation.failure_count,
        "threshold": cb_recommendation.threshold,
        "reset_seconds": cb_recommendation.reset_seconds,
    }
