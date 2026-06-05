# ADR 0002 — Padrões de Resiliência

**Status:** Aceito  
**Data:** 2026-06-05  
**Decisores:** Fernando Luis Rodrigues de Oliveira  
**Contexto relacionado:** [SAD Fase 3](../sad/sad-fase3.md) · Seções 4, 6.1, 9.3

---

## Contexto

O EduVerse tem como requisito de **confiabilidade** atingir CTR > 20% e manter disponibilidade
24/7 durante períodos letivos. O Recommendation Service é o componente mais crítico: é chamado
em todo request de recomendação do estudante e executa inferência ML, que é inerentemente mais
lenta e propensa a timeouts do que operações CRUD convencionais.

Identificamos os seguintes riscos de resiliência:

1. **Falha no Recommendation Service** pode derrubar toda a experiência do estudante se não houver
   proteção no nível do Gateway;
2. **Chamadas síncronas em cascata** entre serviços podem propagar falhas de forma explosiva;
3. **Picos de carga** podem saturar o pool de inferência ML, causando degradação para todos os
   usuários simultaneamente;
4. **Clientes chamando serviços internos diretamente** aumenta acoplamento e superfície de ataque.

Precisamos definir:
- Como **proteger o estudante** de falhas no serviço de recomendação;
- Como **isolar** o impacto de falhas entre serviços;
- Como **retornar algo útil** mesmo quando o serviço de ML está indisponível.

---

## Decisão

Adotamos uma combinação de três padrões de resiliência complementares:

### 1. API Gateway como ponto de entrada único

Um **API Gateway** (Richardson, 2018) centraliza todo o tráfego externo:
- Autentica requests (valida JWT com Auth Service);
- Faz roteamento para os serviços internos;
- Aplica rate limiting por cliente;
- É o único ponto onde os padrões de resiliência abaixo são configurados.

Os serviços internos **não são expostos diretamente** — só respondem ao Gateway. Isso reduz a
superfície de ataque e simplifica a aplicação de políticas de resiliência em um único lugar.

### 2. Circuit Breaker nas chamadas ao Recommendation Service

Implementamos o padrão **Circuit Breaker** (Nygard, 2018) nas chamadas do API Gateway ao
Recommendation Service:

- **Estado Fechado (normal):** chamadas passam normalmente;
- **Estado Aberto (falha detectada):** após N falhas consecutivas (default: 5) ou timeout acima
  do limiar (default: 2s), o circuito abre. O Gateway **não tenta mais chamar** o serviço e
  retorna imediatamente o **fallback** (recomendações populares do cache Redis);
- **Estado Semiaberto (recuperação):** após 30s, o Gateway tenta uma chamada de sonda. Se
  bem-sucedida, o circuito fecha; se falhar, volta ao estado aberto.

**Fallback:** quando o circuito está aberto, o Gateway retorna a lista das 10 recomendações
mais populares da semana, armazenada no Redis com TTL de 24h. O campo `explanation` inclui:
*"Recomendação baseada em popularidade geral — seu perfil personalizado será restaurado em breve."*
Isso implementa **degradação graceful**: o estudante recebe algo útil, a plataforma não cai.

### 3. Bulkhead — isolamento do pool de inferência ML

O **Bulkhead** (Nygard, 2018; analogia com compartimentos estanques de navios) é aplicado no
Recommendation Service:

- O pool de threads/processos de **inferência ML** é separado do pool de threads de outros
  endpoints do mesmo serviço (ex: `/health`, `/popular`);
- Se o pool de inferência ML ficar saturado, apenas as requisições de recomendação são
  afetadas — o healthcheck e os endpoints de fallback continuam respondendo;
- No Kubernetes: o Recommendation Service tem `ResourceRequota` configurado, impedindo que
  a inferência ML consuma toda a CPU do nó e impacte outros serviços.

---

## Consequências

### Positivas
- **Falha isolada:** uma instância do Recommendation Service com problema não derruba o
  fluxo do estudante — o Circuit Breaker garante degradação graceful em < 500ms;
- **Proteção contra retry storm:** sem Circuit Breaker, clientes que reenviassem requests
  fariam o serviço instável mais lento ainda. O breaker elimina esse padrão destrutivo;
- **SLA preservado no fallback:** mesmo com recomendações populares (não personalizadas),
  o estudante continua com uma experiência funcional — mantendo o compromisso de disponibilidade;
- **Ponto único de controle:** políticas de resiliência, rate limiting e autenticação
  centralizadas no Gateway facilitam auditoria e ajuste sem alterar serviços downstream.

### Negativas / Trade-offs
- **Latência incremental do Gateway:** toda chamada passa pelo Gateway, adicionando ~5–20ms.
  Aceitável dado que o SLA de 2s para recomendação tem margem suficiente;
- **Gateway como possível SPOF:** se o próprio Gateway falhar, nenhum serviço é acessível.
  Mitigação: Gateway com 2+ réplicas atrás de Load Balancer cloud (camada de HA do PaaS);
- **Qualidade reduzida no fallback:** recomendações populares são menos precisas que as
  personalizadas. Impacto aceitável dado que o fallback é temporário e a plataforma comunica
  ao usuário que está em modo degradado;
- **Complexidade de configuração:** parâmetros do Circuit Breaker (threshold de falhas, timeout,
  janela de reset) precisam de ajuste fino baseado em dados de produção reais.

---

## Alternativas Consideradas e Rejeitadas

### Alternativa A: Clientes chamando serviços internos diretamente (sem Gateway)

**Descrição:** O frontend e parceiros integram diretamente com cada microsserviço.

**Razão para rejeição:** Acoplamento severo — qualquer mudança de porta, URL ou contrato de um
serviço quebra todos os clientes. Richardson (2018) aponta que o padrão API Gateway é
precisamente a solução para este problema em arquiteturas de microsserviços. Além disso, sem
Gateway é impossível aplicar Circuit Breaker, rate limiting e autenticação de forma consistente.

### Alternativa B: Retry com backoff exponencial sem Circuit Breaker

**Descrição:** Em vez de abrir o circuito, retentar a chamada com espera crescente entre
tentativas (1s, 2s, 4s, 8s...).

**Razão para rejeição:** O problema do "retry storm": se o Recommendation Service está lento
(não totalmente fora do ar), retries multiplicam a carga sobre ele em exatamente o momento
errado. Nygard (2018) descreve este antipadrão explicitamente como *Cascading Failures* —
um serviço marginalmente lento derruba toda a malha de serviços. O Circuit Breaker evita
este cenário ao parar de tentar quando o serviço está claramente em falha.

### Alternativa C: Sem fallback (retornar erro 503)

**Descrição:** Quando o serviço de recomendação falha, retornar erro 503 ao estudante.

**Razão para rejeição:** Viola o requisito de confiabilidade (CTR > 20%) e de disponibilidade.
Um estudante que recebe um erro no momento em que quer estudar provavelmente abandona a sessão,
impactando diretamente retenção e evasão — os dois problemas centrais do sistema. A degradação
graceful (Nygard, 2018) é superior ao fail-fast visível para o usuário final.

### Alternativa D: Service Mesh (Istio / Linkerd) em vez de Circuit Breaker no Gateway

**Descrição:** Delegar Circuit Breaker, retry e observabilidade a um service mesh na camada
de infraestrutura.

**Razão para rejeição:** Service mesh aumenta drasticamente a complexidade operacional (sidecar
proxy em cada pod, configuração de mTLS, políticas de tráfego). Para o estágio atual do projeto,
aplicar Circuit Breaker no nível do Gateway (na aplicação) é suficiente, mais transparente e mais
fácil de debugar. O service mesh é uma evolução natural para o Ciclo 4, quando a malha de serviços
for maior.

---

## Referências

- NYGARD, M. T. *Release It! Design and Deploy Production-Ready Software*. 2. ed. Pragmatic Bookshelf, 2018.
  Capítulos 5 e 6 — definição dos padrões Circuit Breaker, Bulkhead, Fail Fast, Timeouts e Cascading Failures.
  Esta é a referência canônica para os padrões de resiliência adotados.
- RICHARDSON, C. *Microservices Patterns*. Manning Publications, 2018.
  Padrão API Gateway (Cap. 8) e Self-registration / Service discovery.
- FOWLER, M. *CircuitBreaker*. martinfowler.com, 2014.
  Artigo seminal que popularizou o padrão no contexto de microsserviços.
- BASS, L.; CLEMENTS, P.; KAZMAN, R. *Software Architecture in Practice*. 3. ed. Addison-Wesley, 2012.
  Cap. 5 — táticas de disponibilidade: detecção de falhas, recuperação e prevenção.
- NEWMAN, S. *Building Microservices*. 2. ed. O'Reilly Media, 2021.
  Cap. 12 — Resiliência: Circuit Breaker, Bulkhead e degradação graceful em microsserviços.
