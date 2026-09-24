# M1 → M3: como usar o motor de execução

## Quem faz o quê

- **M3 (Treinador):** levanta as hipóteses, escolhe a entrada, chama o M1, analisa os traces e conclui.
- **M1 (motor):** roda o código do aluno e o de referência com a entrada recebida e devolve os fatos: se
  divergiram, a saída de cada um e o trace de cada um. O M1 não interpreta nada e não usa LLM.

## 1. Instalar e subir (uma vez)

Precisa de Python 3.10 ou mais novo. Na pasta do projeto:

```bash
python -m venv C:\venvs\arandu-m1
C:\venvs\arandu-m1\Scripts\activate
pip install -e .
```

Se o projeto estiver no OneDrive, deixe o venv fora dele, como acima.

## 2. Conectar (escolha um jeito)

**a) MCP por stdio.** O seu cliente sobe o servidor sozinho. Configuração no formato mais comum (Claude Agent SDK,
Claude Desktop e a maioria dos clientes MCP):

```json
{
  "mcpServers": {
    "arandu-motor": {
      "command": "C:\\venvs\\arandu-m1\\Scripts\\python.exe",
      "args": ["-m", "arandu_motor"]
    }
  }
}
```

**b) MCP por HTTP.** Rode `python -m arandu_motor --http` e conecte em `http://127.0.0.1:8000/mcp`. Para usar o
servidor rodando na máquina de outra pessoa da equipe, ela roda `python -m arandu_motor --http --host 0.0.0.0` e
você usa `http://<IP dela>:8000/mcp`.

**c) Python direto, sem MCP:**

```python
from arandu_motor import diff_comportamental, trace, executar, rodar_suite
```

Há um exemplo de cliente MCP pronto em `exemplos/cliente_mcp.py`.

## 3. A ferramenta principal: `diff_comportamental`

**Você manda:**

| Parâmetro | O que é |
|---|---|
| `codigo_aluno` | código do aluno (texto) |
| `codigo_ref` | código de referência (texto) |
| `entrada` | o que o `input()` lê, ex.: `"9"`. Várias linhas: separe com `\n` |
| `chamada` | opcional, só para exercícios de função (estilo Refactory), ex.: `"search(5, (1, 5, 9))"` |
| `id_chamada` | opcional, ex.: `"H1"`. Volta igual na resposta, para você saber a que hipótese ela se refere |

**Você recebe** (exemplo real: aluno com o `if`/`elif` das notas trocado, entrada `9`):

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

## 4. Como ler o trace

- **`divergiu`:** `true` quando a saída ou o erro final dos dois códigos são diferentes. O trace vem **sempre**,
  mesmo quando `divergiu` é `false`.
- **Cada passo:** uma linha que rodou (`linha` e o texto dela em `codigo`) e o valor das variáveis **depois**
  dessa linha.
- **Campos que só aparecem quando acontecem:**
  - `funcao`: o passo está dentro de uma função;
  - `imprimiu`: a linha imprimiu algo;
  - `retornou`: a linha é um `return`;
  - `erro`: a linha levantou uma exceção.
- **Valores** vêm como o Python mostra, em texto: `"9"` é o número 9, `"'9'"` é o texto "9" e `"[1, 2]"` é uma lista.
- **`erro`** (do programa) vem como texto, ex.: `"ZeroDivisionError: division by zero (linha 3)"`, ou `null`.
- **Laço infinito:** o programa é interrompido, `erro` diz `"...provável laço infinito (linha N)"` e aparece
  `"truncado": true`.
- **`else:` e `def`** às vezes não aparecem como passo próprio. É assim que o Python executa, não é falha.

## 5. As outras ferramentas (se precisar)

- **`trace(codigo, entrada)`:** o mesmo trace, de um código só. Aceita `linhas=[5]` para gravar só a linha 5.
- **`executar(codigo, entrada)`:** só roda. Devolve `saida`, `erro` e `tempo_ms`.
- **`rodar_suite(codigo, testes)`:** roda os testes do bug (`[{"entrada": "3", "saida_esperada": "6"}]`) e diz
  quais passaram.

O formato completo de todas está no `CONTRATO_A.md`.

## 6. Para confirmar comigo

1. O `id_chamada` é o que você queria com "chamada identificada"?
2. O formato do trace está bom para a sua LLM, ou prefere algum campo diferente?
