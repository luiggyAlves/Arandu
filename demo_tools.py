"""
Demo das ferramentas do Arandu (Contrato A) — sem LLM.
Exercício: contar números PARES. Aluno com bug conta ÍMPARES (condição invertida).
"""

from tools import executar, rodar_suite, analisar

REF = """\
nums = list(map(int, input().split()))
c = 0
for x in nums:
    if x % 2 == 0:
        c += 1
print(c)
"""

ALUNO = """\
nums = list(map(int, input().split()))
c = 0
for x in nums:
    if x % 2 == 1:
        c += 1
print(c)
"""

def h(t): print("\n" + "=" * 68 + "\n" + t + "\n" + "=" * 68)

h("1) rodar_suite no código do ALUNO")
for r in rodar_suite(ALUNO, [{"entrada": "1 2", "esperado": "1"},
                             {"entrada": "2 4 6", "esperado": "3"},
                             {"entrada": "1 2 3 4", "esperado": "2"}]):
    print(f"  [{'OK' if r['passou'] else 'FALHA'}] {r['entrada']!r:10} esperado={r['esperado']} obtido={r['obtido']}")
print("  -> '1 2' passa por coincidência: um teste só não revela o bug.")

h("2) executar (aluno roda uma entrada dele)")
print("  ", executar(ALUNO, "2 4 6"))

h("3) analisar (Contrato A: os DOIS traces + divergência da saída) em '2 4 6'")
a = analisar(ALUNO, REF, "2 4 6")
print("  divergiu?         ", a["divergiu"])
print("  saida_aluno       ", a["saida_aluno"].strip())
print("  saida_ref         ", a["saida_ref"].strip())
print("  divergencia_saida ", a["divergencia_saida"])
print("  trace_aluno (fim):", a["trace_aluno"][-2:])
print("  trace_ref  (fim):", a["trace_ref"][-2:])
print("  -> o agente recebe os dois traces e a divergência da saída para raciocinar.")
