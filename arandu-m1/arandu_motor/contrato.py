"""Contrato A: formato das entradas e saídas das ferramentas do M1.

Estes tipos documentam o contrato para quem usa o motor em Python (M2, M3) e
viram o esquema de saída que o servidor MCP publica para os agentes. Mudou um
campo aqui? Avise a equipe e atualize o CONTRATO_A.md.
"""

import sys

if sys.version_info >= (3, 12):
    from typing import NotRequired, TypedDict
else:  # antes do 3.12, o pydantic exige a versão do typing_extensions
    from typing_extensions import NotRequired, TypedDict


# ---- entradas -------------------------------------------------------------


class Teste(TypedDict):
    """Um caso de teste (o mesmo formato de `testes` no Contrato B)."""

    saida_esperada: str
    id: NotRequired[str]
    entrada: NotRequired[str]  # stdin
    chamada: NotRequired[str | None]  # estilo Refactory: "search(42, (1, 5))"


# ---- saídas ---------------------------------------------------------------


class Execucao(TypedDict):
    """executar(): o que aconteceu numa execução."""

    saida: str  # tudo o que o programa imprimiu
    erro: str | None  # "ZeroDivisionError: division by zero (linha 3)"
    tipo_erro: str | None  # nome da exceção, ou LimiteDeLinhas/LimiteDeTempo/LimiteDeSaida
    linha_erro: int | None
    tempo_ms: float
    linhas_executadas: int


class Passo(TypedDict):
    """Um passo do trace: uma linha que rodou e o estado DEPOIS dela."""

    linha: int
    codigo: str  # o texto da linha, ex.: "if nota >= 5:"
    variaveis: dict[str, str]  # repr do Python: "5", "'Ana'", "[1, 2]"
    funcao: NotRequired[str]  # só dentro de uma função (no programa principal não aparece)
    imprimiu: NotRequired[str]  # o que esta linha imprimiu
    retornou: NotRequired[str]  # valor devolvido (linha de return de uma função)
    erro: NotRequired[str]  # exceção levantada nesta linha


class Rastro(TypedDict):
    """trace() e cada lado do diff_comportamental: a execução, passo a passo."""

    saida: str  # tudo o que o programa imprimiu
    erro: str | None  # "ZeroDivisionError: division by zero (linha 3)"
    trace: list[Passo]
    truncado: NotRequired[bool]  # só aparece (true) se o trace foi cortado (ex.: laço infinito)


class ResultadoTeste(TypedDict):
    teste_id: str
    passou: bool
    esperado: str
    obtido: str
    erro: str | None


class Suite(TypedDict):
    """rodar_suite(): um resultado por teste, na ordem recebida."""

    resultados: list[ResultadoTeste]
    aprovados: int
    total: int


class Comparacao(TypedDict):
    """diff_comportamental(): aluno e referência rodados com a mesma entrada."""

    id_chamada: str | None  # devolvido como veio, para o M3 saber a que pedido é a resposta
    divergiu: bool  # True se a saída ou o erro final forem diferentes
    aluno: Rastro  # saída, erro e trace do código do aluno
    referencia: Rastro  # saída, erro e trace do código de referência
