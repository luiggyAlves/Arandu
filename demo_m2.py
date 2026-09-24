"""
Demo da integração do M2 (banco de bugs real) com o M3 + M1.
Roda sem chave (MockLLM) — valida o encaixe (loader, modo 'chamada', suite,
RAG Fonte A, sessão completa). Com OPENAI_API_KEY, usa gpt-4o-mini de verdade.
"""

import os
import tools
from banco_m2 import carregar_banco, carregar_trajetorias, recuperar_trajetorias
from llm import MockLLM, OpenAILLM
from treinador import Treinador
from sessao import Sessao

AQUI = os.path.dirname(os.path.abspath(__file__))
BANCO_JSON = os.path.join(AQUI, "Arandu-m2", "Mod2", "data", "bugs", "banco_de_bugs.json")
TRAJ_JSON = os.path.join(AQUI, "Arandu-m2", "Mod2", "data", "bugs", "loja_trajetorias.json")


def h(t): print("\n" + "=" * 68 + "\n" + t + "\n" + "=" * 68)


banco = carregar_banco(BANCO_JSON)
h(f"Banco do M2 carregado: {len(banco)} bugs")
for b in banco:
    print(f'  - {b["id"]:16} {b["equivoco"]:24} modo={b["modo"]} ({len(b["testes"])} testes)')

bug0 = banco[0]
h(f"rodar_suite no código BUGADO de {bug0['id']} (deve falhar em algum)")
for r in tools.rodar_suite(bug0["cod_bugado"], bug0["testes"])[:5]:
    print(f'  [{"OK  " if r["passou"] else "FALHA"}] {r["entrada"]:34} esperado={r["esperado"]:>4}  obtido={r["obtido"]:>6}')

h("executar a REFERÊNCIA numa chamada de função")
print("  ", tools.executar(bug0["cod_ref"], chamada=bug0["testes"][0]["chamada"]))

h("RAG (Fonte A): loja de trajetórias do M2")
traj = carregar_trajetorias(TRAJ_JSON)
print(f"  {len(traj)} trajetórias na loja; do equívoco '{bug0['equivoco']}':",
      len(recuperar_trajetorias(traj, bug0["equivoco"])))

h("Sessão completa (aluno simulado)")
llm = OpenAILLM("gpt-4o-mini") if os.environ.get("OPENAI_API_KEY") else MockLLM()
print("  LLM:", type(llm).__name__)
s = Sessao(id_aluno="aluno_m2_demo", banco=banco, treinador=Treinador(llm))
r = s.iniciar()
escolhido = next(b for b in banco if b["id"] == r["bug"]["id"])
print("  bug escolhido:", escolhido["id"], "|", escolhido["equivoco"])
d = s.processar_evento({"tipo": "pediu_dica", "dados": {"codigo": escolhido["cod_bugado"]}})
print("  dica:", (d.get("mensagem") or "")[:90], "…")
sub = s.processar_evento({"tipo": "submeteu_correcao", "dados": {"codigo": escolhido["cod_ref"]}})
print("  submeteu correção:", sub["resposta"])
exp = s.processar_evento({"tipo": "explicou",
                          "dados": {"texto": "eu tratei o caso vazio errado; a condição não refletia o que eu queria contar"}})
print("  explicou -> feedback:", exp.get("feedback_explicacao"), "| qualidade:", s.modelo.explicacao_qualidade)
print("  domínio agora:", s.modelo.dominio_por_equivoco)
