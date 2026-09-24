# Contrato A: ferramentas de execução (entregue pelo M1)

Proposta para travar no Dia 0. As ferramentas **já funcionam** (não são mock): M2, M3 e M4 podem usá-las
desde agora. Os exemplos abaixo são saídas reais. A fonte da verdade em código é
[`arandu_motor/contrato.py`](arandu_motor/contrato.py). O servidor MCP também publica esses formatos
como `outputSchema` de cada ferramenta.

## Convenções (valem para todas)

- **Dois jeitos de alimentar o programa**
  - `entrada`: texto do stdin, o que o `input()` lê (estilo juiz online / CodeBench). Ex.: `"5\n"`.
  - `chamada`: código rodado **depois** do programa, para exercícios de função (estilo Refactory).
    Ex.: `"search(42, (-5, 1, 3, 5, 7, 10))"`. O valor da última expressão é impresso, como no Refactory.
- **Valores de variáveis** vêm como `repr` do Python, em texto: `"5"`, `"'Ana'"`, `"[1, 2]"`. Assim `5` e `"5"` não se confundem.
  Para ter o valor de volta em Python: `ast.literal_eval`.
- **Cada passo do trace é uma linha que rodou e o estado DEPOIS dela.**
  `{"linha": 3, "codigo": "b = a + 1", "variaveis": {"a": "1", "b": "2"}}` quer dizer "a linha 3 (`b = a + 1`) rodou e,
  depois dela, a vale 1 e b vale 2". `funcao`, `imprimiu`, `retornou` e `erro` só aparecem quando acontecem.
- **Erros**: `erro` traz a mensagem com o tipo e a linha (`"ZeroDivisionError: division by zero (linha 3)"`). No
  `executar` vêm também separados, em `tipo_erro` e `linha_erro`. Tipos próprios do sandbox:
  - `LimiteDeLinhas` / `LimiteDeTempo`: provável laço infinito (`linha_erro` diz onde ele estava);
  - `LimiteDeSaida`: imprimiu demais;
  - `ImportError` / `PermissionError`: o sandbox barrou um módulo ou operação (`os`, arquivos, rede...).
- **Comparação de saída** (`rodar_suite`): ignora espaços no fim das linhas e linhas vazias no final.

## 1. `executar(codigo, entrada="", chamada=None)`

```json
{
  "saida": "10",
  "erro": null,
  "tipo_erro": null,
  "linha_erro": null,
  "tempo_ms": 0.3,
  "linhas_executadas": 17
}
```

Laço infinito:

```json
{
  "saida": "",
  "erro": "Limite de 3.000.000 linhas executadas atingido -- provável laço infinito (linha 3)",
  "tipo_erro": "LimiteDeLinhas",
  "linha_erro": 3,
  "tempo_ms": 512.4,
  "linhas_executadas": 3000001
}
```

## 2. `trace(codigo, entrada="", chamada=None, max_passos=None, linhas=None)`

Formato limpo, pensado para uma LLM ler: `saida`, `erro` e `trace`. Cada passo traz:
- `linha` e `codigo` (o texto da linha);
- `variaveis`, com os valores depois da linha;
- `funcao`, só dentro de uma função;
- `imprimiu`, `retornou` e `erro`, só quando acontecem.

`truncado: true` aparece só quando o trace foi cortado. `max_passos` é 500 por padrão; no MCP, é 200, para não
lotar o contexto do agente. `linhas=[5]` grava só os passos da linha 5. Tempo de execução e contagem de linhas
ficam no `executar`.

```python
def dobro(x):
    return 2 * x

d = dobro(4)
print(d)
```

```json
{
  "saida": "8",
  "erro": null,
  "trace": [
    {"linha": 1, "codigo": "def dobro(x):", "variaveis": {}},
    {"linha": 2, "codigo": "return 2 * x", "funcao": "dobro", "variaveis": {"x": "4"}, "retornou": "8"},
    {"linha": 4, "codigo": "d = dobro(4)", "variaveis": {"d": "8"}},
    {"linha": 5, "codigo": "print(d)", "variaveis": {"d": "8"}, "imprimiu": "8"}
  ]
}
```

## 3. `rodar_suite(codigo, testes)`

`testes` usa o mesmo formato do Contrato B: `[{id?, entrada?, chamada?, saida_esperada}]`.
Teste com erro de execução não passa. Exemplo abreviado: 5 testes, 2 mostrados.

```json
{
  "resultados": [
    {"teste_id": "t1", "passou": true,  "esperado": "reprovado", "obtido": "reprovado",   "erro": null},
    {"teste_id": "t5", "passou": false, "esperado": "aprovado",  "obtido": "recuperação", "erro": null}
  ],
  "aprovados": 4,
  "total": 5
}
```

## 4. `diff_comportamental(codigo_aluno, codigo_ref, entrada="", chamada=None, id_chamada=None)`

É a ferramenta que o M3 chama para testar as hipóteses dele. **O M3 escolhe a entrada** e o M1 roda o código do
aluno e o de referência com ela. O M1 devolve os fatos e **não interpreta**: quem conclui qual hipótese é
verdadeira é o M3.

A resposta tem três partes:

- `divergiu`: `true` se a saída ou o erro final forem diferentes;
- `aluno` e `referencia`: saída, erro e **trace completo** de cada código, no mesmo formato limpo do `trace`.
  Vêm sempre, tenha divergido ou não;
- `id_chamada`: opcional. O M3 manda um identificador (ex.: da hipótese testada) e ele volta igual na resposta.

Exemplo real. Aluno com as condições trocadas (`if nota >= 5` antes de `nota >= 7`), entrada `9`:

```json
{
  "id_chamada": "H1",
  "divergiu": true,
  "aluno": {
    "saida": "recuperação",
    "erro": null,
    "trace": [
      {"linha": 1, "codigo": "nota = int(input())", "variaveis": {"nota": "9"}},
      {"linha": 2, "codigo": "if nota >= 5:", "variaveis": {"nota": "9"}},
      {"linha": 3, "codigo": "print(\"recuperação\")", "variaveis": {"nota": "9"}, "imprimiu": "recuperação"}
    ]
  },
  "referencia": {
    "saida": "aprovado",
    "erro": null,
    "trace": [
      {"linha": 1, "codigo": "nota = int(input())", "variaveis": {"nota": "9"}},
      {"linha": 2, "codigo": "if nota >= 7:", "variaveis": {"nota": "9"}},
      {"linha": 3, "codigo": "print(\"aprovado\")", "variaveis": {"nota": "9"}, "imprimiu": "aprovado"}
    ]
  }
}
```

Quando o M3 não chega a uma conclusão, ele já tem o trace dos dois códigos nesta mesma resposta. Se quiser o
trace de um código só, com filtro de linhas, pode usar `trace`.

O trace de cada lado grava até `max_passos` passos, definido na seção `[limites_diff]` do `m1.config`. Se o
programa passar disso (um laço infinito, por exemplo), vem `truncado: true`.

## Quem faz o quê

Registrado também no `m1.config`, na seção `[fronteiras]`:

- O **M3** levanta as hipóteses, escolhe a entrada, chama `diff_comportamental` e conclui qual hipótese é verdadeira.
- O **M1** só executa e relata: divergiu, saídas e traces. Não analisa os traces.

## Mudanças em relação ao documento v1 (para discutir)

1. **As saídas são sempre objetos.** O MCP exige objeto no resultado estruturado, então `trace` virou
   `{passos: [...], ...}` e `rodar_suite` virou `{resultados: [...], aprovados, total}`.
2. **`chamada` além de `entrada`**, para rodar os testes do Refactory sem conversão. O item de teste do
   Contrato B ganha o campo opcional `chamada`.
3. **`diff_comportamental` devolve `divergiu`, as saídas e o trace dos dois códigos** (combinado com o M3). Ele
   não aponta mais a linha/variáveis da divergência: analisar os traces é trabalho do Treinador (M3).
4. **`gerar_entrada_discriminante` saiu do M1**: escolher a entrada a partir das hipóteses é trabalho do M3.

## Nota para o M2: testes do Refactory

Para cada `ans/input_XXX.txt` e `ans/output_XXX.txt` de uma questão:

- `chamada` = conteúdo de `input_XXX.txt` (ex.: `search(42, (-5, 1, 3, 5, 7, 10))`);
- `saida_esperada` = `str(eval(conteúdo de output_XXX.txt))`, que é o que o próprio Refactory compara;
- se a questão tem `code/global.py`, ponha o conteúdo dele no começo da `chamada`.

O Validador do laço Construtor↔Validador pode usar o `rodar_suite` direto: o bug precisa falhar em pelo menos
um teste, sem `LimiteDeLinhas`/`LimiteDeTempo`, e a referência precisa passar em todos.
