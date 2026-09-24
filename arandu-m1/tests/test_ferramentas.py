"""Testes das ferramentas do M1, com os cenários do documento de arquitetura."""

import pytest

from arandu_motor import Limites, diff_comportamental, executar, rodar_suite, trace

# "Soma de 1 até n" -- o erro de condição de parada da Marina.
SOMA_REF = """\
n = int(input())
soma = 0
i = 1
while i <= n:
    soma = soma + i
    i = i + 1
print(soma)
"""
SOMA_BUG = SOMA_REF.replace("i <= n", "i < n")

# Classificar a nota: o aluno inverteu a ordem das condições. Passa em 4 de 5.
NOTA_REF = """\
nota = int(input())
if nota >= 7:
    print("aprovado")
elif nota >= 5:
    print("recuperação")
else:
    print("reprovado")
"""
NOTA_BUG = """\
nota = int(input())
if nota >= 5:
    print("recuperação")
elif nota >= 7:
    print("aprovado")
else:
    print("reprovado")
"""
TESTES_NOTA = [
    {"id": "t1", "entrada": "3\n", "saida_esperada": "reprovado"},
    {"id": "t2", "entrada": "0\n", "saida_esperada": "reprovado"},
    {"id": "t3", "entrada": "5\n", "saida_esperada": "recuperação"},
    {"id": "t4", "entrada": "6\n", "saida_esperada": "recuperação"},
    {"id": "t5", "entrada": "8\n", "saida_esperada": "aprovado"},
]

# Estilo Refactory (questão 1): funções, testadas por chamada.
SEARCH_REF = """\
def search(x, seq):
    for i, v in enumerate(seq):
        if x <= v:
            return i
    return len(seq)
"""
SEARCH_BUG = SEARCH_REF.replace("x <= v", "x < v")


# ---- executar ---------------------------------------------------------------


def test_executar_le_entrada_e_imprime():
    r = executar(SOMA_REF, "5\n")
    assert r["saida"] == "15"
    assert r["erro"] is None
    assert r["tempo_ms"] >= 0


def test_executar_texto_com_acento():
    assert executar('print("recuperação")')["saida"] == "recuperação"


def test_executar_erro_traz_tipo_e_linha():
    r = executar("x = 1\ny = 0\nprint(x / y)\n")
    assert r["tipo_erro"] == "ZeroDivisionError"
    assert r["linha_erro"] == 3
    assert r["erro"] == "ZeroDivisionError: division by zero (linha 3)"


def test_executar_erro_de_sintaxe():
    r = executar("if True\n    print(1)\n")
    assert r["tipo_erro"] == "SyntaxError"
    assert r["linha_erro"] == 1


def test_executar_input_alem_da_entrada():
    assert executar("a = input()\nb = input()\n", "só uma linha\n")["tipo_erro"] == "EOFError"


def test_laco_infinito_para_e_aponta_a_linha():
    r = executar("i = 0\nwhile i < 10:\n    i = i * 1\n", limites=Limites(max_linhas=50_000))
    assert r["tipo_erro"] == "LimiteDeLinhas"
    assert r["linha_erro"] in (2, 3)


def test_programa_parado_estoura_o_tempo_sem_derrubar_os_outros():
    r = executar("import time\ntime.sleep(30)\n", limites=Limites(tempo_s=1))
    assert r["tipo_erro"] == "LimiteDeTempo"
    assert executar("print('ok')")["saida"] == "ok"


def test_saida_gigante_e_cortada():
    r = executar("while True:\n    print('spam')\n", limites=Limites(max_saida=1_000))
    assert r["tipo_erro"] == "LimiteDeSaida"
    assert r["saida"].startswith("spam") and len(r["saida"]) <= 1_000


def test_exit_encerra_normalmente():
    r = executar("print('a')\nexit()\nprint('b')\n")
    assert (r["saida"], r["erro"]) == ("a", None)


@pytest.mark.parametrize("codigo, tipo", [
    ("import os\nos.getcwd()", "ImportError"),
    ("import subprocess", "ImportError"),
    ("open('arquivo.txt', 'w').write('oi')", "PermissionError"),
    ("open('C:/Windows/win.ini').read()", "PermissionError"),
    ("import sys\nsys.modules['os'].system('echo oi')", "PermissionError"),
    ("__import__('socket')", "ImportError"),
])
def test_sandbox_barra_operacoes_perigosas(codigo, tipo):
    assert executar(codigo)["tipo_erro"] == tipo


def test_modulos_comuns_funcionam():
    codigo = (
        "import math, random, collections, itertools, datetime, statistics\n"
        "print(math.sqrt(16), statistics.mean([1, 2, 3]))\n"
        "print(datetime.datetime.strptime('26/09/2026', '%d/%m/%Y').year)\n"
    )
    r = executar(codigo)
    assert r["erro"] is None, r["erro"]
    assert r["saida"] == "4.0 2\n2026"


def test_random_e_deterministico():
    codigo = "import random\nprint(random.randint(1, 1000))"
    assert executar(codigo)["saida"] == executar(codigo)["saida"]


def test_chamada_estilo_refactory():
    assert executar(SEARCH_REF, chamada="search(42, (-5, 1, 3, 5, 7, 10))")["saida"] == "6"
    # com print() explícito, não imprime duas vezes
    assert executar(SEARCH_REF, chamada="print(search(0, (1, 2)))")["saida"] == "0"
    # preâmbulo (ex.: o global.py do Refactory) antes da chamada
    assert executar(SEARCH_REF, chamada="limite = 3\nprint('prep')\nsearch(limite, (1, 5))")["saida"] == "prep\n1"


def test_chamada_de_funcao_inexistente():
    r = executar("def serch(x, seq):\n    return 0\n", chamada="search(1, (1,))")
    assert r["tipo_erro"] == "NameError"
    assert r["erro"].endswith("(na chamada)")


# ---- trace ----------------------------------------------------------------------


def test_trace_formato_limpo():
    r = trace("a = 1\nb = a + 1\nprint(b)\n")
    assert r == {
        "saida": "2",
        "erro": None,
        "trace": [
            {"linha": 1, "codigo": "a = 1", "variaveis": {"a": "1"}},
            {"linha": 2, "codigo": "b = a + 1", "variaveis": {"a": "1", "b": "2"}},
            {"linha": 3, "codigo": "print(b)", "variaveis": {"a": "1", "b": "2"}, "imprimiu": "2"},
        ],
    }


def test_trace_de_funcao_mostra_nome_e_retorno():
    r = trace(SEARCH_REF, chamada="search(5, (1, 5, 9))")
    retorno = [p for p in r["trace"] if "retornou" in p]
    assert retorno[0]["funcao"] == "search"
    assert retorno[0]["retornou"] == "1"
    assert retorno[0]["codigo"] == "return i"


def test_trace_recursao():
    r = trace("def fat(n):\n    if n <= 1:\n        return 1\n    return n * fat(n - 1)\nprint(fat(3))\n")
    retornos = [(p["variaveis"]["n"], p["retornou"]) for p in r["trace"] if "retornou" in p]
    assert retornos == [("1", "1"), ("2", "2"), ("3", "6")]
    assert "funcao" not in r["trace"][-1]  # programa principal


def test_trace_valores_sao_repr():
    r = trace("nome = 'Ana'\nlista = [1, 2]\nd = {'b': 1, 'a': 2}\n")
    assert r["trace"][-1]["variaveis"] == {"nome": "'Ana'", "lista": "[1, 2]", "d": "{'b': 1, 'a': 2}"}


def test_trace_filtra_linhas():
    r = trace(SOMA_REF, "3\n", linhas=[5])
    assert {p["codigo"] for p in r["trace"]} == {"soma = soma + i"}
    assert [p["variaveis"]["soma"] for p in r["trace"]] == ["1", "3", "6"]


def test_trace_de_laco_infinito_vem_truncado():
    r = trace("i = 0\nwhile True:\n    i = i + 1\n", max_passos=50, limites=Limites(max_linhas=10_000))
    assert r["truncado"] is True
    assert len(r["trace"]) == 50
    assert r["erro"].startswith("Limite de")


def test_trace_marca_erro_na_linha():
    r = trace("x = [1]\ny = x[5]\n")
    assert r["trace"][-1]["codigo"] == "y = x[5]"
    assert r["trace"][-1]["erro"].startswith("IndexError")


# ---- rodar_suite --------------------------------------------------------------


def test_suite_passa_4_de_5():
    r = rodar_suite(NOTA_BUG, TESTES_NOTA)
    assert (r["aprovados"], r["total"]) == (4, 5)
    falhou = [t for t in r["resultados"] if not t["passou"]]
    assert [(t["teste_id"], t["obtido"]) for t in falhou] == [("t5", "recuperação")]


def test_suite_com_chamada_e_dicionario_fora_de_ordem():
    testes = [{"chamada": "search(42, (-5, 1, 3, 5, 7, 10))", "saida_esperada": "6"}]
    assert rodar_suite(SEARCH_REF, testes)["aprovados"] == 1
    conjunto = [{"chamada": "f()", "saida_esperada": "{3, 1, 2}"}]
    assert rodar_suite("def f():\n    return {1, 2, 3}\n", conjunto)["aprovados"] == 1


def test_suite_teste_com_erro_nao_passa():
    r = rodar_suite("print(1/0)", [{"saida_esperada": ""}])
    assert r["resultados"][0]["passou"] is False
    assert r["resultados"][0]["erro"].startswith("ZeroDivisionError")


# ---- diff_comportamental -------------------------------------------------------
# O M3 escolhe a entrada (a partir das hipóteses dele); o M1 roda os dois códigos
# e devolve divergiu, as saídas e o trace de cada um.


def test_diff_devolve_divergiu_saidas_e_trace():
    d = diff_comportamental(NOTA_BUG, NOTA_REF, "9\n")
    assert d["divergiu"] is True
    assert d["aluno"]["saida"] == "recuperação"
    assert d["referencia"]["saida"] == "aprovado"
    assert [p["codigo"] for p in d["aluno"]["trace"]] == ["nota = int(input())", "if nota >= 5:",
                                                         'print("recuperação")']
    assert [p["codigo"] for p in d["referencia"]["trace"]] == ["nota = int(input())", "if nota >= 7:",
                                                              'print("aprovado")']
    assert d["aluno"]["trace"][-1]["imprimiu"] == "recuperação"


def test_diff_sem_divergencia_ainda_devolve_o_trace():
    d = diff_comportamental(NOTA_BUG, NOTA_REF, "3\n")  # nessa entrada os dois imprimem "reprovado"
    assert d["divergiu"] is False
    assert d["aluno"]["saida"] == d["referencia"]["saida"] == "reprovado"
    assert d["aluno"]["trace"] and d["referencia"]["trace"]


def test_diff_devolve_o_id_da_chamada():
    assert diff_comportamental(SOMA_BUG, SOMA_REF, "5\n", id_chamada="H1")["id_chamada"] == "H1"
    assert diff_comportamental(SOMA_BUG, SOMA_REF, "5\n")["id_chamada"] is None


def test_diff_iguais():
    d = diff_comportamental(SOMA_REF, SOMA_REF, "4\n")
    assert d["divergiu"] is False
    assert d["aluno"]["trace"] == d["referencia"]["trace"]


def test_diff_erro_so_no_aluno_diverge():
    d = diff_comportamental("print(1 / 0)", "print(0)")
    assert d["divergiu"] is True
    assert d["aluno"]["erro"].startswith("ZeroDivisionError")
    assert d["referencia"]["erro"] is None


def test_diff_laco_infinito_do_aluno_vem_truncado():
    d = diff_comportamental(SOMA_REF.replace("    i = i + 1\n", ""), SOMA_REF, "3\n")
    assert d["divergiu"] is True
    assert "laço infinito" in d["aluno"]["erro"]
    assert d["aluno"]["truncado"] is True
    assert "truncado" not in d["referencia"]
    assert d["referencia"]["saida"] == "6"


def test_diff_estilo_refactory():
    d = diff_comportamental(SEARCH_BUG, SEARCH_REF, chamada="search(5, (1, 5, 9))")
    assert d["divergiu"] is True
    assert (d["aluno"]["saida"], d["referencia"]["saida"]) == ("2", "1")
    assert any(p.get("retornou") == "2" for p in d["aluno"]["trace"])


def test_diff_erro_de_sintaxe_do_aluno():
    d = diff_comportamental("n = int(input(\nprint(n)\n", SOMA_REF, "3\n")
    assert d["divergiu"] is True
    assert d["aluno"]["erro"].startswith("SyntaxError")
    assert d["aluno"]["trace"] == []


def test_diff_nao_interpreta():
    d = diff_comportamental(SOMA_BUG, SOMA_REF, "5\n")
    assert set(d) == {"id_chamada", "divergiu", "aluno", "referencia"}


# ---- m1.config -----------------------------------------------------------------


def test_limites_vem_do_m1_config():
    from arandu_motor.config import CAMINHO, LIMITES, LIMITES_DIFF

    assert CAMINHO.name == "m1.config" and CAMINHO.exists()
    assert Limites().max_linhas == LIMITES["max_linhas"]
    assert LIMITES_DIFF["max_passos"] >= 100
