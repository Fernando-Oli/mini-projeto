# Gold Plating — EduVerse (Fase 3)

Esta pasta contém artefatos que demonstram excelência técnica além do mínimo exigido.

## Índice de Artefatos

| Artefato | Descrição | Arquivo |
|---|---|---|
| Diagramas Mermaid Extras | C4 Componentes, Deployment, sequências síncrona e assíncrona | [diagramas-extras.md](diagramas-extras.md) |
| ADR 0004 | Estratégia de Observabilidade (logs, traces, métricas) | [0004-estrategia-observabilidade.md](0004-estrategia-observabilidade.md) |
| CI/CD GitHub Actions | Pipeline automatizado: lint + testes por serviço | [../.github/workflows/ci.yml](../.github/workflows/ci.yml) |
| Makefile | Automação de comandos de desenvolvimento | [../Makefile](../Makefile) |
| .env.example | Template de variáveis de ambiente documentado | [../.env.example](../.env.example) |

## Por que isso importa

### Diagramas Extras
Os diagramas C4 de Componentes e Deployment mostram níveis de detalhe além do Container
(exigido no README). O diagrama de sequência deixa explícito como o Circuit Breaker (ADR 0002)
é acionado em tempo de execução.

### ADR 0004 — Observabilidade
Observabilidade é um requisito de qualidade de produção tão importante quanto resiliência.
O ADR 0004 documenta a decisão de adotar a tríade Logs + Métricas + Traces
(OpenTelemetry + Prometheus + Grafana + Jaeger), conectando diretamente ao `correlation_id`
mencionado no ADR 0003.

### CI/CD
O workflow `.github/workflows/ci.yml` executa lint (ruff) e testes (pytest) para cada serviço
em paralelo, bloqueando merges que quebrem os serviços. Isso demonstra maturidade de processo
além da entrega de documentação.
