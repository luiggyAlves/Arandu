# Projeto Arandu

**Um treinador de depuração autônomo: o aluno recebe um programa curto com um
bug de lógica realista, investiga (roda entradas, vê variáveis passo a passo),
conserta e explica o erro. Um agente de IA observa a investigação, mantém um
modelo do aluno e decide sozinho a próxima intervenção — sempre ancorada em
execução real, nunca em suposição.**

Projeto do **AKCIT Camp 2026** (Agentes de IA) — Trilha Norte / Manaus.

> Arandu (tupi, "saber/conhecimento"). A ferramenta não corrige o código por
> você: ela ensina o **processo** de depuração no espaço onde as ferramentas
> comuns se calam — os erros de **lógica** (o programa roda sem quebrar e mesmo
> assim está errado).

---

## Índice
1. [O problema](#1-o-problema)
2. [A solução e os 4 módulos](#2-a-solução-e-os-4-módulos)
3. [O pipeline completo (Fase A offline → Fase B runtime)](#3-o-pipeline-completo)
4. [Fluxo de informação em runtime](#4-fluxo-de-informação-em-runtime)
5. [Fluxo do agente: inputs, lógica e outputs](#5-fluxo-do-agente)
6. [Exemplo prático (uma sessão real, passo a passo)](#6-exemplo-prático)
7. [Detalhe crucial: o que o agente "vê" para decidir (o retrato)](#7-o-retrato)
8. [Detalhe crucial: as tarefas de LLM (prompts)](#8-as-tarefas-de-llm)
9. [Modelo do aluno](#9-modelo-do-aluno)
10. [Verificador (guardrail)](#10-verificador)
11. [Como rodar](#11-como-rodar)
12. [Estrutura de pastas e o que cada arquivo faz](#12-estrutura-e-arquivos)
13. [Datasets, fundamentação e limitações](#13-datasets-e-limitações)

---

## 1. O problema

Ferramentas de correção automática (juízes online, linters, testes) dizem **que**
um programa está errado, mas param aí. Elas brilham no determinístico (sintaxe,
exceção, teste que falha) e se calam onde o programa **roda sem quebrar e mesmo
assim está errado**: os erros de **lógica** — condição invertida, filtro que
faltou, `range` com um a menos, comparar com `== False`. Pior: quando apontam a
linha, ensinam a consertar *aquele* bug, não a **depurar**.

Arandu ataca esse vão: ensina o **método investigativo** de depuração usando a
execução real como fonte de verdade.

---

## 2. A solução e os 4 módulos

O sistema é dividido em quatro módulos com contratos claros (a equipe trabalha em
paralelo). Este repositório é o **runtime do M3** integrado ao **M1** e aos
**dados do M2**.

| Módulo | Papel | Quando roda |
|---|---|---|
| **M1 — Motor de execução** | Roda o código do aluno com segurança (sandbox) e devolve fatos: `executar`, `trace`, `rodar_suite`, `diff_comportamental`. É a **fonte de verdade**. | Runtime |
| **M2 — Banco de bugs** | Pipeline **offline** (roda uma vez): do dataset bruto do Refactory até um banco curado de bugs rotulados (ProgMiscon), variações validadas e uma loja de trajetórias. | Offline (Fase A) |
| **M3 — Treinador** | O agente: decide se/quando/como intervir, investiga (ReAct), redige dicas; mantém o modelo do aluno; o Verificador (guardrail). | Runtime (Fase B) |
| **M4 — Interface/métricas/pitch** | A interface web do aluno e as métricas. *(Neste repo, a interface em `arandu-m3/web/` já cumpre esse papel para a demo.)* | Runtime |

Ideia central em uma frase: **o agente decide como um tutor decidiria; as
ferramentas determinísticas do M1 produzem os fatos; o Verificador impede
vazamento da solução; e tudo é registrado ao vivo.**

---

## 3. O pipeline completo

### Fase A — M2 (offline, roda uma vez): construir o material didático

```mermaid
flowchart LR
    A[ProgMiscon<br/>scrape] --> B[Catálogo de equívocos<br/>~30 fichas]
    C[Refactory<br/>data.zip ~1.783 bugs] --> D[Etapa 1: classificar<br/>→ ~895 falha silenciosa]
    D --> E[Etapa 2: buscar + rotular<br/>+ revisão humana]
    B --> E
    E --> F[Banco de bugs curado<br/>5 bugs reais rotulados]
    F --> G[Etapa 3: Construtor→Validador<br/>gera variações do MESMO equívoco]
    G --> H[Variações aprovadas<br/>+3 = 8 bugs de treino]
    F --> I[Etapa 4: minerar trajetórias<br/>→ Loja de Trajetórias]
```

O que a Fase A entrega para o runtime (arquivos em `Arandu-m2/Mod2/data/bugs/`):
- **`banco_de_bugs.json`** — bugs reais do Refactory, rotulados com o equívoco do
  ProgMiscon, no formato do runtime (Contrato B).
- **`variacoes_etapa3.json`** — variações geradas que reproduzem o mesmo equívoco;
  só as **aprovadas pelo Validador** viram treino.
- **`loja_trajetorias.json`** — trajetórias de intervenção por equívoco (semente
  do RAG; ver limitações).

> A geração usa um LLM (por padrão local, via Ollama) e revisão humana no meio —
> é offline e não precisa rodar para usar a ferramenta. O runtime só **consome**
> os JSONs acima.

### Fase B — M3 (runtime): treinar o aluno

O aluno interage pela interface; cada ação vira um **evento** para o motor da
sessão (M3), que consulta o **agente** (decisão) e as **ferramentas** (M1), e
mantém o **modelo do aluno**. Detalhado na próxima seção.

---

## 4. Fluxo de informação em runtime

```mermaid
flowchart TD
    A["Aluno na interface (M4)<br/>rodar / editar / ver variáveis / colar / submeter / explicar"] -->|POST /evento| B[sessao.processar_evento]
    B --> C[atualiza sinais + modelo do aluno]
    B --> D{"Monitor agêntico<br/>decidir_intervencao()"}
    D -->|monta o RETRATO<br/>contexto+progresso+modelo| E["LLM tarefa 'decidir_acao'"]
    E -->|acao + motivo| D
    D -->|OBSERVAR| F[registra no painel e segue]
    D -->|ação| G[guarda-corpos: cooldown, teto, Verificador]
    G -->|DAR_DICA| H["investigar() — laço ReAct"]
    H --> I["M1 (tools.py → arandu_motor)<br/>executar / trace / diff_comportamental / rodar_suite"]
    I --> H
    G --> J[intervenção volta na resposta + no painel ao vivo]
    B -->|GET /painel a cada 2,5s| K["telinha 'Raciocínio do Agente'"]
    A -->|explicou o erro| L["LLM 'avaliar_explicacao' → rubrica"]
    L --> M[card de rubrica: nota por dimensão]
```

**Eventos que a interface envia** (`POST /evento`, campo `tipo`):
`rodou_entrada`, `ver_trace`, `pediu_dica`, `submeteu_correcao`, `explicou`,
`respondeu_pergunta`, `sinais` (churn/pausas/colagem), `inativo`, `sair`.

Depois de `rodou_entrada`, `submeteu_correcao` (quando falha) e da colagem de
código externo, a sessão chama o **monitor**: monta o **retrato** (seção 7) e
pergunta ao agente o que fazer. A decisão e a ação entram na resposta **e** no
painel. `ver_trace` (abrir variáveis) é ação boa do aluno — só observamos.

---

## 5. Fluxo do agente

O agente é o **Treinador** (`arandu-m3/treinador.py`), acionado pelo orquestrador
da sessão (`arandu-m3/sessao.py`). Ele trabalha em quatro etapas: **decidir** se
intervém, **investigar** o bug (ReAct), **redigir uma dica verificada** e
**avaliar** o que o aluno responde ou explica. Esta seção descreve o contrato de
cada etapa: o que entra, o que acontece e o que sai.

### 5.1 Inputs

| Gatilho (evento da interface) | Etapa acionada | O que o agente recebe |
|---|---|---|
| `rodou_entrada` | Decidir | Retrato + baralho de ações. `evento_atual`: `entrada`, `saida`, `entrada_expoe_o_erro`, `e_repeticao_da_anterior` |
| `submeteu_correcao` que falhou | Decidir | Retrato + baralho. `evento_atual`: `submeteu_e_falhou`, `testes_passaram`, `testes_total` |
| `sinais` com colagem de código externo | Decidir | Retrato + baralho. `evento_atual`: `colou_codigo_externo` (colar trecho do próprio exercício **não** conta) |
| `pediu_dica`, ou decisão `DAR_DICA` | Investigar → Dica | Código atual do aluno, código de referência, entrada que falha (1º teste reprovado da suíte), testes, modo (`stdin`/`chamada`) e assinatura da função |
| `respondeu_pergunta` | Avaliar resposta | Pergunta feita, resposta do aluno, equívoco do bug, correção de referência, código do aluno |
| `explicou` (depois de passar nos testes) | Avaliar explicação | Explicação do aluno, equívoco do bug, correção de referência |

**Não acionam o agente:** `ver_trace` (só registra que o aluno abriu as
variáveis), `sinais` sem colagem (atualizam o modelo do aluno) e `inativo`/`sair`
(encerram a sessão).

O **retrato** reúne só fatos, em cinco blocos: `evento_atual`, `progresso` no
bug, `historico_recente` (as últimas 8 ações em linguagem natural),
`modelo_aluno`, e `bug` com flags (`ja_usou_dica`, `ja_intervim_neste_bug`,
`ultima_intervencao_do_agente`). Campo a campo na [seção 7](#7-o-retrato).

### 5.2 Lógica

```mermaid
flowchart TD
    EV["Evento do aluno<br/>rodou entrada · submeteu e falhou · colou código de fora"] --> RT["Monta o retrato (só fatos)"]
    RT --> DA["LLM: decidir_acao"]
    DA -->|OBSERVAR| SL["Silêncio<br/>(a leitura vai para o painel)"]
    DA -->|outra ação| GC{"Guarda-corpos<br/>teto de 8 · cooldown de 15 s"}
    GC -->|bloqueou| SL
    GC -->|mensagem curta| V1{"Verificador<br/>(não exige âncora)"}
    GC -->|DAR_DICA| INV["investigar() — laço ReAct com o M1"]
    PD["Aluno pede dica"] --> INV
    INV --> RD["LLM: redigir_dica (começa no nível 3)"]
    RD --> V2{"Verificador<br/>(exige âncora)"}
    V2 -->|"reprovou: desce 1 nível<br/>(3ª reprovação → dica segura nível 1)"| RD
    V2 -->|aprovou| OUT["Intervenção → aluno + painel"]
    V1 -->|aprovou| OUT
    V1 -->|barrou| SL
```

**Etapa 1: Decidir.** A cada gatilho, o LLM (tarefa `decidir_acao`) lê o retrato
e escolhe **uma** ação do baralho: `OBSERVAR · ENCORAJAR · PERGUNTAR ·
SUGERIR_TESTE · MOSTRAR_VALORES · DAR_DICA · AVANCAR`. `OBSERVAR` é o padrão; o
prompt manda intervir só com razão clara e escalar (não repetir o mesmo tipo de
ação no mesmo bug). A leitura e a decisão vão **sempre** para o painel, mesmo
quando a escolha é observar. Se a ação não é `OBSERVAR`, os guarda-corpos
conferem o teto de intervenções e o cooldown. Eles não decidem *quando* ajudar,
só evitam atrapalhar. Depois disso:

- `ENCORAJAR`, `PERGUNTAR`, `SUGERIR_TESTE`, `AVANCAR`: a mensagem escrita pelo
  LLM passa pelo Verificador (que dispensa âncora, mas barra vazamento da
  solução). `PERGUNTAR` abre uma caixa de resposta para o aluno.
- `MOSTRAR_VALORES`: além da mensagem, o agente **roda o trace de verdade** no M1
  com a última entrada e envia as variáveis passo a passo.
- `DAR_DICA`: segue para as etapas 2 e 3.

**Etapa 2: Investigar (ReAct).** Antes de dizer qualquer coisa, o agente prova o
diagnóstico executando código:

1. `gerar_hipoteses`: 2–3 hipóteses concorrentes sobre o **equívoco**, a partir
   dos dois códigos e do catálogo de equívocos (ProgMiscon).
2. Enquanto restar mais de uma hipótese (até 6 passos):
   - `projetar_entrada` propõe de 2 a 4 entradas em que as hipóteses preveem
     saídas **diferentes** (nunca repete uma já tentada);
   - o M1 roda cada entrada no código do aluno **e** no de referência até uma
     divergir. Cada execução vira uma **âncora** (entrada, saída do aluno, saída
     esperada);
   - `podar` recebe o resultado real e mantém só as hipóteses compatíveis.
   - Se não houver entrada nova para testar, ou se a poda eliminar todas as
     hipóteses, elas são regeneradas (até 2 vezes); depois disso, o laço para.
3. Se não convergir para uma hipótese, cai no **modo direto**: roda a entrada que
   falha na suíte e usa esse resultado como âncora.

Sai daqui: `{equivoco, ancoras, conclusivo, log}`. O `log` alimenta o painel.

**Etapa 3: Dica verificada.** `redigir_dica` escreve a dica no nível 3 (a escada
vai de 1 = pergunta socrática a 5 = nomear o equívoco; entregar a correção nunca
é permitido), ancorada nos valores reais. O Verificador **exige âncora** e barra
a revelação da solução. A cada reprovação, a dica é reescrita um nível abaixo; na
3ª, sai uma dica segura de nível 1 (*"Qual a sua hipótese sobre o erro? Que
entrada você poderia rodar para testá-la?"*).

**Etapa 4: Avaliar.**
- `avaliar_resposta`: feedback de 1–2 frases, ancorado no exercício (não é chat
  livre), mais uma nota de `compreensao` de 0 a 1. O feedback também passa pelo
  Verificador.
- `avaliar_explicacao`: rubrica com `identificou`, `causa` e `correcao` (0–1),
  mais `nota` e `comentario`.

**Quando algo falha, o agente degrada com segurança e nunca derruba a sessão:**

| Falha | Comportamento |
|---|---|
| `decidir_acao` dá erro (rede, JSON inválido) | Assume `OBSERVAR` |
| Investigação dá erro | Envia a dica segura de nível 1 |
| `avaliar_resposta` dá erro | Feedback genérico: *"Anotei a sua resposta…"* |
| `avaliar_explicacao` dá erro | Rubrica vazia com *"Não consegui avaliar a explicação agora."* |
| Ação desconhecida vinda do LLM | Tratada como `OBSERVAR` |

**Limites** (em `arandu-m3/config.py`):

| Parâmetro | Valor | Protege contra |
|---|---|---|
| `MAX_PASSOS_REACT` | 6 | Laço de investigação longo demais |
| `MAX_REGENERACOES_HIPOTESE` | 2 | Hipóteses que nunca convergem |
| `MAX_REJEICOES_VERIFICADOR` | 3 | Dica reprovada em loop |
| `MAX_INTERVENCOES_PROATIVAS` | 8 por sessão | Agente falando demais |
| `COOLDOWN_INTERVENCAO_S` | 15 s | Intervenções em sequência |
| `MAX_CHAMADAS_LLM_SESSAO` | 150 por sessão | Custo descontrolado |

### 5.3 Outputs

| Output | Onde aparece | Formato |
|---|---|---|
| Intervenção proativa | Campo `intervencao` na resposta do `POST /evento` | `{acao, mensagem, proativa: true}` + `espera_resposta` (em `PERGUNTAR`), `trace: {entrada, passos}` (em `MOSTRAR_VALORES`) ou `nivel` (em `DAR_DICA`) |
| Dica pedida pelo aluno | Resposta do `pediu_dica` | `{resposta: "dica", mensagem, nivel}` |
| Feedback de uma resposta | Resposta do `respondeu_pergunta` | `{resposta: "feedback_resposta", feedback, compreensao}` |
| Rubrica da explicação | Resposta do `explicou` | `rubrica: {identificou, causa, correcao, nota, comentario}` + `bug_resolvido` + o próximo bug (ou o encerramento) |
| Raciocínio ao vivo | `GET /painel` (tela "Raciocínio do Agente") | Eventos: 🧠 leitura · 🎯 decisão com confiança · 🔬 hipóteses, experimentos, poda e conclusão · 💬 fala/dica com veredito do Verificador, rejeições e âncoras · 🔒 guarda-corpo acionado |
| Modelo do aluno | `arandu-m3/dados_alunos/<aluno>.json` | Atualizado só com evidência limpa (ver abaixo) |
| Registro da sessão | `arandu-m3/dados_sessoes/<sessão>.json` (visão do professor) | Intervenções, dicas, rubricas e custo (chamadas e tokens por tarefa) |

**Como o fluxo do agente alimenta o modelo do aluno (evidência limpa):**
- O aluno roda uma entrada que expõe o erro → sobe `testa_entrada_discriminante`.
  Se quem rodou foi o agente, não conta.
- Resposta com `compreensao` ≥ 0,5 → conta como `forma_hipotese`.
- O domínio do equívoco (BKT) só recebe o crédito de acerto se a nota da
  explicação for ≥ 0,5, ou ≥ 0,7 se o aluno colou código de fora. Caso
  contrário, conta como erro: passar nos testes não é prova de domínio. Por
  exemplo, partindo de 0,5, um acerto leva a 0,87 e um erro a 0,38.
- Variáveis abertas pelo agente (`MOSTRAR_VALORES`) não contam como `le_variaveis`.

**Exemplo de um ciclo de decisão** (retrato abreviado):

```jsonc
// Input: parte do retrato enviado ao LLM
{
  "evento_atual": {"tipo": "rodou_entrada", "entrada": "search(42, (-5, 1, 3, 5, 7, 10))",
                   "saida": "6", "entrada_expoe_o_erro": false, "e_repeticao_da_anterior": true},
  "progresso": {"execucoes_neste_bug": 3, "repeticoes_seguidas_da_mesma_entrada": 2,
                "ja_achou_entrada_que_expoe_o_erro": false},
  "ja_intervim_neste_bug": false
}
// Output do LLM (decidir_acao)
{"acao": "SUGERIR_TESTE", "confianca": 0.7,
 "motivo": "Ele repetiu a mesma entrada duas vezes seguidas sem tirar conclusão.",
 "mensagem": "Que tal tentar uma entrada bem diferente, tipo um caso extremo, pra ver como o programa reage?"}
// O que a interface recebe (depois dos guarda-corpos e do Verificador)
"intervencao": {"acao": "SUGERIR_TESTE", "mensagem": "Que tal tentar uma entrada bem diferente…",
                "proativa": true, "espera_resposta": false}
```

---

## 6. Exemplo prático

Uma sessão real com o bug `search(x, seq)` cujo equívoco é comparar com um
booleano (`if seq == False:` — equívoco *ComparisonWithBoolLiteral*):

1. **Aluno roda** `search(42, (-5,1,3,5,7,10))` → saída `6`.
   → 🧠 leitura: "1ª execução, explorando"; 🎯 **OBSERVAR**.
2. **Roda a mesma entrada de novo** → 🎯 **OBSERVAR** (ainda explorando).
3. **Roda a mesma pela 3ª vez** → 🧠 "repetiu sem tirar conclusão"; 🎯 **PERGUNTAR**:
   *"O que você espera que aconteça testando a mesma entrada de novo?"* — abre a
   caixa de resposta; o aluno responde e recebe **feedback ancorado**.
4. **Roda** `search(42, ())` (lista vazia) → saída `None`, **discriminante!**
   → 🎯 **ENCORAJAR**: *"Boa! Essa entrada expôs o problema."*
5. **Cola um código de fora** → 🎯 **PERGUNTAR**: *"Explique com suas palavras o
   que o código colado faz."* (colar um trecho do **próprio** exercício NÃO
   dispara isso.)
6. **Pede dica** → o agente **investiga** (ReAct), visível no painel:
   `🔬 3 hipóteses → 🔬 experimento: rodei search(5, []) → SEPAROU → 🔬 poda: sobra H1
   → 🔬 conclusão: CondicaoInvertida` → 💬 **dica ancorada** (sem entregar a resposta,
   barrada pelo Verificador se tentasse).
7. **Corrige e submete** → 11/11 testes passam → o sistema pede a explicação.
8. **Explica o erro** → aparece a **rubrica**: Identificou 100% · Causa 50% ·
   Correção 0% · Nota 50% + comentário. O aluno lê e clica em "próximo desafio".

Tudo isso aparece **ao vivo** na tela "Raciocínio do Agente" — é o que torna a
agência demonstrável.

---

## 7. O retrato

**Este é o detalhe mais importante da decisão agêntica.** A cada ação, o
orquestrador monta um "retrato" da situação (só **fatos**, não decide nada) e o
entrega ao agente. É exatamente isto que o agente "vê" para decidir
(`sessao._retrato()`):

**Do que acabou de acontecer (`evento_atual`):**
- `tipo` do evento (rodou_entrada, submeteu_correcao, colou_codigo_externo…)
- `entrada` rodada e `saida` obtida
- `entrada_expoe_o_erro` — essa entrada é **discriminante** (revela o bug)? *(vem do M1)*
- `e_repeticao_da_anterior` — repetiu a mesma entrada?

**Do progresso no bug atual (`progresso`):**
- `execucoes_neste_bug`
- `entradas_distintas_testadas` — mede exploração
- `repeticoes_seguidas_da_mesma_entrada` — mede estagnação
- `ja_achou_entrada_que_expoe_o_erro`
- `editou_o_codigo` — já mexeu no editor (não só na entrada)?
- `modo` — chamada de função ou stdin

**Do histórico recente da sessão (`historico_recente`):** as últimas ~8 ações em
linguagem natural (ex.: "rodou X → não expôs o erro", "abriu as variáveis",
"pediu dica").

**Do modelo do aluno (`modelo_aluno`):**
- `dominio_do_equivoco_atual` — probabilidade de domínio (BKT) no equívoco do bug
- `depuracao` — 4 sinais 0–1: `forma_hipotese`, `testa_entrada_discriminante`,
  `le_variaveis`, `localiza_antes_de_editar`
- `bugs_resolvidos` — quantos já resolveu
- `interface_neste_bug` — `abriu_ver_variaveis` (0 = nunca olhou o trace) e
  `colou_codigo_de_fora`

**Do contexto (`bug`, e flags):** `enunciado`, `equivoco`, `tempo_no_bug_s`;
`ja_usou_dica`; `ja_intervim_neste_bug`; `ultima_intervencao_do_agente`
(`{acao, ha_s}` — evita repetir o mesmo tipo de cutucão e permite escalonar).

Com esse retrato, o agente escolhe **uma** ação de um baralho fixo:
`OBSERVAR · ENCORAJAR · PERGUNTAR · SUGERIR_TESTE · MOSTRAR_VALORES · DAR_DICA · AVANCAR`.
Não há regra fixa ("aja após N erros") — a decisão é do LLM, com base no retrato.
O código só impõe **guarda-corpos de segurança** (cooldown, teto por sessão,
Verificador), que não decidem *quando* ajudar, só evitam atrapalhar.

---

## 8. As tarefas de LLM

Todas as chamadas ao LLM passam por uma porta única, `llm.chamar(tarefa, dados)`
(`arandu-m3/llm.py`). Há três implementações: `AnthropicLLM` (Claude Sonnet por
padrão), `OpenAILLM` (gpt-4o por padrão) — ambas com timeout — e `MockLLM`
(respostas roteirizadas, roda sem chave). As **tarefas** e o que cada prompt faz:

| Tarefa | Para quê | Devolve |
|---|---|---|
| `decidir_acao` | **Decisão agêntica**: dado o retrato, escolher a ação (ou OBSERVAR). | `{acao, motivo, confianca, mensagem}` |
| `gerar_hipoteses` | Início da investigação: 2–3 hipóteses concorrentes sobre o equívoco. | `{hipoteses:[{id,equivoco,descricao}]}` |
| `projetar_entrada` | Propor entradas **discriminantes** que separam as hipóteses. | `{entradas:[...], justificativa}` |
| `podar` | Dado o resultado real da execução, dizer quais hipóteses sobrevivem. | `{sobreviventes:[ids], raciocinio}` |
| `redigir_dica` | Escrever a dica no nível pedido, ancorada nos valores reais, sem vazar solução. | `{texto, nivel, revela_solucao}` |
| `avaliar_resposta` | Feedback curto e ancorado quando o aluno responde a uma PERGUNTA. | `{feedback, compreensao}` |
| `avaliar_explicacao` | **Rubrica** da explicação final do aluno. | `{identificou, causa, correcao, nota, comentario}` |

Os textos completos dos prompts estão em `llm.py` (dicionário `_PROMPTS`).

---

## 9. Modelo do aluno

Quatro dimensões (`modelo_aluno.py`), atualizadas **só com evidência limpa**
(estratégias forçadas por falha de ferramenta, ou ações do próprio agente, não
contam):
1. **Domínio por equívoco** — probabilidade estilo **BKT**. Sobe apenas quando o
   aluno **demonstra** entendimento (rubrica boa), não por passar nos testes.
   Resolver colando + "não sei" **não** infla o domínio.
2. **Habilidade de depuração** — forma hipótese, testa entrada discriminante, lê
   variáveis, localiza antes de editar.
3. **Sinais de interface** — execuções, entradas discriminantes rodadas sozinho
   (sinal-ouro), uso do trace, tempo até a 1ª execução, churn, colagens, pausas.
4. **Qualidade da explicação** — nota geral da rubrica.

Persistência: um JSON por aluno em `arandu-m3/dados_alunos/` (pseudônimo — LGPD).

---

## 10. Verificador

Toda mensagem passa por `verificar()` antes de chegar ao aluno. Barra:
- dicas **sem âncora** de execução (afirmou sem rodar);
- mensagens que **revelariam a solução** (trechos do código de referência, ou um
  bloco de código embutido que passa em todos os testes).

Cutucões socráticos (perguntas/encorajamento) dispensam a âncora, mas o bloqueio
de vazar solução continua valendo.

---

## 11. Como rodar

**Requisitos:** Python 3.10+ e `anthropic` ou `openai` (só para a chave real).

```bash
pip install -r requirements.txt
```

1. `arandu-m1/` (motor M1) e `Arandu-m2/` (dados do M2) devem estar na raiz do
   repositório, ao lado de `arandu-m3/` (já estão).
2. Crie um `.env` na **raiz do repositório** com a sua chave (uma das duas; se
   houver as duas, a Anthropic tem prioridade):
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   # ou: OPENAI_API_KEY=sk-...
   # opcional: modelo (padrão claude-sonnet-5 / gpt-4o)
   ARANDU_MODELO=claude-sonnet-5
   ```
3. Rode o servidor (a partir da raiz):
   ```bash
   py arandu-m3/servidor_web.py            # Windows
   # python3 arandu-m3/servidor_web.py     # Linux/Mac
   ```
4. Abra **http://localhost:8002**.

**Demos isoladas** (rodam sem chave, com o `MockLLM`):
`python3 arandu-m3/demos/demo_tools.py` (idem `demo_treinador`, `demo_sessao`,
`demo_m2`).

**Confirme a versão:** o boot imprime `... [build N · ...]` e o topo da página
mostra o mesmo selo. O Python **não recarrega** arquivos editados — após mudar um
`.py`, **Ctrl+C e rode de novo** (o `.html` pede só um Ctrl+F5).

**Sem a chave:** cai no `MockLLM` (a estrutura roda de graça; a inteligência real
é o LLM). Custo típico com a chave: alguns centavos por sessão.

**Banco de bugs:** padrão = M2 (bugs reais do Refactory). Para os exemplos de
stdin: `ARANDU_BANCO=exemplos py arandu-m3/servidor_web.py`.

---

## 12. Estrutura e arquivos

```
Arandu/
├── README.md               # este arquivo
├── requirements.txt        # dependências (anthropic, openai)
├── .env                    # chave do LLM (não versionado)
├── docs/
│   ├── contexto-projeto-arandu.md  # resumo do contexto do projeto
│   ├── PONTOS-DE-ATENCAO.md        # auditoria para a banca (forças, riscos, plano)
│   ├── PRODUCT.md                  # produto: público, superfícies, restrições
│   └── DESIGN.md                   # sistema visual da interface
├── arandu-m1/              # M1 — motor de execução isolada (subprocesso/sandbox) + servidor MCP/REST
├── Arandu-m2/              # M2 — só os dados de bugs usados entram no repo (o pipeline é offline)
└── arandu-m3/              # M3 — o Treinador (+ a interface web que cumpre o papel do M4)
    ├── servidor_web.py     # ponto de entrada: servidor HTTP + escolha do LLM + selo de build
    ├── sessao.py           # orquestrador: máquina de estados + monitor agêntico + painel
    ├── treinador.py        # o agente: decidir_intervencao(), investigar() (ReAct), intervir()
    ├── modelo_aluno.py     # retrato do aluno (4 dimensões, BKT) + persistência JSON
    ├── verificador.py      # guardrail (exige âncora; barra vazamento da solução)
    ├── llm.py              # porta única do LLM (Anthropic/OpenAI) + MockLLM + TODOS os prompts (_PROMPTS)
    ├── catalogo.py         # catálogo de equívocos (ProgMiscon)
    ├── tools.py            # adaptador M3 ↔ motor do M1 (executar/trace/diff/suíte)
    ├── banco_m2.py         # carrega banco de bugs + variações do M2; estima dificuldade
    ├── validacao_banco.py  # métricas do banco de bugs (revalida as variações)
    ├── registro.py         # gravação de cada sessão (visão do professor)
    ├── config.py           # tetos do laço, cooldown/teto de intervenções, níveis de dica
    ├── log.py              # logging (terminal + logs/arandu.log)
    ├── web/                # interface: aluno (index), painel do agente, visão do professor
    └── demos/              # demonstrações isoladas de cada peça (não fazem parte do servidor)
```

Gerados em runtime dentro de `arandu-m3/` e ignorados no Git: `logs/`,
`dados_alunos/`, `dados_sessoes/`. Também ignorados: `.env`, `__pycache__/`,
`_to_delete/` e o grosso do M2 (mantém-se só `data/bugs/`).

---

## 13. Datasets e limitações

- **ProgMiscon** — catálogo de equívocos (base do `catalogo.py` e das etiquetas).
- **Refactory** — pares (código com bug, código correto) de funções Python de
  iniciantes. Fonte dos bugs reais do M2.
- **CodeBench** — juiz online longitudinal (uso previsto na fase final).

**Segurança:** o M1 executa código não-confiável em **subprocesso isolado**, com
timeout, lista de módulos proibidos e limites de recurso.

**Limitações conhecidas** (detalhe completo em `docs/PONTOS-DE-ATENCAO.md`): o servidor
de demo atende **um aluno por vez** (proposital para a gravação); o comportamento
do agente é não-determinístico (mitigado por guarda-corpos + Verificador); o
modelo do aluno é um protótipo (BKT não calibrado); e o RAG de trajetórias ainda
não está ligado à decisão.

---

*Projeto Arandu — AKCIT Camp 2026 · Trilha Norte / Manaus.*
