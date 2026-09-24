"""As ferramentas do M1 (Contrato A): executar, trace, rodar_suite e diff_comportamental.

O M1 só executa e relata: não levanta hipóteses, não escolhe entradas e não tira
conclusões. Isso é do Treinador (M3). Ver as fronteiras no m1.config.

Dois jeitos de alimentar um programa:
- `entrada`: texto enviado ao stdin (o que o input() lê), estilo juiz online;
- `chamada`: código executado depois do programa, para testar funções, estilo
  Refactory, ex.: "search(42, (1, 5, 9))"; o valor da última expressão é impresso.
"""

from __future__ import annotations

from dataclasses import replace

from .config import LIMITES_DIFF
from .contrato import Comparacao, Execucao, Rastro, Suite, Teste
from .sandbox import PADRAO, Limites, rodar
from .saidas import normalizar_saida, saidas_equivalentes


def executar(codigo: str, entrada: str = "", chamada: str | None = None, *,
             limites: Limites = PADRAO) -> Execucao:
    """Roda o programa uma vez: saída, erro (com tipo e linha) e tempo."""
    return _execucao(rodar([_pedido(codigo, entrada, chamada)], limites)[0])


def trace(codigo: str, entrada: str = "", chamada: str | None = None, max_passos: int | None = None,
          linhas: list[int] | None = None, *, limites: Limites = PADRAO) -> Rastro:
    """Roda o programa gravando, a cada linha executada, o valor das variáveis.

    Cada passo traz a linha, o texto dela e o estado DEPOIS de ela executar.
    `linhas` restringe a gravação a algumas linhas."""
    pedido = _pedido(codigo, entrada, chamada, rastrear=True, max_passos=max_passos, linhas=linhas)
    return _rastro(rodar([pedido], limites)[0], codigo)


def rodar_suite(codigo: str, testes: list[Teste], *, limites: Limites = PADRAO) -> Suite:
    """Roda o programa em cada teste e compara com a saída esperada.

    A comparação ignora espaços no fim das linhas e linhas vazias no final; um
    teste com erro de execução não passa."""
    for k, teste in enumerate(testes, 1):
        if "saida_esperada" not in teste:
            raise ValueError(f"o teste {k} não tem 'saida_esperada'")
    execucoes = [_pedido(codigo, t.get("entrada") or "", t.get("chamada")) for t in testes]
    resultados = []
    for k, (teste, r) in enumerate(zip(testes, rodar(execucoes, limites)), 1):
        esperado = teste["saida_esperada"]
        resultados.append({
            "teste_id": str(teste.get("id") or f"t{k}"),
            "passou": r["erro"] is None and saidas_equivalentes(r["saida"], esperado),
            "esperado": esperado,
            "obtido": r["saida"].rstrip("\n"),
            "erro": r["erro"],
        })
    return {"resultados": resultados, "aprovados": sum(r["passou"] for r in resultados), "total": len(resultados)}


def diff_comportamental(codigo_aluno: str, codigo_ref: str, entrada: str = "", chamada: str | None = None,
                        id_chamada: str | None = None, *, limites: Limites = PADRAO) -> Comparacao:
    """Roda o código do aluno e o de referência com a mesma entrada e compara.

    Devolve se divergiram (saída ou erro final diferentes) e a saída, o erro e
    o trace de cada um. Não interpreta: a entrada vem do M3 (escolhida a partir
    das hipóteses dele) e quem analisa os traces e conclui é o M3."""
    limites = replace(limites, max_passos=LIMITES_DIFF["max_passos"],
                      max_linhas=min(limites.max_linhas, LIMITES_DIFF["max_linhas"]))
    pedidos = [_pedido(c, entrada, chamada, rastrear=True) for c in (codigo_aluno, codigo_ref)]
    ra, rr = rodar(pedidos, limites)
    return {
        "id_chamada": id_chamada,
        "divergiu": (normalizar_saida(ra["saida"]) != normalizar_saida(rr["saida"])
                     or ra["tipo_erro"] != rr["tipo_erro"]),
        "aluno": _rastro(ra, codigo_aluno),
        "referencia": _rastro(rr, codigo_ref),
    }


def _pedido(codigo, entrada, chamada, **extra) -> dict:
    if not isinstance(codigo, str):
        raise TypeError("'codigo' precisa ser texto (o código-fonte Python)")
    if not isinstance(entrada or "", str) or not isinstance(chamada or "", str):
        raise TypeError("'entrada' e 'chamada' precisam ser texto")
    pedido = {"codigo": codigo, "entrada": entrada or "", "chamada": chamada or None}
    pedido.update({k: v for k, v in extra.items() if v is not None})
    return pedido


def _execucao(resultado: dict) -> Execucao:
    return {
        "saida": resultado["saida"].rstrip("\n"),
        "erro": resultado["erro"],
        "tipo_erro": resultado["tipo_erro"],
        "linha_erro": resultado["linha_erro"],
        "tempo_ms": resultado["tempo_ms"],
        "linhas_executadas": resultado["linhas_executadas"],
    }


def _rastro(resultado: dict, codigo: str) -> Rastro:
    """Resultado do sandbox no formato limpo, pensado para uma LLM ler."""
    linhas = codigo.splitlines()
    trace = []
    for p in resultado.get("passos", []):
        numero = p["linha"]
        passo = {"linha": numero, "codigo": linhas[numero - 1].strip() if 0 < numero <= len(linhas) else ""}
        if p["funcao"] != "<module>":
            passo["funcao"] = p["funcao"]
        passo["variaveis"] = p["variaveis"]
        if "saida" in p:
            passo["imprimiu"] = p["saida"].rstrip("\n")
        if "retorno" in p:
            passo["retornou"] = p["retorno"]
        if "excecao" in p:
            passo["erro"] = p["excecao"]
        trace.append(passo)
    rastro = {"saida": resultado["saida"].rstrip("\n"), "erro": resultado["erro"], "trace": trace}
    if resultado.get("truncado"):
        rastro["truncado"] = True
    return rastro
