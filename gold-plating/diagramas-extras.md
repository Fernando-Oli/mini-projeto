# Diagramas Arquiteturais Extras — EduVerse (Fase 3)

Estes diagramas complementam o C4 de Containers do README com níveis de detalhe adicionais.

---

## 1. C4 — Nível 3: Componentes do Recommendation Service

```mermaid
C4Component
    title Componentes do Recommendation Service

    Container_Boundary(rec, "Recommendation Service") {
        Component(api, "Recommendations API", "FastAPI Router", "Recebe requisições HTTP; aplica validação Pydantic; orquestra o fluxo de recomendação")
        Component(cache_mgr, "Cache Manager", "redis.asyncio", "Implementa o padrão Cache-Aside; lê e escreve no Redis com TTL configurável")
        Component(engine, "Recommendation Engine", "Python (mock → scikit-learn)", "Filtragem colaborativa + embeddings de conteúdo; gera lista ranqueada")
        Component(xai, "XAI Explainer", "Python", "Gera explicações em linguagem natural para cada recomendação retornada")
        Component(event_pub, "Event Publisher", "aio-pika (AMQP)", "Publica evento 'interaction.created' no RabbitMQ após cada recomendação servida")
        ComponentDb(redis_db, "Redis Cache", "Redis 7", "Cache externo — TTL padrão 5 min")
        ComponentDb(pg_db, "PostgreSQL", "PostgreSQL 16", "Histórico de interações e modelo de preferências")
    }

    Rel(api, cache_mgr, "verifica cache")
    Rel(cache_mgr, redis_db, "GET / SETEX", "Redis Protocol")
    Rel(api, engine, "computa recomendações (cache MISS)")
    Rel(engine, pg_db, "lê histórico do aluno", "SQL")
    Rel(engine, xai, "gera explicações")
    Rel(api, event_pub, "publica evento")
    Rel(cache_mgr, redis_db, "armazena resultado")
```

---

## 2. Diagrama de Deployment — Topologia Cloud (Kubernetes)

```mermaid
graph TB
    subgraph internet["Internet"]
        student["Estudante (Browser/App)"]
    end

    subgraph cloud["Cloud Provider (GKE / EKS / AKS)"]
        lb["Load Balancer\n(Cloud-managed)"]

        subgraph k8s["Kubernetes Cluster"]
            subgraph ingress_ns["Namespace: ingress"]
                ingress["Ingress Controller\n(nginx)"]
            end

            subgraph app_ns["Namespace: eduverse"]
                gw["api-gateway\nDeployment\n2 réplicas mínimo"]
                rec["recommendation-service\nDeployment + HPA\n2–10 réplicas"]
                cnt["content-service\nDeployment + HPA\n2–6 réplicas"]
                auth["auth-service\nDeployment\n2 réplicas"]
                fbk["feedback-service\nStatefulSet\n2 workers"]
                anl["analytics-service\nStatefulSet\n2 workers"]
            end

            subgraph data_ns["Namespace: data"]
                redis_svc["Redis\n(Managed/Cloud)"]
                pg_rec["PostgreSQL\nrec-db\n(Cloud SQL)"]
                pg_cnt["PostgreSQL\ncontent-db\n(Cloud SQL)"]
                mq["RabbitMQ Cluster\n3 nós (HA)"]
            end
        end
    end

    subgraph external["Sistemas Externos"]
        lms["LMS Acadêmico"]
        content_repo["Repositório de Conteúdo"]
    end

    student --> lb --> ingress --> gw
    gw --> rec & cnt & auth
    rec --> redis_svc & pg_rec & mq
    cnt --> pg_cnt & lms & content_repo
    mq --> fbk & anl
```

---

## 3. Diagrama de Sequência — Fluxo Síncrono de Recomendação (RF01)

```mermaid
sequenceDiagram
    actor Student as Estudante
    participant GW as API Gateway
    participant CB as Circuit Breaker
    participant Redis as Redis Cache
    participant Rec as Recommendation Service
    participant DB as PostgreSQL

    Student->>GW: GET /recommendations?student_id=1
    GW->>CB: allow_request()?
    CB-->>GW: CLOSED (sim)

    GW->>Rec: GET /recommendations?student_id=1
    Rec->>Redis: GET rec:1
    alt Cache HIT
        Redis-->>Rec: dados cacheados
        Rec-->>GW: 200 OK (source: "cache", ~200ms)
    else Cache MISS
        Redis-->>Rec: nil
        Rec->>DB: SELECT histórico, preferências WHERE student_id=1
        DB-->>Rec: dados do aluno
        Note over Rec: Executa filtragem colaborativa<br/>+ gera explicações XAI
        Rec->>Redis: SETEX rec:1 300 [recomendações]
        Rec-->>GW: 200 OK (source: "model", ~1.5s)
    end

    GW->>CB: record_success()
    GW-->>Student: 200 OK (lista ranqueada + explicações XAI)
```

---

## 4. Diagrama de Sequência — Fluxo Assíncrono de Feedback (RF02)

```mermaid
sequenceDiagram
    actor Student as Estudante
    participant GW as API Gateway
    participant Broker as RabbitMQ
    participant NLP as Feedback/NLP Service
    participant DB_Rec as DB Recomendação

    Student->>GW: POST /feedback {student_id, content_id, text}
    GW->>Broker: publish("feedback.submitted", {student_id, content_id, text, correlation_id})
    GW-->>Student: 202 Accepted (processamento assíncrono)

    Note over Broker,NLP: Processamento em background (até 30s)

    Broker->>NLP: deliver("feedback.submitted")
    NLP->>NLP: Análise de sentimento (HuggingFace / BERT)
    Note over NLP: sentiment = "positivo" / "negativo" / "neutro"

    NLP->>DB_Rec: UPDATE relevance_weights SET weight=weight+delta<br/>WHERE student_id=X AND topic=Y
    DB_Rec-->>NLP: OK

    NLP->>Broker: publish("feedback.processed", {correlation_id, sentiment, delta})
    Note over NLP: Confirma processamento (ack)
```

---

## 5. Diagrama de Sequência — Circuit Breaker em Ação (ADR 0002)

```mermaid
sequenceDiagram
    actor Student as Estudante
    participant GW as API Gateway
    participant CB as Circuit Breaker
    participant Rec as Recommendation Service (FALHANDO)
    participant Redis as Redis (Fallback)

    Note over CB: Estado: CLOSED

    Student->>GW: GET /recommendations?student_id=1
    GW->>CB: allow_request()? → CLOSED (sim)
    GW->>Rec: GET /recommendations
    Rec--xGW: Timeout (> 2.5s)
    GW->>CB: record_failure() [1/3]

    Student->>GW: GET /recommendations?student_id=2
    GW->>CB: allow_request()? → CLOSED (sim)
    GW->>Rec: GET /recommendations
    Rec--xGW: Timeout
    GW->>CB: record_failure() [2/3]

    Student->>GW: GET /recommendations?student_id=3
    GW->>Rec: Timeout
    GW->>CB: record_failure() [3/3] → estado: OPEN

    Note over CB: Estado: OPEN (circuito aberto)

    Student->>GW: GET /recommendations?student_id=4
    GW->>CB: allow_request()? → OPEN (não!)
    GW->>Redis: GET popular_fallback
    Redis-->>GW: recomendações populares
    GW-->>Student: 200 OK (source: "fallback") → degradação graceful

    Note over CB: Após 30s → estado: HALF_OPEN

    Student->>GW: GET /recommendations?student_id=5
    GW->>CB: allow_request()? → HALF_OPEN (sonda)
    GW->>Rec: GET /recommendations (Rec voltou ao normal)
    Rec-->>GW: 200 OK
    GW->>CB: record_success() → estado: CLOSED

    Note over CB: Estado: CLOSED — operação normal restaurada
```
