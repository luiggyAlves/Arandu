"""
Projeto Arandu — Registro de uma sessão de treino.

Um JSON por sessão em dados_sessoes/ (ao lado deste módulo). A gravação é
atômica: escreve <id>.json.tmp e só então troca o arquivo final. A leitura
não regrava — sessão parada demais aparece como abandonada só na resposta.
"""

from __future__ import annotations

import json
import os
import re
import time

import catalogo
import config

PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados_sessoes")
_ID_RE = re.compile(r"^[0-9A-Za-z_-]{1,64}$")
_CHAVES_DETALHE = ("desafios", "dominio_por_equivoco", "depuracao", "rotulos_equivocos")
_CAMPOS_DESAFIO = (
    "bug_id", "equivoco", "rotulo", "origem", "inicio", "fim", "duracao_s",
    "execucoes", "entradas_distintas", "entradas_que_expuseram_o_erro",
    "abriu_variaveis", "submissoes", "dicas_pedidas", "intervencoes",
    "colou_codigo", "resolvido", "rubrica",
)


def _novo_id() -> str:
    """Ano-mês-dia-hora mais 4 hex: cabe no validador de carregar_sessao."""
    return time.strftime("%Y%m%d-%H%M%S") + "-" + os.urandom(2).hex()


def _rotulo(equivoco) -> str | None:
    return (catalogo.CATALOGO.get(equivoco) or {}).get("nome")


def _rotulos(dominio: dict, desafios: list[dict]) -> dict:
    ids = set(catalogo.CATALOGO)
    ids.update(dominio or {})
    for d in desafios:
        if d.get("equivoco"):
            ids.add(d["equivoco"])
    return {i: _rotulo(i) for i in sorted(ids, key=str)}


def _desafio_publico(d: dict, agora: float) -> dict:
    out = {k: d.get(k) for k in _CAMPOS_DESAFIO}
    out["intervencoes"] = dict(d.get("intervencoes") or {})
    if out.get("fim") is None:
        ini = out.get("inicio") if isinstance(out.get("inicio"), (int, float)) else agora
        out["duracao_s"] = max(0, int(agora - ini))
    return out


def _gravar_atomico(id_sessao: str, rec: dict) -> None:
    os.makedirs(PASTA, exist_ok=True)
    final = os.path.join(PASTA, f"{id_sessao}.json")
    tmp = os.path.join(PASTA, f"{id_sessao}.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, final)


def _ler(caminho: str) -> dict | None:
    if not os.path.isfile(caminho):
        return None
    try:
        with open(caminho, encoding="utf-8") as f:
            rec = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return rec if isinstance(rec, dict) else None


def _ajustar_leitura(rec: dict) -> dict:
    """Copia o registro e aplica abandono/duração. Não escreve no disco."""
    rec = dict(rec)
    agora = time.time()
    if rec.get("em_andamento"):
        atualizado = rec.get("atualizado_em")
        if isinstance(atualizado, (int, float)) and (agora - atualizado) > config.TIMEOUT_INATIVIDADE_S:
            rec["em_andamento"] = False
            rec["motivo_fim"] = "abandonada"
            rec["fim"] = atualizado
    inicio = rec.get("inicio")
    if not isinstance(inicio, (int, float)):
        inicio = agora
    if rec.get("em_andamento"):
        rec["duracao_s"] = max(0, int(agora - inicio))
    else:
        fim = rec.get("fim")
        if not isinstance(fim, (int, float)):
            fim = rec.get("atualizado_em") if isinstance(rec.get("atualizado_em"), (int, float)) else agora
        rec["duracao_s"] = max(0, int(fim - inicio))
    return rec


def listar_sessoes() -> list[dict]:
    """Resumos, da mais nova para a mais antiga (sem o miúdo de cada desafio)."""
    if not os.path.isdir(PASTA):
        return []
    regs = []
    for nome in os.listdir(PASTA):
        if not nome.endswith(".json"):
            continue
        rec = _ler(os.path.join(PASTA, nome))
        if rec is None:
            continue
        resumo = _ajustar_leitura(rec)
        for chave in _CHAVES_DETALHE:
            resumo.pop(chave, None)
        regs.append(resumo)
    regs.sort(key=lambda r: (
        r.get("inicio") if isinstance(r.get("inicio"), (int, float)) else 0,
        str(r.get("id") or ""),
    ), reverse=True)
    return regs


def carregar_sessao(id_sessao: str) -> dict | None:
    """Registro completo, ou None se o id for inválido ou não existir."""
    if not isinstance(id_sessao, str) or _ID_RE.fullmatch(id_sessao) is None:
        return None
    rec = _ler(os.path.join(PASTA, f"{id_sessao}.json"))
    if rec is None:
        return None
    return _ajustar_leitura(rec)


class RegistroSessao:
    """Acumula desafios, dicas e custo de uma sessão e grava o JSON."""

    def __init__(self, id_aluno: str, nome_llm: str = ""):
        self.id = _novo_id()
        self.id_aluno = id_aluno
        self.llm = nome_llm or ""
        self.inicio = time.time()
        self.fim = None
        self.motivo_fim = None
        self.em_andamento = True
        self.atualizado_em = self.inicio
        self.desafios: list[dict] = []
        self._aberto: dict | None = None

    def novo_desafio(self, bug: dict) -> None:
        """Abre um desafio. O anterior, se ainda aberto, fecha sem resolvido."""
        self._fechar_aberto(False)
        eq = bug.get("equivoco")
        agora = time.time()
        d = {
            "bug_id": bug.get("id"),
            "equivoco": eq,
            "rotulo": _rotulo(eq),
            "origem": bug.get("origem") or "",
            "inicio": agora,
            "fim": None,
            "duracao_s": 0,
            "execucoes": 0,
            "entradas_distintas": 0,
            "entradas_que_expuseram_o_erro": 0,
            "abriu_variaveis": 0,
            "submissoes": 0,
            "dicas_pedidas": 0,
            "intervencoes": {},
            "colou_codigo": 0,
            "resolvido": False,
            "rubrica": None,
            "_entradas": set(),
            "_expuseram": set(),
            "_dicas_proativas": 0,
        }
        self.desafios.append(d)
        self._aberto = d

    def _fechar_aberto(self, resolvido: bool) -> None:
        d = self._aberto
        if d is None:
            return
        if d.get("fim") is None:
            d["fim"] = time.time()
            d["duracao_s"] = max(0, int(d["fim"] - d["inicio"]))
        if not d.get("resolvido"):
            d["resolvido"] = bool(resolvido)
        self._aberto = None

    def rodou_entrada(self, entrada: str, divergiu: bool) -> None:
        d = self._aberto
        if d is None:
            return
        d["execucoes"] += 1
        d["_entradas"].add(entrada)
        d["entradas_distintas"] = len(d["_entradas"])
        if divergiu:
            d["_expuseram"].add(entrada)
            d["entradas_que_expuseram_o_erro"] = len(d["_expuseram"])

    def ver_trace(self) -> None:
        if self._aberto is not None:
            self._aberto["abriu_variaveis"] += 1

    def pediu_dica(self) -> None:
        if self._aberto is not None:
            self._aberto["dicas_pedidas"] += 1

    def intervencao(self, acao: str) -> None:
        """Intervenção proativa que chegou de fato ao aluno."""
        d = self._aberto
        if d is None:
            return
        d["intervencoes"][acao] = d["intervencoes"].get(acao, 0) + 1
        if acao == "DAR_DICA":
            d["_dicas_proativas"] += 1

    def colou_codigo(self) -> None:
        if self._aberto is not None:
            self._aberto["colou_codigo"] += 1

    def submeteu(self, passou: bool) -> None:
        """Conta a submissão, tenha a suíte passado ou não."""
        if self._aberto is None:
            return
        self._aberto["submissoes"] += 1

    def explicou(self, rubrica: dict | None) -> None:
        d = self._aberto
        if d is None:
            return
        d["rubrica"] = rubrica
        d["resolvido"] = True
        self._fechar_aberto(True)

    def encerrar(self, motivo: str) -> None:
        """Fecha o desafio aberto (resolvido só se já estava) e a sessão."""
        if self._aberto is not None:
            self._fechar_aberto(bool(self._aberto.get("resolvido")))
        if self.em_andamento:
            self.em_andamento = False
            self.fim = time.time()
            self.motivo_fim = motivo

    def salvar(self, custo: dict | None = None, dominio: dict | None = None,
               depuracao: dict | None = None) -> None:
        agora = time.time()
        self.atualizado_em = agora
        if self._aberto is not None and self._aberto.get("fim") is None:
            self._aberto["duracao_s"] = max(0, int(agora - self._aberto["inicio"]))
        dominio = dict(dominio or {})
        depuracao = dict(depuracao or {})
        desafios = [_desafio_publico(d, agora) for d in self.desafios]
        notas = []
        dicas = 0
        submissoes = 0
        resolvidos = 0
        for d in self.desafios:
            submissoes += int(d.get("submissoes") or 0)
            dicas += int(d.get("dicas_pedidas") or 0) + int(d.get("_dicas_proativas") or 0)
            if d.get("resolvido"):
                resolvidos += 1
            rub = d.get("rubrica")
            if isinstance(rub, dict) and rub.get("nota") is not None:
                try:
                    notas.append(float(rub["nota"]))
                except (TypeError, ValueError):
                    pass
        if self.em_andamento:
            duracao = max(0, int(agora - self.inicio))
        else:
            fim = self.fim if isinstance(self.fim, (int, float)) else agora
            duracao = max(0, int(fim - self.inicio))
        rec = {
            "id": self.id,
            "id_aluno": self.id_aluno,
            "llm": self.llm,
            "inicio": self.inicio,
            "fim": self.fim,
            "motivo_fim": self.motivo_fim,
            "em_andamento": self.em_andamento,
            "atualizado_em": self.atualizado_em,
            "duracao_s": duracao,
            "desafios_iniciados": len(self.desafios),
            "desafios_resolvidos": resolvidos,
            "submissoes": submissoes,
            "dicas": dicas,
            "nota_media_explicacao": (sum(notas) / len(notas)) if notas else None,
            "custo": dict(custo or {}),
            "desafios": desafios,
            "dominio_por_equivoco": dominio,
            "depuracao": depuracao,
            "rotulos_equivocos": _rotulos(dominio, self.desafios),
        }
        _gravar_atomico(self.id, rec)
