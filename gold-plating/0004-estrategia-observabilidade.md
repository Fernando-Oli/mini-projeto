# ADR 0004 — Estratégia de Observabilidade

**Status:** Aceito  
**Data:** 2026-06-05  
**Decisores:** Fernando Luis Rodrigues de Oliveira  
**Contexto relacionado:** [SAD Fase 3](../docs/sad/sad-fase3.md) · [ADR 0003](../docs/adrs/0003-modelo-comunicacao.md) (correlation_id)

---

## Contexto

O EduVerse, na Fase 3, é composto por múltiplos microsserviços comunicando-se de forma
síncrona e assíncrona. Em produção, problemas difíceis de diagnosticar surgem:

- A latência de recomendação excedeu 2s — mas em qual serviço? Gateway? Recommendation?
  Redis? O modelo ML?
- Um evento de feedback foi publicado no broker, mas o peso de relevância do estudante não
  foi atualizado — onde falhou?
- A taxa de erro aumentou às 14h — qual serviço, qual endpoint, qual version?

Sem observabilidade adequada, depurar um sistema distribuído é virtualmente impossível.
Precisamos definir uma **estratégia de observabilidade** que cubra os três pilares
(Majors, 2022): **logs, métricas e traces**.

---

## Decisão

Adotamos o padrão **Três Pilares da Observabilidade** com ferramentas open-source e
aderentes ao padrão **OpenTelemetry (OTel)**:

### Pilar 1 — Logs estruturados (JSON)

Todos os serviços emitem logs em formato **JSON estruturado** com campos obrigatórios:
- `timestamp` (ISO 8601)
- `level` (INFO / WARNING / ERROR)
- `service` (nome do microsserviço)
- `correlation_id` (propagado do ADR 0003 — liga log ao trace)
- `student_id` (anonimizado por hash para LGPD)
- `message`

Coleta centralizada via **Loki** (Grafana Labs) — scrape dos containers Kubernetes. Para o
ambiente local (Docker Compose), logs são exibidos via `docker compose logs`.

### Pilar 2 — Métricas (RED Method + USE Method)

Cada serviço expõe um endpoint `/metrics` compatível com **Prometheus**. Métricas coletadas:

**RED Method** (Weaving & Wilkes, Google SRE, 2016) — para serviços:
- **R**ate: requisições por segundo por endpoint
- **E**rror rate: porcentagem de respostas 5xx
- **D**uration: histograma de latência (p50, p95, p99)

**USE Method** (Gregg, 2013) — para recursos de infra:
- **U**tilization: CPU/memória por pod
- **S**aturation: fila de conexões Redis, fila do broker
- **E**rrors: falhas de conexão

**SLO Dashboard** (Grafana):
- `recommendation_latency_p99 < 2s` — alerta se violado por > 1 min
- `gateway_error_rate < 1%` — alerta se violado
- `circuit_breaker_state == OPEN` — alerta imediato

### Pilar 3 — Distributed Tracing

**OpenTelemetry SDK** instrumenta cada serviço para propagar o contexto de trace via HTTP
headers (`traceparent`, `tracestate` — W3C Trace Context). O `correlation_id` do ADR 0003
é mapeado para o `trace_id` do OTel.

Backend de armazenamento e visualização: **Jaeger** (ou Tempo da Grafana).

Um trace do fluxo de recomendação mostra:
```
Trace: GET /recommendations?student_id=1
  └─ api-gateway: 5ms (roteamento + CB check)
     └─ recommendation-service: 1.2s
        ├─ redis.get: 2ms (MISS)
        ├─ postgresql.query: 50ms
        ├─ ml.inference: 1100ms  ← gargalo identificado
        └─ redis.setex: 3ms
```

---

## Consequências

### Positivas
- **Diagnóstico preciso:** traces permitem identificar o gargalo exato (ex: inferência ML levou
  1.1s dos 1.2s totais — alvorecer de Majors, 2022);
- **SLO enforcement:** alertas automáticos quando p99 latência viola o SLA de 2s — antes
  que o estudante perceba degradação;
- **Correlação cross-service:** `correlation_id` liga um evento assíncrono do broker ao log
  do Feedback Service que o processou, simplificando debugs no fluxo RF02;
- **Conformidade LGPD:** hash do `student_id` nos logs permite rastreabilidade técnica sem
  expor dados pessoais.

### Negativas / Trade-offs
- **Overhead de instrumentação:** cada trace adiciona ~1–5ms de overhead na serialização de
  contexto — aceitável para o SLA de 2s;
- **Custo de armazenamento:** traces e métricas em alta granularidade consomem armazenamento.
  Mitigação: sampling adaptativo (10% de traces em operação normal, 100% em caso de erro);
- **Complexidade de setup:** adicionar Prometheus, Grafana, Jaeger e Loki ao Kubernetes aumenta
  a carga do time de plataforma. Opção cloud-native (Cloud Monitoring, Datadog, New Relic)
  reduz overhead mas aumenta custo e lock-in.

---

## Alternativas Consideradas e Rejeitadas

### Alternativa A: Logs apenas (sem métricas nem traces)

**Razão para rejeição:** Logs são necessários mas insuficientes. Correlacionar uma degradação
de latência manualmente lendo logs de múltiplos serviços é inviável em escala. Majors (2022)
demonstra que times que dependem apenas de logs têm MTTR (Mean Time To Recovery) 3–5x maior
que times com traces distribuídos.

### Alternativa B: APM SaaS proprietário (Datadog / New Relic)

**Razão para rejeição:** Custo operacional elevado para um projeto acadêmico/startup. Além
disso, os dados de uso dos estudantes (séries temporais de comportamento) trafegando por
um APM externo cria riscos de conformidade com a LGPD. A pilha OpenTelemetry + Grafana OSS
é equivalente em funcionalidade e mantém os dados sob controle.

---

## Referências

- MAJORS, C.; FONG-JONES, L.; MIRANDA, G. *Observability Engineering*. O'Reilly Media, 2022.
  Capítulo 1 — Os três pilares da observabilidade. Referência central para a decisão.
- BEYER, B. et al. *Site Reliability Engineering*. O'Reilly / Google, 2016.
  RED Method (Rate, Errors, Duration) e SLO-based alerting.
- GREGG, B. *Systems Performance: Enterprise and the Cloud*. Prentice Hall, 2013.
  USE Method (Utilization, Saturation, Errors) para recursos de infraestrutura.
- OpenTelemetry Project. *OpenTelemetry Specification*. opentelemetry.io, 2024.
  Padrão open-source de instrumentação de telemetria — base da estratégia de traces.
- W3C. *Trace Context*. w3.org/TR/trace-context, 2021.
  Padrão de propagação de contexto de trace via headers HTTP.
