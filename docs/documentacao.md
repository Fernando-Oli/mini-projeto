# Documentação do Projeto: EduVerse

## 1. Classificação de Domínio: Inteligência Artificial (IA)

Embora o **EduVerse** utilize tecnologias Web (para interface) e de Sistemas de Informação (para armazenamento e gestão de dados educacionais), o "coração" do projeto é a **capacidade preditiva e prescritiva**. 

A proposta foca na análise de dados para personalização e otimização, o que exige o uso de:
*   Algoritmos de filtragem colaborativa;
*   Processamento de Linguagem Natural (NLP);
*   Redes neurais para compreensão do comportamento do estudante.

> **Nota:** Sem o domínio de IA, o sistema seria apenas um repositório estático de arquivos, perdendo sua proposta de valor principal.

---

## 2. Mapa de Stakeholders

| Stakeholder | Principal Interesse / Preocupação com a Arquitetura de IA |
| :--- | :--- |
| **Estudante (Usuário Final)** | **Relevância e Engajamento:** Preocupa-se se as recomendações realmente ajudam a sanar suas dúvidas ou se o sistema sugere conteúdos irrelevantes. |
| **Cientista de Dados** | **Qualidade e Proveniência:** Focado em pipelines de dados, garantindo que os dados de treino sejam limpos e que não haja viés (*bias*) nas recomendações. |
| **Gerente de Produto** | **Retenção e Valor:** Preocupa-se com o impacto da IA nas métricas de uso (tempo de tela, conclusão) e se o custo computacional é sustentável. |
| **Engenheiro de Segurança** | **Proteção de Dados:** Focado em como o sistema lida com o histórico escolar e dados sensíveis, garantindo conformidade com a **LGPD**. |

---

## 3. Requisitos Funcionais (RFs)

*   **RF01 - Recomendação de Conteúdo:** O sistema deve recomendar materiais de estudo (vídeos, textos, exercícios) com base no histórico de desempenho e lacunas de conhecimento identificadas.
*   **RF02 - Análise de Sentimento/Feedback:** O sistema deve processar o feedback textual do aluno sobre as aulas para ajustar o peso de importância de futuros temas recomendados.
*   **RF03 - Predição de Risco de Evasão:** O sistema deve identificar padrões de comportamento (ex: queda na frequência) e alertar tutores sobre a probabilidade de abandono.

---

## 4. Requisitos Não Funcionais (RNFs) - Modelo FURPS+

### Performance (Eficiência)
O tempo de inferência para gerar uma lista de recomendações personalizadas na dashboard inicial não deve prejudicar a experiência de navegação.

### Usabilidade (Transparência)
As sugestões de IA devem ser acompanhadas de uma breve explicação (*Explainable AI*), como: *"Porque você estudou X, talvez goste de Y"*, aumentando a confiança do usuário.

---

## 5. Refinamento para Mensurabilidade

| Tipo | Descrição |
| :--- | :--- |
| **Declaração Vaga** | "As recomendações de estudo do EduVerse devem ser precisas e úteis para os alunos." |
| **Declaração Mensurável (Testável)** | "O sistema de recomendação deve apresentar uma **CTR (Click-Through Rate) > 20%** e uma **Taxa de Relevância Percebida de pelo menos 85%** nos primeiros 3 meses de operação." |
