# Template do Aluno: Mini Projeto "O Arquiteto Decisor"

**Aluno:** Fernando Luis Rodrigues de Oliveira  
**Matr�cula:** 2321056  
**Reposit�rio GitHub:** [Fernando-Oli/mini-projeto](https://github.com/Fernando-Oli/mini-projeto.git)

---

## ?? CICLO 1: Vis�o e Requisitos (Fase 1)

### 1.1 Resumo do Cen�rio de Neg�cio
O **EduVerse** � uma plataforma de aprendizado adaptativo projetada para mitigar a rigidez do ensino tradicional. Utilizando **Intelig�ncia Artificial**, o sistema cria trilhas personalizadas, identifica lacunas de conhecimento e sugere conte�dos espec�ficos em tempo real.

**Objetivos Estrat�gicos:**
*   **Reten��o de Alunos:** Aumentar o engajamento atrav�s de relev�ncia pedag�gica.
*   **Efic�cia da Aprendizagem:** Prover feedback instant�neo para otimizar o fluxo de estudo.

**Principais Stakeholders:**

| Papel | Responsabilidade Principal |
| :--- | :--- |
| **Estudante** | Busca um fluxo de estudo fluido e personalizado. |
| **Cientista de Dados** | Garante a qualidade e integridade dos dados para a IA. |
| **Gestor de Produto** | Assegura que a solu��o resolva a dor real do cliente. |
| **Engenheiro de Neg�cios** | Zela pela conformidade legal, governan�a e viabilidade. |
| **Engenheiro de Seguran�a** | Protege contra ataques (ex: *data poisoning*) e garante conformidade com a **LGPD**. |

---

### 1.2 Atributos de Qualidade (RNFs) Priorizados

*   **[Performance]:** O sistema deve gerar recomenda��es em menos de 2 segundos.
    *   *Justificativa:* Essencial para manter o fluxo de estudo e o engajamento em tempo real.
*   **[Escalabilidade]:** Suportar milhares de alunos simultaneamente sem degrada��o.
    *   *Justificativa:* Requisito chave para o crescimento e sustentabilidade da plataforma.
*   **[Usabilidade - XAI]:** A IA deve explicar os motivos das recomenda��es (*Explainable AI*).
    *   *Justificativa:* Aumenta a transpar�ncia e a confian�a do aluno nas trilhas sugeridas.
*   **[Manutenibilidade]:** Permitir atualiza��o de modelos e conte�dos sem *downtime*.
    *   *Justificativa:* Crucial para um dom�nio tecnol�gico que evolui rapidamente.
*   **[Confiabilidade]:** Atingir uma taxa de CTR (Click-Through Rate) superior a 20%.
    *   *Justificativa:* Garante que o motor de recomenda��o est� entregando valor real.

---

### 1.3 Diagrama de Contexto (C4 N�vel 1)

Diagrama em /diagrams/diagrama-c4.png

---

### 1.4 Classifica��o da Estrat�gia

**Classifica��o:** Ousada

**Justificativa:**
A escolha � classificada como **Ousada** devido � transi��o de sistemas determin�sticos para modelos **probabil�sticos e adaptativos**. Segundo Pressman, o software � um "transformador de informa��es" que se deteriora pela complexidade mal gerida. No **EduVerse**, a arquitetura enfrenta o desafio de manter a integridade conceitual perante "requisitos emergentes" (o sistema aprende e evolui com o uso). Essa abordagem exige alta maturidade tecnol�gica para garantir que a vis�o arquitetural sustente a escalabilidade e a inova��o de forma cont�nua, mitigando a deteriora��o causada pela evolu��o constante.
