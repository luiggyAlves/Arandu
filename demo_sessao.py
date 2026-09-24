"""
Demo do MOTOR DA SESSÃO de ponta a ponta, com um "aluno simulado" (sem API).
Mostra a máquina de estados inteira: escolher bug -> aluno testa -> pede dica ->
submete correção -> explica -> resolvido -> encerra.

A interface real (M4) faria exatamente estas mesmas chamadas a processar_evento().
"""

import os
from llm import MockLLM, OpenAILLM
from treinador import Treinador
from sessao import Sessao


def escolher_llm():
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAILLM("gpt-4o-mini")
    return MockLLM()

# ---- Banco de bugs de exemplo (viria do M2) ----
COD_REF = """\
nums = list(map(int, input().split()))
c = 0
for x in nums:
    if x % 2 == 0:
        c += 1
print(c)
"""
COD_BUGADO = """\
nums = list(map(int, input().split()))
c = 0
for x in nums:
    if x % 2 == 1:
        c += 1
print(c)
"""
BANCO = [{
    "id": "bug_pares_01",
    "equivoco": "CondicaoInvertida",
    "dificuldade": 2,
    "enunciado": "Conte quantos números pares há na linha.",
    "cod_bugado": COD_BUGADO,
    "cod_ref": COD_REF,
    "testes": [{"entrada": "1 2", "esperado": "1"},
               {"entrada": "2 4 6", "esperado": "3"},
               {"entrada": "1 2 3 4", "esperado": "2"}],
}]


def mostrar(titulo, resp):
    print(f"\n>>> {titulo}")
    for k, v in resp.items():
        print(f"      {k}: {v}")


sessao = Sessao(id_aluno="aluno_sessao", banco=BANCO, treinador=Treinador(escolher_llm()))

print("=" * 70)
print("SESSÃO DE TREINO — aluno simulado")
print("=" * 70)

mostrar("iniciar()", sessao.iniciar())

# 1. aluno testa uma entrada DISCRIMINANTE por conta própria (sinal-ouro)
mostrar("evento: rodou_entrada '2 4 6'",
        sessao.processar_evento({"tipo": "rodou_entrada", "dados": {"entrada": "2 4 6"}}))

# 2. aluno pede dica
mostrar("evento: pediu_dica",
        sessao.processar_evento({"tipo": "pediu_dica"}))

# 3. aluno submete uma correção AINDA errada
COD_ERRADO2 = COD_BUGADO.replace("== 1", "> 10")  # ainda não conta pares
mostrar("evento: submeteu_correcao (ainda errada)",
        sessao.processar_evento({"tipo": "submeteu_correcao", "dados": {"codigo": COD_ERRADO2}}))

# 4. aluno submete a correção CERTA
mostrar("evento: submeteu_correcao (correta)",
        sessao.processar_evento({"tipo": "submeteu_correcao", "dados": {"codigo": COD_REF}}))

# 5. aluno explica o erro
mostrar("evento: explicou",
        sessao.processar_evento({"tipo": "explicou",
                                 "dados": {"texto": "eu tinha invertido a condição, estava contando os ímpares"}}))

print("\n" + "=" * 70)
print("MODELO DO ALUNO ao fim da sessão")
print("=" * 70)
print("  domínio por equívoco:", sessao.modelo.dominio_por_equivoco)
print("  depuração           :", sessao.modelo.depuracao)
print("  sinais interface    :", sessao.modelo.sinais_interface)
print("  bugs resolvidos     :", sessao.modelo.bugs_resolvidos)
print("  explicação (0..1)   :", sessao.modelo.explicacao_qualidade)
