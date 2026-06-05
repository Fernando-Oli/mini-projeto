"""
Content Service — EduVerse
Catálogo de materiais didáticos. Integra com LMS e Repositório de Conteúdo externo
via Anti-Corruption Layer (ADR 0001, ADR 0003).
"""
import os
from typing import Optional

from fastapi import FastAPI, Query
from pydantic import BaseModel

app = FastAPI(title="EduVerse — Content Service", version="3.0.0")

LMS_URL = os.getenv("LMS_URL", "http://lms-mock:9001")  # externo — mockado localmente
CONTENT_REPO_URL = os.getenv("CONTENT_REPO_URL", "http://content-repo-mock:9002")


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------

class ContentItem(BaseModel):
    content_id: str
    title: str
    type: str  # "video" | "texto" | "exercicio"
    topic: str
    difficulty: str  # "basico" | "intermediario" | "avancado"
    duration_minutes: Optional[int] = None
    url: str
    tags: list[str]


class ContentResponse(BaseModel):
    topic: str
    items: list[ContentItem]
    total: int


# ---------------------------------------------------------------------------
# Mock catalog (substituir por integração real com LMS/Repositório no Ciclo 4)
# ---------------------------------------------------------------------------

CATALOG: dict[str, list[ContentItem]] = {
    "matematica": [
        ContentItem(
            content_id="c001",
            title="Álgebra Linear para Machine Learning",
            type="video",
            topic="matematica",
            difficulty="intermediario",
            duration_minutes=45,
            url="https://content.eduverse.io/videos/c001",
            tags=["matrizes", "vetores", "transformacoes"],
        ),
        ContentItem(
            content_id="c004",
            title="Multiplicação de Matrizes — Teoria e Prática",
            type="texto",
            topic="matematica",
            difficulty="basico",
            duration_minutes=20,
            url="https://content.eduverse.io/textos/c004",
            tags=["matrizes", "produto-escalar"],
        ),
    ],
    "calculo": [
        ContentItem(
            content_id="c002",
            title="Exercícios de Derivadas — Nível Intermediário",
            type="exercicio",
            topic="calculo",
            difficulty="intermediario",
            duration_minutes=60,
            url="https://content.eduverse.io/exercicios/c002",
            tags=["derivadas", "regra-da-cadeia", "calculo-diferencial"],
        ),
    ],
    "programacao": [
        ContentItem(
            content_id="p001",
            title="Fundamentos de Programação em Python",
            type="video",
            topic="programacao",
            difficulty="basico",
            duration_minutes=30,
            url="https://content.eduverse.io/videos/p001",
            tags=["python", "logica", "iniciante"],
        ),
        ContentItem(
            content_id="p002",
            title="Lógica de Programação — Exercícios",
            type="exercicio",
            topic="programacao",
            difficulty="basico",
            duration_minutes=45,
            url="https://content.eduverse.io/exercicios/p002",
            tags=["logica", "algoritmos", "python"],
        ),
    ],
}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "service": "content-service"}


@app.get("/content", response_model=ContentResponse)
async def get_content(
    topic: str = Query(..., description="Tópico do conteúdo (ex: matematica, calculo, programacao)"),
    difficulty: Optional[str] = Query(None, description="Filtro de dificuldade: basico | intermediario | avancado"),
    content_type: Optional[str] = Query(None, description="Tipo: video | texto | exercicio"),
):
    items = CATALOG.get(topic.lower(), [])

    if difficulty:
        items = [i for i in items if i.difficulty == difficulty]
    if content_type:
        items = [i for i in items if i.type == content_type]

    return ContentResponse(topic=topic, items=items, total=len(items))


@app.get("/content/{content_id}", response_model=ContentItem)
async def get_content_by_id(content_id: str):
    for items in CATALOG.values():
        for item in items:
            if item.content_id == content_id:
                return item
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail=f"Content '{content_id}' not found")


@app.get("/topics")
async def list_topics():
    return {"topics": list(CATALOG.keys())}
