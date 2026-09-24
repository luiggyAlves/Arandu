"""O que o M1 devolve quando o M3 manda uma entrada para testar.

O M3 (Treinador) tem as hipóteses dele e escolhe uma entrada. O M1 só roda o
código do aluno e o de referência com essa entrada e devolve o que aconteceu.
Quem conclui qual hipótese é verdadeira é o M3.

    python exemplos/exemplo_diff.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from arandu_motor import diff_comportamental  # noqa: E402

REFERENCIA = """\
nota = int(input())
if nota >= 7:
    print("aprovado")
elif nota >= 5:
    print("recuperação")
else:
    print("reprovado")
"""

ALUNO = """\
nota = int(input())
if nota >= 5:
    print("recuperação")
elif nota >= 7:
    print("aprovado")
else:
    print("reprovado")
"""


def mostrar(entrada: str) -> None:
    print(f"\n=== O M3 manda a entrada {entrada.strip()!r}")
    r = diff_comportamental(ALUNO, REFERENCIA, entrada, id_chamada="exemplo")
    print(f"divergiu: {r['divergiu']}")
    print(f"saída do aluno = {r['aluno']['saida']!r}  |  saída da referência = {r['referencia']['saida']!r}")
    for lado in ("aluno", "referencia"):
        print(f"trace ({lado}):")
        for p in r[lado]["trace"]:
            extra = f"  imprimiu {p['imprimiu']!r}" if "imprimiu" in p else ""
            print(f"   linha {p['linha']}  {p['codigo']:<24} {p['variaveis']}{extra}")


if __name__ == "__main__":
    mostrar("3\n")  # os dois imprimem "reprovado": não divergem
    mostrar("9\n")  # divergem
    if "--json" in sys.argv:
        print(json.dumps(diff_comportamental(ALUNO, REFERENCIA, "9\n"), ensure_ascii=False, indent=2))
