"""
Demo do Treinador de ponta a ponta — SEM chave de API (usa o MockLLM).
As ferramentas rodam DE VERDADE; só o raciocínio do LLM é roteirizado.

Cenário: bug "contar pares". O aluno está com um código que conta ÍMPARES
(condição invertida). Ele pediu uma dica. O Treinador investiga, prova por
execução qual é o equívoco, redige a dica, o Verificador aprova, e o modelo
do aluno é atualizado.
"""

import os
from llm import MockLLM, OpenAILLM
from treinador import Treinador
from modelo_aluno import ModeloAluno


def escolher_llm():
    """Se houver OPENAI_API_KEY, usa gpt-4o-mini; senão, o mock (roda sem chave)."""
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAILLM("gpt-4o-mini"), "OpenAILLM(gpt-4o-mini)"
    return MockLLM(), "MockLLM (sem chave)"

COD_ALUNO = """\
nums = list(map(int, input().split()))
c = 0
for x in nums:
    if x % 2 == 1:      # BUG: conta ímpares
        c += 1
print(c)
"""

COD_REF = """\
nums = list(map(int, input().split()))
c = 0
for x in nums:
    if x % 2 == 0:
        c += 1
print(c)
"""

TESTES = [
    {"entrada": "1 2", "esperado": "1"},
    {"entrada": "2 4 6", "esperado": "3"},
    {"entrada": "1 2 3 4", "esperado": "2"},
]


def h(t): print("\n" + "=" * 70 + "\n" + t + "\n" + "=" * 70)


llm_obj, nome_llm = escolher_llm()
treinador = Treinador(llm_obj)
modelo = ModeloAluno(id_aluno="aluno_demo")

h("O aluno pediu uma dica. Treinador vai INTERVIR (investigar -> redigir -> verificar).")

res = treinador.intervir(
    cod_aluno=COD_ALUNO, cod_ref=COD_REF,
    entrada_falha="2 4 6", testes=TESTES, nivel_inicial=3,
)

h("Log do laço investigativo (o que o agente pensou e rodou)")
for passo in res["investigacao"]["log"]:
    print("  ", passo)

inv = res["investigacao"]
print("\n  conclusivo?      ", inv["conclusivo"])
print("  equívoco achado: ", inv["equivoco"])
print("  âncoras (execuções reais que sustentam a dica):")
for a in inv["ancoras"]:
    print("     ", a)

h("Dica proposta -> Verificador")
print("  texto :", res["envelope"]["texto"])
print("  nível :", res["envelope"]["nivel"])
print("  veredito do Verificador:", res["veredito"])
print("  rejeições até aprovar   :", res["rejeicoes"])

h("Teste do guardrail: e se a dica ENTREGASSE a solução?")
from verificador import verificar
envelope_ruim = {
    "texto": "É só trocar a condição. Cole isto:\n```python\n" + COD_REF + "```",
    "nivel": 5, "revela_solucao": False,
    "ancoras": [{"entrada": "2 4 6"}],
}
print("  veredito:", verificar(envelope_ruim, COD_REF, TESTES))

h("Atualização do modelo do aluno (só com evidência limpa)")
# aluno ainda NÃO resolveu (pediu dica) -> registramos que o equívoco está fraco
eq = inv["equivoco"]["equivoco"] if inv["equivoco"] else "CondicaoInvertida"
modelo.registrar_conceitual(eq, acertou=False)
# a interface reportou que ele rodou sozinho uma entrada discriminante -> OURO
modelo.registrar_depuracao({"testa_entrada_discriminante": True, "le_variaveis": True})
modelo.registrar_sinais_interface({"num_execucoes": 3, "usou_trace": True})
print("  domínio no equívoco:", modelo.dominio_por_equivoco)
print("  depuração          :", modelo.depuracao)
print("  sinais interface   :", modelo.sinais_interface)

modelo.salvar()
print("\n  modelo salvo em dados_alunos/aluno_demo.json")
print(f"\nLLM usado: {nome_llm}.  (defina OPENAI_API_KEY para usar o gpt-4o-mini real)")
