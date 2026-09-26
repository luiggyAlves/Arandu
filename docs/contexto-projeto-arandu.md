# Projeto Arandu — Contexto e Decisões (para a equipe)

> Documento de retomada do projeto. Serve para alinhar os 4 integrantes: o que é a ideia, o que já ficou **decidido**, as **dúvidas** que levantamos e como resolvemos, a arquitetura, a divisão de módulos e o status atual.
> Atualiza e substitui o `contexto-akcit-agente-tutor.md` anterior naquilo que divergir.
> Referência complementar: `Projeto-Arandu.docx` (arquitetura detalhada, fluxo de informação e contratos).
> Data: 24/09/2026 · AKCIT Camp 2026 — Trilha Norte (Manaus).

---

## 1. Resumo do projeto

**Nome:** Projeto Arandu (nome de trabalho).

**O que é, em 3 frases:**

1. Um **treinador de depuração** que funciona sozinho, fora de qualquer plataforma. O aluno recebe um programa curto com um erro realista, roda as entradas que quiser, acompanha o valor das variáveis passo a passo, conserta o código e explica o erro em uma frase.
2. Por trás, um **agente de IA** observa como o aluno depura, mantém um **retrato do aluno** (o que domina e como depura) e decide a cada momento o próximo passo: dar uma dica, mostrar valores reais da execução, repetir o mesmo tipo de erro em outro contexto, avançar ou encerrar.
3. **Tudo que o agente afirma sobre o código é provado rodando o programa** — ele não "acha", ele executa e verifica.

**O problema:** o juiz online só diz "certo/errado". O aluno trava, não sabe o que entendeu errado e desiste; o professor não acompanha turma grande; e depurar — a habilidade que mais separa quem avança de quem trava — quase nunca é treinada de propósito. (INEP: ~23% de reprovação/evasão em lógica de programação; UFPR: 79% dos reprovados em Algoritmos abandonaram o curso.)

**O diferencial (moat = vantagem difícil de copiar):** não é o catálogo de erros. São três coisas combinadas:
- o **retrato individual do aluno**, que melhora quanto mais o sistema é usado;
- os **dados de longo prazo** que ligam "que erro cometeu" a "continuou ou desistiu do curso";
- a **verificação por execução**, que impede o agente de inventar (o problema que derruba os tutores de IA atuais).

---

## 2. Decisões fechadas

- **Framing:** treinador de depuração **autônomo, off-platform**. O **CodeBench** entra só como **evidência do problema e fundamentação**, nunca como dependência de runtime.
- **Núcleo = treinador** (decisão pedagógica sob incerteza sobre o aluno). O **laço investigativo** é a **sub-rotina** que o treinador aciona quando decide intervir (para a dica sair ancorada em execução).
- **Modo A sempre:** o agente investiga sempre contra uma **referência correta conhecida** (todo bug do banco nasce de uma referência). Descartado o cenário "aluno traz código arbitrário sem referência".
- **Dados:** MVP usa **Refactory** (público: Python iniciante, com códigos certos, errados e testes). Fase final usa **recorte anonimizado do CodeBench** (longitudinal). *No MVP não dá tempo de usar o CodeBench.*
- **Equívocos:** usamos o catálogo **ProgMiscon** como vocabulário de rótulos (31 fichas de Python). Onde não encaixa, **extensão local** de 2–3 rótulos nossos.
- **Política de decisão:** **regras explícitas** no MVP; política aprendida (RL) como roadmap da final.
- **RAG:** **Fonte A** (trajetórias derivadas do Refactory) no MVP; **Fonte B** (uso real do sistema) é o **flywheel** de produção.
- **Ativo próprio / moat:** os **dados longitudinais + o método/pipeline validado**, **não** o corpus de bugs — o corpus será **publicado como recurso aberto** (bom para o objetivo open source do edital, mas por isso não é o moat).
- **Bugs mostrados ao aluno são sintéticos** (regenerados com o mesmo equívoco), não o código real de aluno — mais agêntico e resolve LGPD.

**Descartes do documento antigo (não usar):** o projeto BrandPilot (é outra coisa); a narrativa de "pivô de tutor reativo"; os rótulos de 4 agentes (usar os 3 abaixo); a ideia de um "agente solucionador calibrar dificuldade" (a dificuldade vem do nº de tentativas de alunos reais).

---

## 3. Dúvidas que levantamos e como resolvemos

**"Onde está o agente? Não é um if-else disfarçado?"**
Não. As ferramentas determinísticas (execução, trace) resolvem erros com assinatura clara (memória, crash). O agente opera **onde o determinismo silencia**: erros de **lógica**, em que o código roda, não trava e dá resposta errada. Ali não há regex nem chave de busca — precisa investigar.

**"O laço investigativo (rodar o código e capturar valores reais) não é complexo demais?"**
Não. É problema resolvido: o paper **LDB (ACL 2024)** faz exatamente isso (executa e coleta valores de variáveis por instrumentação); capturar valores passo a passo em Python é trivial com `sys.settrace` (o que o Python Tutor usa). **Complexidade baixa-média.** O risco fica no raciocínio do LLM, que a gente escopa por nível (MVP: usa testes existentes; final: gera entradas novas).

**"De onde vêm as trajetórias de conserto para o RAG, se no começo não há alunos?" (cold start)**
No MVP, o "caminho de conserto" é **derivado do par (errado, certo)** do Refactory — não observado de aluno. De cada par extraímos: o rótulo do equívoco, a **diferença que corrige** e a **assinatura comportamental** (via `diff_comportamental`). Com isso o RAG faz **(a)** escolher o próximo bug e **(b)** fundamentar a dica. O que **só vem com uso real** (Fonte B) é "que dica de fato destravou alunos parecidos" — esse é o flywheel de produção. *Não vamos vender o RAG como mais do que ele é no MVP.*

**"Por que exatamente duas hipóteses?"**
Não é exatamente duas — é **um punhado, tipicamente 2 a 3**. Precisa de pelo menos 2 porque hipóteses **rivais** são o que obriga a projetar um experimento que decide entre elas (senão é só confirmar um palpite). Não muitas porque encarece e dá retorno decrescente. (Base: método científico de depuração — Zeller; *strong inference* — Platt.)

**"Com base em que o agente levanta as hipóteses? Tem base na literatura?"**
Ele lê **código do aluno + saída errada + referência + trace** e propõe explicações candidatas. **A hipótese é só um palpite** — ela só vale se **sobreviver ao experimento** (execução é o juiz). Para os palpites saírem bons, condicionamos a geração no **catálogo de equívocos**, no **trace** e no **diff**. Base: *Why Programs Fail* / delta debugging (Zeller); fault localization com LLM (AutoFL, FSE 2024); LDB e Self-Debug (raciocínio ancorado em execução). **A montagem para tutoria é contribuição nossa** (reforça o Parâmetro 3).

**"O ProgMiscon tem os bugs em Python?"**
O ProgMiscon **não é um dataset de bugs** — é um **catálogo de equívocos** (247 no total; 31 de Python), com fichas (nome, crença errada, sintomas, correção). Os **bugs vêm do Refactory**; o ProgMiscon só fornece o **nome do equívoco**.

**"Montar um corpus categorizado por bug é o diferencial?"**
Não — já existem catálogos categorizados (ProgMiscon, PyMETA, HaPy-Bug). O corpus é **meio**, não é o ativo. O ativo é o dado longitudinal + o método (ver seção 2).

---

## 4. Arquitetura (visão)

**Três agentes:**
1. **Construtor** — gera e valida os bugs (Fase A). Na Fase B, é chamado para repetir um equívoco em outro contexto.
2. **Treinador** — o cérebro. Conduz a sessão, mantém o modelo do aluno e decide a intervenção.
3. **Verificador** — o guardrail. Barra toda mensagem que (a) não esteja ancorada em execução ou (b) entregue a solução.

**Ferramentas determinísticas (expostas via MCP):** `executar(codigo, entrada)`, `trace` (valores passo a passo), `rodar_suite`, `diff_comportamental` (primeiro ponto de divergência entre código do aluno e referência), `gerar_entrada_discriminante`.

**Três lugares de estado:** Banco de bugs (compartilhado) · Sessão atual (curto prazo) · Modelo do aluno (longo prazo).

**Duas fases:**
- **Fase A (offline, roda 1 vez):** pegar dados (Refactory) → rotular equívoco (ProgMiscon) → Construtor gera bug novo → Validador executa e aprova/reprova (laço) → calibrar dificuldade (nº de tentativas reais) → minerar trajetórias. Resultado: **Banco de Bugs** + **Loja de Trajetórias**.
- **Fase B (runtime, roda sempre):** Treinador escolhe o bug → aluno investiga (roda entradas, vê variáveis, conserta, explica) → Treinador decide intervenção (aciona sub-rotina investigativa se preciso) → Verificador checa a mensagem → observador atualiza o modelo do aluno → painel registra a decisão + evidência.

**Sub-rotina investigativa:** gera 2–3 hipóteses do equívoco → gera entrada que as separa → executa → poda até sobrar uma → dica ancorada nos valores reais.

---

## 5. Modelo do aluno e estratégias de feedback

Baseado no artigo **SP-TeachLLM** (que faz modelo do aluno → seleção de estratégia via RL) + literatura de feedback (Narciss; Keuning) + knowledge tracing. *Ressalva: o SP-TeachLLM foi avaliado com alunos simulados por LLM e benchmarks de código, não com alunos reais — usamos como validação de arquitetura, não como lista pronta de estratégias.*

**Características do aluno a capturar:**

| Grupo | O que capturamos |
|---|---|
| Domínio conceitual | domínio por equívoco (0–1), estilo BKT, com rótulos ProgMiscon |
| Habilidade de depuração *(diferencial)* | forma hipótese? testa com entrada que discrimina? lê variáveis ou chuta? localiza antes de editar? |
| Esforço / frustração | nº de tentativas, tempo, repetição do mesmo erro, pedidos de dica |
| Qualidade da explicação | a frase do aluno pontuada contra o equívoco de referência |
| Progresso / contexto | bugs vistos, resultados, dificuldade atual (para aplicar ZPD) |

Todas atualizadas a partir de **evidência verificada por execução**.

**Estratégias de feedback (escada — sobe só quando precisa):**

| Nível | Estratégia | Termo (Narciss) |
|---|---|---|
| 0 | devolver pro aluno tentar (falha produtiva) | — |
| 1 | pergunta metacognitiva ("que hipótese você tem?") | KMC |
| 2 | "seu código falha no teste X" | KR |
| 3 | mostrar onde o comportamento diverge (valores reais) | KM |
| 4 | dica de próximo passo, sem a correção | KH |
| 5 | nomear/explicar o equívoco (texto do ProgMiscon) | KC |
| — | **nunca**: entregar o código correto | KCR (linha do guardrail) |

Ações não-verbais: mostrar valores, repetir o equívoco em outro contexto, avançar, encerrar.

**Teorias como travas de design:** ZPD (dificuldade logo acima do domínio), Carga Cognitiva (um equívoco por vez), Falha Produtiva (deixar tentar antes da dica), Autodeterminação (não super-ajudar).

---

## 6. Divisão em módulos e contratos

Quatro frentes em paralelo, integradas no fim. Detalhe completo (campos, tipos, exemplos) no `Projeto-Arandu.docx`.

- **M1 — Motor de execução + ferramentas (MCP).** Fundação de que todos dependem; entrega primeiro o formato das ferramentas.
- **M2 — Fase A: banco de bugs.** Ingestão, rotulagem, laço Construtor→Validador, trajetórias, dificuldade.
- **M3 — Fase B: treinador + modelo do aluno.** O cérebro e o diferencial. *(responsável: Guilherme)*
- **M4 — Experiência + medição + pitch.** Interface, observabilidade, métricas (incl. ablação), BMC, pitch, relatórios quinzenais.

**Caminho crítico:** M1 → M3. Se algo precisar encolher no MVP, encolhe em M2/M4, nunca em M1/M3.

**Contrato = formato de dado combinado entre duas peças.** Fixá-los no Dia 0 permite trabalhar em paralelo contra mocks. Os cinco: (A) ferramentas de execução, (B) item do banco de bugs, (C) registro de trajetória, (D) modelo do aluno, (E) envelope de mensagem que o Verificador checa.

---

## 7. MVP do hackathon regional (26/09)

**Entra:** ferramentas de execução (M1); alguns bugs do Refactory rotulados à mão com 5–10 equívocos + fatia pequena do laço Construtor→Validador ao vivo (M2); Treinador por regras + sub-rotina investigativa + Verificador (M3); interface da sessão + painel de decisões + métrica simples de ablação (M4).

**A cena que precisa funcionar:** um código que compila, roda, não trava e falha silenciosamente num teste. O juiz só diz "errado". O Arandu levanta 2–3 hipóteses, fabrica uma entrada que as separa, roda instrumentado, descarta as demais e explica o equívoco mostrando os valores reais — sem entregar a correção. Se isso for demonstrado, o critério técnico (30%) está bem defendido.

**Fica para a final:** base própria (recorte anonimizado do CodeBench), RAG por uso real (flywheel), política aprendida (RL), painel do professor completo, piloto com turma real.

---

## 8. Status atual e próximos passos

- Arquitetura **fechada e validada**. Documento formal (`Projeto-Arandu.docx`) entregue.
- **Guilherme assumiu o M3.** Antes de codar, vamos **fechar no papel 7 artefatos de design** (todos testáveis sem código) e só depois implementar do mais arriscado pro mais fácil, contra mocks de M1/M2:
  1. as fronteiras/contratos do M3;
  2. a máquina de estados da sessão;
  3. a política de decisão como tabela explícita;
  4. as regras de atualização do modelo do aluno;
  5. a sub-rotina investigativa + contratos de prompt;
  6. o Verificador (guardrail);
  7. o plano de teste (casos-ouro, aluno simulado, ablação).
- **Decisões em aberto (gates da implementação do M3):**
  - **LLM/provedor:** Bedrock (Claude) via créditos AWS? API Anthropic? OpenAI?
  - **Orquestração:** Python puro + function calling (recomendado para o MVP) vs LangGraph.

---

## 9. Fundamentação (para quem quiser conferir)

- LDB — depurar verificando execução passo a passo (ACL 2024): https://arxiv.org/abs/2402.16906
- Teaching LLMs to Self-Debug (ICLR 2024): https://arxiv.org/abs/2304.05128
- AutoFL / LLM-based fault localization (FSE 2024): https://dl.acm.org/doi/full/10.1145/3660771
- Zeller — *Why Programs Fail* / delta debugging: https://queue.acm.org/detail.cfm?id=1217270
- ProgMiscon — catálogo de equívocos (Python): https://progmiscon.org/
- Refactory — dataset do protótipo: https://github.com/githubhuyang/refactory
- SP-TeachLLM (Information/MDPI 2025): https://doi.org/10.3390/info16121045
- Keuning et al. — revisão de feedback automático para programação (ACM TOCE 2019): https://dl.acm.org/doi/10.1145/3231711
- Narciss — estratégias de feedback (2008): https://www.researchgate.net/profile/Susanne-Narciss/publication/233833269_Feedback_Strategies_for_Interactive_Learning_Tasks
- A Survey of Knowledge Tracing (BKT/DKT): https://arxiv.org/pdf/2105.15106
