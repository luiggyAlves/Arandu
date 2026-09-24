"""
Projeto Arandu — Loader do banco de bugs do M2 (Contrato B) + variações geradas.

Lê o `banco_de_bugs.json` (5 bugs reais do Refactory) e, se pedido, também as
variações aprovadas do Construtor (`variacoes_etapa3.json`) — realizando a visão
"gerar novos bugs reproduzindo o equívoco". Converte tudo para o formato do M3.

Os bugs do Refactory são estilo FUNÇÃO: cada teste é uma CHAMADA
(ex.: "search(42, (1,5,10))"). Por isso `modo="chamada"`. Para a interface, cada
bug carrega `exemplo_entrada` (uma chamada real dos testes) que já vem preenchida
no campo — o aluno só edita os números, sem digitar a chamada do zero.
"""

from __future__ import annotations
import json
import os
import re

_ENUNCIADOS = {
    "question_1": ("Busca em sequência ORDENADA. search(x, seq) deve devolver o índice da "
                   "primeira posição cujo elemento é maior ou igual a x. Se x for maior que "
                   "todos, devolve o tamanho da sequência."),
    "question_2": ("Datas únicas. Dado um dia (ou mês) e uma lista de aniversários, diga se "
                   "aquele dia (ou mês) aparece EXATAMENTE uma vez na lista."),
    "question_3": "Remova os elementos duplicados da lista, preservando a ordem.",
    "question_4": "Ordene as tuplas segundo o critério pedido.",
    "question_5": "Retorne os K maiores elementos da lista.",
}


def _assinatura(codigo_ref: str) -> str:
    m = re.search(r"^def .+:", codigo_ref, flags=re.MULTILINE)
    return m.group(0) if m else ""


def _dificuldade(codigo: str) -> int:
    """Estima dificuldade pela complexidade do código (nº de funções e linhas),
    para a sessão apresentar os bugs mais SIMPLES primeiro (demo mais intuitiva)."""
    linhas = len([l for l in codigo.splitlines() if l.strip()])
    funcoes = codigo.count("def ")
    d = 1 + funcoes + (1 if linhas > 15 else 0) + (1 if linhas > 25 else 0)
    return max(1, min(5, d))


def _mapear(b: dict) -> dict:
    testes = [{"chamada": t["input"], "esperado": str(t["output_esperado"])}
              for t in b.get("testes", [])]
    return {
        "id": b["bug_id"],
        "equivoco": b.get("equivoco_progmiscon", "Desconhecido"),
        "dificuldade": b.get("dificuldade") or _dificuldade(b["codigo_errado"]),
        "enunciado": _ENUNCIADOS.get(b.get("question_id", ""), "Conserte o bug no programa."),
        "cod_bugado": b["codigo_errado"],
        "cod_ref": b["codigo_referencia"],
        "modo": "chamada",
        "assinatura": _assinatura(b["codigo_referencia"]),
        "exemplo_entrada": testes[0]["chamada"] if testes else "",   # p/ pré-preencher o campo
        "origem": b.get("origem", "refactory"),
        "testes": testes,
    }


def carregar_banco(caminho_banco: str, caminho_variacoes: str | None = None,
                   incluir_variacoes: bool = True) -> list[dict]:
    with open(caminho_banco, encoding="utf-8") as f:
        banco = [_mapear(b) for b in json.load(f)]

    if incluir_variacoes and caminho_variacoes and os.path.exists(caminho_variacoes):
        with open(caminho_variacoes, encoding="utf-8") as f:
            variacoes = json.load(f)
        # só as variações aprovadas pelo Validador viram bugs de treino
        aprovadas = [v for v in variacoes if v.get("aprovado_por_validador")]
        banco.extend(_mapear(v) for v in aprovadas)

    return banco


def carregar_trajetorias(caminho: str) -> list[dict]:
    if not os.path.exists(caminho):
        return []
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def recuperar_trajetorias(trajetorias: list[dict], equivoco: str, limite: int = 3) -> list[dict]:
    return [t for t in trajetorias if t.get("equivoco") == equivoco][:limite]
