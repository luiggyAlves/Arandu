"""Sandbox do Arandu: roda código Python em processos separados, com limites.

Cada chamada de `rodar()` recebe uma lista de "execuções" (código + entrada) e
devolve um resultado por execução, na mesma ordem. As execuções são divididas
entre alguns processos-filhos que rodam em paralelo; cada filho (_filho.py)
executa a sua fatia em sequência e responde uma linha JSON por execução.

Se um filho morre no meio (tempo esgotado, falha grave), a execução culpada é
marcada com erro e as restantes seguem num filho novo -- um programa ruim não
derruba os outros.
"""

from __future__ import annotations

import collections
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import LIMITES

_FILHO = Path(__file__).with_name("_filho.py")
_MAX_PROCESSOS = max(1, min(8, os.cpu_count() or 2))
_MAX_REINICIOS = 5
_FOLGA_S = 5.0  # além do tempo por execução: partida do processo, máquina ocupada


@dataclass(frozen=True)
class Limites:
    """Limites de cada execução (padrões: seção [limites] do m1.config)."""

    tempo_s: float = LIMITES["tempo_s"]  # tempo de relógio por execução
    max_linhas: int = LIMITES["max_linhas"]  # linhas executadas (pega laço infinito e diz onde)
    max_saida: int = LIMITES["max_saida"]  # caracteres impressos
    max_passos: int = LIMITES["max_passos"]  # passos guardados num trace
    memoria_mb: int = LIMITES["memoria_mb"]  # só vale em Linux/macOS


PADRAO = Limites()


def rodar(execucoes: list[dict], limites: Limites = PADRAO) -> list[dict]:
    """Roda cada execução no sandbox e devolve os resultados na mesma ordem.

    Cada execução é um dict com: codigo, entrada (stdin), chamada (opcional),
    rastrear (bool), max_passos e linhas (filtro do trace)."""
    if not execucoes:
        return []
    n = min(len(execucoes), _MAX_PROCESSOS)
    tamanho = -(-len(execucoes) // n)  # divisão arredondando para cima
    fatias = [execucoes[k : k + tamanho] for k in range(0, len(execucoes), tamanho)]
    if len(fatias) == 1:
        return _rodar_fatia(fatias[0], limites)
    with ThreadPoolExecutor(max_workers=len(fatias)) as pool:
        partes = pool.map(lambda fatia: _rodar_fatia(fatia, limites), fatias)
        return [resultado for parte in partes for resultado in parte]


def _rodar_fatia(execucoes: list[dict], limites: Limites) -> list[dict]:
    resultados: list[dict] = []
    reinicios = 0
    while len(resultados) < len(execucoes):
        restantes = execucoes[len(resultados) :]
        obtidos, falha, diagnostico = _processo(restantes, limites)
        resultados.extend(obtidos)
        if len(resultados) == len(execucoes):
            break
        if not (obtidos and obtidos[-1].get("fim_do_processo")):
            # o filho morreu sem responder pela execução em andamento
            resultados.append(_resultado_de_falha(falha, diagnostico, limites))
        reinicios += 1
        if reinicios > _MAX_REINICIOS:
            faltam = len(execucoes) - len(resultados)
            resultados.extend(
                _resultado_de_falha("desistiu", "muitas falhas seguidas no sandbox", limites) for _ in range(faltam)
            )
    for resultado in resultados:
        resultado.pop("i", None)
        resultado.pop("fim_do_processo", None)
    return resultados


def _processo(execucoes: list[dict], limites: Limites) -> tuple[list[dict], str | None, str]:
    """Roda as execuções num filho; devolve (resultados recebidos, falha, stderr do filho)."""
    trabalho = json.dumps({"limites": asdict(limites), "execucoes": execucoes}).encode("ascii")
    proc = subprocess.Popen(
        [_interpretador(), "-S", "-s", "-B", str(_FILHO)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=_pasta_de_trabalho(),
        env=_ambiente(),
        **_opcoes_da_plataforma(),
    )
    linhas: queue.Queue = queue.Queue()
    erros: collections.deque = collections.deque(maxlen=40)
    threading.Thread(target=_encaminhar, args=(proc.stdout, linhas), daemon=True).start()
    leitor_de_erros = threading.Thread(target=erros.extend, args=(proc.stderr,), daemon=True)
    leitor_de_erros.start()
    try:
        proc.stdin.write(trabalho)
        proc.stdin.close()
    except OSError:
        pass  # o filho já morreu; o motivo aparece no stderr

    obtidos: list[dict] = []
    falha = None
    try:
        while len(obtidos) < len(execucoes):
            try:
                linha = linhas.get(timeout=limites.tempo_s + _FOLGA_S)
            except queue.Empty:
                falha = "tempo"
                break
            if linha is None:
                falha = "morreu"
                break
            obtidos.append(json.loads(linha))
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait()
    leitor_de_erros.join(timeout=1)
    diagnostico = b"".join(erros).decode("utf-8", "replace").strip()
    return obtidos, falha, diagnostico


def _encaminhar(fluxo, fila: queue.Queue) -> None:
    for linha in fluxo:
        fila.put(linha)
    fila.put(None)  # fim: o filho fechou a saída


def _resultado_de_falha(falha: str | None, diagnostico: str, limites: Limites) -> dict:
    if falha == "tempo":
        erro, tipo = f"Tempo limite de {limites.tempo_s:g} s excedido", "LimiteDeTempo"
    else:
        erro, tipo = "O sandbox falhou ao executar o programa", "FalhaDoSandbox"
        if diagnostico:
            erro += ": " + diagnostico[-400:]
    return {
        "saida": "", "erro": erro, "tipo_erro": tipo, "linha_erro": None,
        "tempo_ms": 0.0, "linhas_executadas": 0, "passos": [], "truncado": True,
    }


def _interpretador() -> str:
    # Num venv do Windows, sys.executable é um lançador que abre outro processo;
    # o interpretador-base evita isso (e o filho não precisa dos pacotes do venv).
    base = getattr(sys, "_base_executable", None)
    return base if base and os.path.exists(base) else sys.executable


_AMBIENTE_HERDADO = {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL"}


def _ambiente() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k.upper() in _AMBIENTE_HERDADO}
    env.update(PYTHONHASHSEED="0", PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    return env


def _pasta_de_trabalho() -> str:
    pasta = Path(tempfile.gettempdir()) / "arandu_sandbox"
    pasta.mkdir(exist_ok=True)
    return str(pasta)


def _opcoes_da_plataforma() -> dict:
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {"start_new_session": True}
