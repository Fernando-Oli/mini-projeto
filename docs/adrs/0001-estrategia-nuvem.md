# ADR 0001 — Estratégia de Nuvem e Escalabilidade

**Status:** Aceito  
**Data:** 2026-06-05  
**Decisores:** Fernando Luis Rodrigues de Oliveira  
**Contexto relacionado:** [SAD Fase 3](../sad/sad-fase3.md) · Seções 4, 7

---

## Contexto

O EduVerse possui um requisito central de **escalabilidade**: suportar milhares de alunos
simultâneos sem degradação (RNF — Ciclo 1). O motor de recomendação com ML é o componente
de maior custo computacional e de maior variação de carga (picos no início do período letivo,
vales nos fins de semana).

Precisamos decidir:
1. **Modelo de serviço cloud** (IaaS, PaaS, SaaS ou Serverless) para hospedar os microsserviços;
2. **Estratégia de escalabilidade** (horizontal vs. vertical) para atender a variação de carga.

A decisão afeta diretamente custo operacional, overhead de gestão de infraestrutura, flexibilidade
para customizar o pipeline de ML e capacidade de atualizar modelos sem downtime.

---

## Decisão

### Modelo de serviço: PaaS (Kubernetes Gerenciado) + Serverless para workers event-driven

Adotamos **PaaS** na forma de um cluster Kubernetes gerenciado pelo provedor cloud
(ex: Google Kubernetes Engine — GKE, Amazon EKS ou Azure AKS) para os serviços síncronos
(API Gateway, Recommendation Service, Content Service, Auth/LGPD Service).

Para os serviços assíncronos orientados a eventos (Feedback/NLP Service, Analytics/Evasão
Service), adotamos **Serverless** (Cloud Run, AWS Lambda ou Azure Container Apps) pois estas
cargas são intermitentes e não justificam instâncias permanentes.

### Estratégia de escalabilidade: Horizontal (scale-out)

O **Recommendation Service** é declarado **stateless**: nenhum estado de sessão é mantido na
memória da instância — o estado vive no Redis (cache) e no PostgreSQL (persistência). Isso
permite que o Horizontal Pod Autoscaler (HPA) do Kubernetes adicione ou remova réplicas
automaticamente com base em CPU/memória ou métricas customizadas (requests/second).

Banco de dados e cache escalam de forma independente, via serviços gerenciados com read replicas.

---

## Consequências

### Positivas
- **Elasticidade real:** HPA escala o Recommendation Service de 2 a N réplicas em resposta a picos,
  sem intervenção manual — atende o RNF de "milhares de alunos simultâneos".
- **Redução de overhead operacional:** Kubernetes gerenciado elimina a necessidade de gerenciar
  control plane, patches de SO e upgrades de cluster (provedor assume esse ônus — Mell & Grance,
  NIST SP 800-145, 2011).
- **Serverless para workers:** custo zero quando não há eventos para processar; escala automática
  até centenas de instâncias em segundos.
- **Portabilidade:** uso de Kubernetes padrão e AMQP (RabbitMQ) minimiza lock-in com provider
  específico.

### Negativas / Trade-offs
- **Custo de cluster:** cluster Kubernetes gerenciado tem custo fixo (nodes mínimos), mesmo em
  carga baixa. Para startups, pode ser substituído por managed container services mais simples
  em estágios iniciais.
- **Cold start serverless:** workers serverless têm latência de cold start (~500ms–2s). Aceitável
  para fluxos assíncronos (feedback, evasão), **inaceitável** para o caminho síncrono do estudante
  — por isso o caminho síncrono fica em PaaS (sempre quente).
- **Curva de aprendizado:** Kubernetes tem complexidade operacional significativa; exige investimento
  em capacitação do time de plataforma.

---

## Alternativas Consideradas e Rejeitadas

### Alternativa A: IaaS Puro (VMs self-managed)

**Descrição:** Provisionar VMs (EC2, Compute Engine, Azure VMs) e gerenciar toda a pilha
(SO, runtime, clustering, balanceamento).

**Razão para rejeição:** Overhead operacional muito alto para uma plataforma educacional com equipe
enxuta. Newman (2021) alerta que microsserviços amplificam a carga operacional — gerenciar VMs
individualmente é insustentável em escala. A escalabilidade precisaria de scripts customizados de
auto-scaling menos confiáveis que o HPA nativo do Kubernetes.

### Alternativa B: SaaS Completo (MLaaS — ex: AWS SageMaker end-to-end)

**Descrição:** Delegar todo o pipeline de ML, serving e infra para um serviço SaaS gerenciado de ML.

**Razão para rejeição:** Perda de controle sobre o modelo de recomendação, que é o diferencial
competitivo central do EduVerse. Vendor lock-in severo: migrar o modelo treinado em SageMaker para
outro provedor é extremamente custoso. Além disso, o requisito de XAI (explicar as recomendações)
exige acesso às entranhas do modelo — dificultado em soluções SaaS caixa-preta.

### Alternativa C: Escalabilidade Vertical (scale-up)

**Descrição:** Usar instâncias maiores (mais CPU/RAM) em vez de adicionar réplicas.

**Razão para rejeição:** Escalabilidade vertical tem teto físico e não oferece tolerância a falhas
(uma única instância grande é um SPOF). Bass, Clements e Kazman (2012) classificam a replicação
horizontal como tática de escalabilidade superior por oferecer tanto capacidade quanto
disponibilidade. O custo de uma VM com 64 vCPUs é desproporcional em relação a múltiplas
instâncias menores com HPA.

### Alternativa D: 100% Serverless (FaaS para todos os serviços)

**Descrição:** Migrar todos os microsserviços para funções serverless.

**Razão para rejeição:** O cold start é incompatível com o SLA de latência < 2s para recomendações.
Funções serverless com modelos ML de centenas de MB demoram entre 2s e 10s para cold start.
Serverless é adequado apenas para cargas event-driven intermitentes, não para APIs síncronas com
SLA estrito.

---

## Referências

- MELL, P.; GRANCE, T. *The NIST Definition of Cloud Computing* (NIST SP 800-145). NIST, 2011.
  Definição formal de IaaS, PaaS e SaaS usada como base conceitual.
- NEWMAN, S. *Building Microservices*. 2. ed. O'Reilly Media, 2021.
  Cap. 8 — Deployment: estratégias de implantação e escalabilidade de microsserviços.
- BASS, L.; CLEMENTS, P.; KAZMAN, R. *Software Architecture in Practice*. 3. ed. Addison-Wesley, 2012.
  Cap. 5 — Táticas de escalabilidade: replicação horizontal como mecanismo primário.
- RICHARDSON, C. *Microservices Patterns*. Manning Publications, 2018.
  Padrão de serviços stateless como pré-condição para escalabilidade horizontal.
- FOWLER, M. *Patterns of Enterprise Application Architecture*. Addison-Wesley, 2002.
  Session State patterns — justificativa para externalizar estado da instância de serviço.
