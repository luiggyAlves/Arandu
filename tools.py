"""
Projeto Arandu — Adaptador do Contrato A (liga o M3 ao motor real do M1).

O M3 continua chamando a MESMA interface de sempre (analisar, executar,
rodar_suite, trace, resumo_analise). Este arquivo traduz essas chamadas para as
funções do `arandu_motor` (M1) e converte os formatos de volta.

Diferenças de formato que este adaptador reconcilia:
  - M1.diff_comportamental -> {id_chamada, divergiu, aluno:{saida,erro,trace}, referencia:{...}}
    aqui vira -> {entrada, saida_aluno, saida_ref, erro_aluno, erro_ref, divergiu,
                  divergencia_saida, trace_aluno, trace_ref}
  - M1.rodar_suite usa 'saida_esperada' e devolve {resultados, aprovados, total};
    aqui a gente aceita 'esperado' e devolve a lista simples que o M3 usa.

Se o pacote do M1 não for encontrado, o erro abaixo diz o que fazer.
"""

from __future__ import annotations
import os
import sys
from itertools import zip_longest

# Encontra o pacote arandu_motor (M1) ao lado deste arquivo (arandu-m1/) ou já instalado.
_AQUI = os.path.dirname(os.path.abspath(__file__))
for _cand in (os.path.join(_AQUI, "arandu-m1"), _AQUI, os.path.join(_AQUI, "..", "arandu-m1")):
    if os.path.isdir(os.path.join(_cand, "arandu_motor")):
        if _cand not in sys.path:
            sys.path.insert(0, _cand)
        break

try:
    from arandu_motor import (
        executar as _m1_executar,
        trace as _m1_trace,
        rodar_suite as _m1_suite,
        diff_comportamental as _m1_diff,
    )
except ImportError as e:  # ajuda quem for rodar
    raise ImportError(
        "Não encontrei o motor do M1 (arandu_motor). Deixe a pasta 'arandu-m1' "
        "ao lado deste arquivo, ou rode 'pip install -e .' dentro de arandu-m1. "
        f"Detalhe: {e}"
    )

MAX_PASSOS_TRACE = 200  # compatibilidade


def executar(codigo: str, entrada: str = "", chamada: str | None = None) -> dict:
    r = _m1_executar(codigo, entrada, chamada)
    return {"saida": r["saida"], "erro": r["erro"], "tempo_ms": r.get("tempo_ms")}


def trace(codigo: str, entrada: str = "", chamada: str | None = None) -> dict:
    r = _m1_trace(codigo, entrada, chamada)
    return {"saida": r["saida"], "erro": r["erro"], "passos": r.get("trace", [])}


def _primeira_divergencia_saida(sa: str, sr: str):
    for i, (la, lr) in enumerate(zip_longest((sa or "").splitlines(),
                                             (sr or "").splitlines()), start=1):
        if la != lr:
            return {"linha_saida": i, "aluno": la, "ref": lr}
    return None


def analisar(cod_aluno: str, cod_ref: str, entrada: str = "", chamada: str | None = None) -> dict:
    c = _m1_diff(cod_aluno, cod_ref, entrada, chamada)
    aluno, ref = c["aluno"], c["referencia"]
    return {
        "entrada": chamada or entrada,   # o estímulo usado (chamada de função ou stdin)
        "saida_aluno": aluno["saida"],
        "saida_ref": ref["saida"],
        "erro_aluno": aluno["erro"],
        "erro_ref": ref["erro"],
        "divergiu": c["divergiu"],
        "divergencia_saida": _primeira_divergencia_saida(aluno["saida"], ref["saida"]),
        "trace_aluno": aluno.get("trace", []),
        "trace_ref": ref.get("trace", []),
    }


def rodar_suite(codigo: str, testes: list[dict]) -> list[dict]:
    # M3 usa {entrada, esperado}; M1 usa {entrada, saida_esperada, chamada?}
    testes_m1 = []
    for t in testes:
        item = {"entrada": t.get("entrada", ""),
                "saida_esperada": t.get("esperado", t.get("saida_esperada", ""))}
        if t.get("chamada"):
            item["chamada"] = t["chamada"]
        testes_m1.append(item)
    s = _m1_suite(codigo, testes_m1)
    out = []
    for t, r in zip(testes, s["resultados"]):
        estimulo = t.get("entrada") or t.get("chamada", "")   # stdin ou chamada de função
        out.append({"entrada": estimulo, "esperado": r["esperado"],
                    "obtido": r["obtido"], "passou": r["passou"], "erro": r["erro"]})
    return out


def resumo_analise(a: dict) -> dict:
    """Versão enxuta de analisar() para mandar ao LLM sem estourar contexto."""
    return {
        "entrada": a["entrada"],
        "saida_aluno": (a["saida_aluno"] or "").strip(),
        "saida_ref": (a["saida_ref"] or "").strip(),
        "erro_aluno": a["erro_aluno"],
        "divergiu": a["divergiu"],
        "divergencia_saida": a["divergencia_saida"],
        "ultimos_passos_aluno": a["trace_aluno"][-5:],
    }
