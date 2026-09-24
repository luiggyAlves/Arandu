"""Exemplo para o M3: conectar ao servidor do M1 por MCP e usar as ferramentas.

    python exemplos/cliente_mcp.py                              # sobe o servidor por stdio
    python exemplos/cliente_mcp.py http://127.0.0.1:8000/mcp    # usa um servidor HTTP já no ar

Qualquer cliente MCP serve (Claude Agent SDK, LangChain/LangGraph com
adaptadores MCP, etc.); aqui é o cliente do próprio SDK `mcp`.
"""

import json
import sys
from pathlib import Path

import anyio
from mcp import Client, StdioServerParameters

RAIZ = Path(__file__).resolve().parent.parent

ALUNO = """\
n = int(input())
soma = 0
i = 1
while i < n:
    soma = soma + i
    i = i + 1
print(soma)
"""
REFERENCIA = ALUNO.replace("i < n", "i <= n")


async def main(url: str | None) -> None:
    servidor = url or StdioServerParameters(command=sys.executable, args=["-m", "arandu_motor"], cwd=str(RAIZ))
    async with Client(servidor) as cliente:
        ferramentas = await cliente.list_tools()
        print("Ferramentas:", ", ".join(f.name for f in ferramentas.tools))

        # O M3 escolheu a entrada "5" a partir das hipóteses dele e manda para o M1:
        resultado = await cliente.call_tool("diff_comportamental", {
            "codigo_aluno": ALUNO,
            "codigo_ref": REFERENCIA,
            "entrada": "5\n",
            "id_chamada": "hipotese-1",
        })
        r = resultado.structured_content
        print(f"\ndivergiu={r['divergiu']}  aluno={r['aluno']['saida']!r}  "
              f"referencia={r['referencia']['saida']!r}  id={r['id_chamada']}")
        print("trace do aluno (linha 4):", [p["variaveis"] for p in r["aluno"]["trace"] if p["linha"] == 4])
        print("\nresposta completa:", json.dumps(r, ensure_ascii=False)[:300], "...")


if __name__ == "__main__":
    anyio.run(main, sys.argv[1] if len(sys.argv) > 1 else None)
