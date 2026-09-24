"""Lê o m1.config: limites do sandbox e endereço do servidor.

O arquivo fica na raiz do projeto. Outro caminho pode ser indicado na variável de
ambiente ARANDU_M1_CONFIG. Sem arquivo, valem os padrões abaixo.
"""

import configparser
import os
from pathlib import Path

CAMINHO = Path(os.environ.get("ARANDU_M1_CONFIG") or Path(__file__).resolve().parent.parent / "m1.config")

_PADROES = {
    "limites": {"tempo_s": 5.0, "max_linhas": 3_000_000, "max_saida": 64_000, "max_passos": 500, "memoria_mb": 512},
    "limites_diff": {"max_passos": 1_000, "max_linhas": 200_000},
    "servidor": {"host": "127.0.0.1", "porta": 8000},
}

_arquivo = configparser.ConfigParser(interpolation=None)
_arquivo.read(CAMINHO, encoding="utf-8")


def _secao(nome: str) -> dict:
    valores = {}
    for chave, padrao in _PADROES[nome].items():
        texto = _arquivo.get(nome, chave, fallback=None)
        valores[chave] = padrao if texto is None else type(padrao)(texto)
    return valores


LIMITES = _secao("limites")
LIMITES_DIFF = _secao("limites_diff")
SERVIDOR = _secao("servidor")
