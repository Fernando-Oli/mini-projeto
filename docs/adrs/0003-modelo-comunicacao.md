# ADR 0003 — Modelo de Comunicação

**Status:** Aceito  
**Data:** 2026-06-05  
**Decisores:** Fernando Luis Rodrigues de Oliveira  
**Contexto relacionado:** [SAD Fase 3](../sad/sad-fase3.md) · Seções 4, 6

---

## Contexto

O EduVerse possui fluxos com **naturezas radicalmente distintas**:

| Fluxo | RF | Expectativa do usuário | Tolerância de latência |
|---|---|---|---|
| Estudante solicita recomendações | RF01 | Resultado imediato (está na frente do computador, aguardando) | < 2 segundos |
| Estudante envia feedback sobre uma aula | RF02 | Confirmação de recebimento; processamento pode ser posterior | Até 30 segundos |
| Sistema analisa risco de evasão | RF03 | Processo batch/background; aluno não espera | Minutos a horas |
| Re-treino do modelo de recomendação | Infra | Processo noturno/semanal | Horas |

Precisamos decidir: **qual protocolo de comunicação usar entre os microsserviços** para cada
um desses fluxos, considerando os trade-offs de acoplamento temporal, tolerância a falhas,
consistência e complexidade operacional.

---

## Decisão

Adotamos um **modelo híbrido**, escolhendo o estilo de comunicação em função da semântica do
fluxo de negócio:

### Comunicação Síncrona (REST/JSON via API Gateway) — caminho do estudante

Utilizada nos fluxos onde o **estudante aguarda uma resposta** em tempo real:

- `GET /recommendations?student_id={id}` — Gateway → Recommendation Service
- `GET /content?topic={topic}` — Gateway → Content Service
- Validação de autenticação — Gateway → Auth/LGPD Service

**Protocolo:** HTTP/REST com JSON. O API Gateway é o único ponto de entrada; serviços internos
não são expostos diretamente. O Circuit Breaker (ADR 0002) protege o caminho síncrono.

**Justificativa:** Quando o estudante aguarda uma resposta, qualquer assincronismo introduz
complexidade desnecessária de polling ou WebSocket. Richardson (2018) recomenda comunicação
síncrona para operações de consulta (query) onde o cliente precisa do resultado imediatamente.

### Comunicação Assíncrona (AMQP via RabbitMQ) — processamento em background

Utilizada em fluxos onde o **processamento pode ocorrer após a confirmação de recebimento**:

- **Feedback:** Gateway publica `feedback.submitted` no broker após confirmar 202 Accepted ao
  estudante. O Feedback/NLP Service consome e processa assincronamente;
- **Evasão:** a cada sessão encerrada, o Recommendation Service publica `session.ended`. O
  Analytics/Evasão Service consome e atualiza o modelo de risco;
- **Re-treino:** eventos acumulados no broker disparam o pipeline de re-treino do modelo de
  recomendação (fora do escopo do Ciclo 3, mas o contrato de evento já está definido).

**Protocolo:** AMQP (Advanced Message Queuing Protocol) via RabbitMQ com filas duráveis.
Mensagens persistidas em disco — não são perdidas em caso de reinicialização do broker.

**Padrão de integração:** Publicação de eventos de domínio seguindo o padrão **Domain Event**
(Hohpe & Woolf, 2003; Fowler, 2014). Cada evento carrega os dados mínimos necessários e um
`correlation_id` para rastreabilidade (ver ADR 0004 — Observabilidade).

---

## Consequências

### Positivas
- **Desacoplamento temporal no caminho assíncrono:** o Feedback/NLP Service pode ser
  reiniciado, atualizado ou escalado independentemente sem afetar o estudante. O broker absorve
  o tráfego durante a indisponibilidade do consumidor — Hohpe & Woolf (2003) chamam isso de
  "store-and-forward", que proporciona resiliência por padrão;
- **Absorção de picos:** o broker nivela cargas de pico — se 10.000 estudantes enviarem
  feedback simultaneamente, o broker enfileira tudo e os workers consomem no seu ritmo,
  sem sobrecarregar o NLP Service;
- **SLA síncrono preservado:** ao separar os caminhos, o desempenho do caminho < 2s não é
  afetado pelo processamento de feedback (que pode ser pesado em NLP);
- **Extensibilidade:** novos consumidores podem ser adicionados ao broker sem alterar o
  produtor — por exemplo, adicionar um serviço de notificação push sem tocar no Feedback Service.

### Negativas / Trade-offs
- **Consistência eventual:** o perfil do estudante (pesos de relevância) só é atualizado após
  o processamento assíncrono do feedback. Existe uma janela de inconsistência — aceitável
  dado que o impacto pedagógico de um único feedback não é imediato;
- **Complexidade do broker:** RabbitMQ adiciona um componente de infra que precisa de gestão
  (cluster HA, monitoramento de filas, Dead Letter Queues para mensagens com erro);
- **Observabilidade distribuída:** rastrear um fluxo que passa por Gateway → broker → worker
  exige correlação de logs por `correlation_id` e ferramentas de distributed tracing (Jaeger,
  Zipkin) — complexidade operacional adicional (ver ADR 0004);
- **Ordenação e idempotência:** em casos de retry, o consumidor pode receber a mesma mensagem
  mais de uma vez. Os workers devem ser **idempotentes** (processar a mesma mensagem múltiplas
  vezes sem efeitos colaterais) — exige atenção no design dos handlers.

---

## Alternativas Consideradas e Rejeitadas

### Alternativa A: 100% Síncrono (REST para todos os fluxos)

**Descrição:** Todos os serviços se comunicam via REST síncrono. O Gateway chama
sequencialmente Recommendation, Feedback e Analytics em cada request.

**Razão para rejeição:** Acoplamento temporal severo — se o Feedback/NLP Service estiver
lento ou indisponível, o estudante fica esperando por processamento que não é relevante para
ele naquele momento. Hohpe e Woolf (2003) descrevem este problema como "temporal coupling":
o remetente fica bloqueado esperando o receptor, mesmo que o receptor seja um processo de
background. Richardson (2018) recomenda explicitamente comunicação assíncrona para operações
de comando (command) que não precisam de resposta imediata. Adicionalmente, cascading failures
ficam mais prováveis: a indisponibilidade do NLP Service derrubaria o fluxo de recomendação.

### Alternativa B: 100% Assíncrono (Pub/Sub para todos os fluxos)

**Descrição:** Até o fluxo de recomendação torna-se assíncrono: o estudante publica um
"evento de solicitação" e aguarda via polling ou WebSocket o resultado.

**Razão para rejeição:** UX ruim para o caso de uso principal. O estudante que clica em
"ver recomendações" tem a expectativa de ver uma resposta imediata — não de fazer polling.
Implementar WebSocket para este caso adiciona complexidade no frontend sem benefício prático.
Fowler (2002) argumenta que a escolha do padrão de integração deve ser guiada pela semântica
do negócio, não pela preferência tecnológica. Para uma **query** com SLA de 2s, REST
síncrono é a escolha natural e mais simples.

### Alternativa C: gRPC para comunicação interna (em vez de REST)

**Descrição:** Usar gRPC (Protocol Buffers) para comunicação síncrona entre os microsserviços
internos, com REST apenas na borda externa (API Gateway para cliente).

**Razão para rejeição:** gRPC oferece menor latência e tipagem forte via Protobuf — vantagens
reais em sistemas com alta frequência de chamadas internas. Porém, para o Ciclo 3 com 3
serviços no scaffold executável, o custo de setup (definição de .proto, geração de stubs,
reflexão para debugging) não se justifica. A adoção de gRPC internamente é identificada como
evolução natural para o Ciclo 4, quando o número de serviços e a frequência de chamadas
internas justificar o investimento (Newman, 2021, Cap. 4).

### Alternativa D: GraphQL como protocolo de API

**Descrição:** Expor uma API GraphQL no Gateway para que o frontend consulte exatamente
os campos que precisa.

**Razão para rejeição:** GraphQL é vantajoso quando o frontend precisa de flexibilidade de
query sobre múltiplos recursos relacionados (ex: um único request que retorna dados do aluno,
recomendações e histórico). No EduVerse, os endpoints são bem definidos e pouco relacionados —
REST com endpoints especializados é suficiente e mais simples de cachear (GET `/recommendations`
é cacheável em HTTP nível; queries GraphQL geralmente não são). Adicionalmente, implementar
um layer GraphQL sobre serviços REST internos adicionaria uma camada de resolvers sem benefício
claro no Ciclo 3.

---

## Referências

- HOHPE, G.; WOOLF, B. *Enterprise Integration Patterns: Designing, Building, and Deploying Messaging Solutions*. Addison-Wesley, 2003.
  Referência canônica para padrões de integração assíncrona: Message Channel, Event Message,
  Dead Letter Channel, Correlation Identifier, Guaranteed Delivery. Base conceitual para toda
  a arquitetura de broker adotada.
- RICHARDSON, C. *Microservices Patterns*. Manning Publications, 2018.
  Cap. 3 — Inter-process communication: quando usar síncrono (REST/gRPC) vs. assíncrono
  (messaging). Cap. 4 — Saga Pattern e consistência eventual em microsserviços.
- FOWLER, M. *What do you mean by "Event-Driven"?* martinfowler.com, 2017.
  Taxonomia de event-driven architecture: Event Notification, Event-Carried State Transfer,
  Event Sourcing e CQRS — fundamentação para a escolha de Domain Events.
- NEWMAN, S. *Building Microservices*. 2. ed. O'Reilly Media, 2021.
  Cap. 4 — Communication styles: motivações para REST vs. gRPC vs. messaging. Cap. 10 —
  Event-driven collaboration e seus trade-offs de consistência.
- BASS, L.; CLEMENTS, P.; KAZMAN, R. *Software Architecture in Practice*. 3. ed. Addison-Wesley, 2012.
  Cap. 8 — Táticas de modificabilidade: desacoplamento temporal como tática para
  modificabilidade e escalabilidade independente de serviços.
