"""
Projeto Arandu — Interface web simples (M3/M4 para testes e demo).

Servidor da biblioteca padrão do Python (sem instalar nada). Serve a página e
expõe a porta única do motor da sessão: POST /evento -> sessao.processar_evento.

Rodar:
    py servidor_web.py
Depois abra no navegador: http://localhost:8000

Se OPENAI_API_KEY estiver definida, usa gpt-4o-mini; senão, o MockLLM.
"""

from __future__ import annotations
import json
import os
import http.server
import socketserver

from sessao import Sessao
from treinador import Treinador
from llm import MockLLM, OpenAILLM

PORTA = 8002   # trocada de 8001 -> 8002 para escapar de um servidor antigo preso na porta
AQUI = os.path.dirname(os.path.abspath(__file__))
# selo de versão: aparece no topo da página e no boot. Se não bater, o servidor
# que está no ar é antigo -> Ctrl+C e rode "py servidor_web.py" de novo.
BUILD = "build 11 · porta 8002 · colagem interna + explicação multilinha"

# ---- banco de bugs de exemplo (viria do M2) ----
BANCO = [
    {
        "id": "bug_pares_01", "equivoco": "CondicaoInvertida", "dificuldade": 2,
        "enunciado": "Leia uma linha de números e imprima QUANTOS são pares.",
        "cod_bugado": "nums = list(map(int, input().split()))\nc = 0\nfor x in nums:\n    if x % 2 == 1:\n        c += 1\nprint(c)\n",
        "cod_ref":    "nums = list(map(int, input().split()))\nc = 0\nfor x in nums:\n    if x % 2 == 0:\n        c += 1\nprint(c)\n",
        "testes": [{"entrada": "1 2", "esperado": "1"},
                   {"entrada": "2 4 6", "esperado": "3"},
                   {"entrada": "1 2 3 4", "esperado": "2"}],
    },
    {
        "id": "bug_soma_01", "equivoco": "LimiteLaco", "dificuldade": 2,
        "enunciado": "Leia um número N e imprima a soma de 1 até N.",
        "cod_bugado": "n = int(input())\ns = 0\nfor i in range(1, n):\n    s += i\nprint(s)\n",
        "cod_ref":    "n = int(input())\ns = 0\nfor i in range(1, n + 1):\n    s += i\nprint(s)\n",
        "testes": [{"entrada": "5", "esperado": "15"},
                   {"entrada": "1", "esperado": "1"},
                   {"entrada": "3", "esperado": "6"}],
    },
]


# Banco padrão = exemplos de stdin (você digita números, ex.: "2 4 6").
# Para usar o banco do M2 (bugs do Refactory, estilo função/chamada), rode com:
#   ARANDU_BANCO=m2 py servidor_web.py     (PowerShell: $env:ARANDU_BANCO="m2")
# Padrão = banco do M2 (bugs reais do Refactory + variações geradas, estilo função).
# O campo de entrada vem pré-preenchido com uma chamada de exemplo (o aluno só edita).
# Para usar os exemplos de stdin (digitar números): ARANDU_BANCO=exemplos
if os.environ.get("ARANDU_BANCO", "m2").lower() != "exemplos":
    try:
        from banco_m2 import carregar_banco
        _dir = os.path.join(AQUI, "Arandu-m2", "Mod2", "data", "bugs")
        BANCO = carregar_banco(os.path.join(_dir, "banco_de_bugs.json"),
                               os.path.join(_dir, "variacoes_etapa3.json"))
        print(f"Banco do M2: {len(BANCO)} bugs (reais do Refactory + variações geradas).")
    except Exception as e:
        print("Aviso: falha ao carregar M2, usando exemplos de stdin:", e)
else:
    print(f"Banco de exemplos (stdin, digite números): {len(BANCO)} bugs.")


def _fazer_llm():
    if os.environ.get("OPENAI_API_KEY"):
        # modelo trocável sem mexer no código: ARANDU_MODELO no .env
        # (ex.: gpt-4o para julgamento/dicas melhores; gpt-4o-mini p/ economizar)
        modelo = os.environ.get("ARANDU_MODELO", "gpt-4o")
        return OpenAILLM(modelo), modelo
    return MockLLM(), "MockLLM (sem chave)"


_llm, NOME_LLM = _fazer_llm()


def nova_sessao():
    # começa sempre um aluno do zero (carregar_modelo=False) para a demo poder repetir
    return Sessao(id_aluno="aluno_web", banco=BANCO, treinador=Treinador(_llm), carregar_modelo=False)


SESSAO = nova_sessao()


class Handler(http.server.BaseHTTPRequestHandler):
    def _json(self, obj, status=200):
        corpo = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _corpo_json(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            caminho = os.path.join(AQUI, "web", "index.html")
            with open(caminho, "rb") as f:
                corpo = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
        elif self.path == "/modelo":
            self._json(SESSAO.resumo_modelo())
        elif self.path == "/painel":
            self._json(SESSAO.snapshot_painel())
        elif self.path == "/info":
            self._json({"llm": NOME_LLM, "build": BUILD})
        else:
            self._json({"erro": "rota desconhecida"}, 404)

    def do_POST(self):
        try:
            if self.path == "/iniciar":
                global SESSAO
                SESSAO = nova_sessao()   # cada início = aluno novo (demo pode repetir)
                self._json(SESSAO.iniciar())
            elif self.path == "/evento":
                self._json(SESSAO.processar_evento(self._corpo_json()))
            else:
                self._json({"erro": "rota desconhecida"}, 404)
        except Exception as e:  # nunca deixa o servidor cair por erro de um evento
            self._json({"erro": f"{type(e).__name__}: {e}"}, 500)

    def log_message(self, *a):   # silencia o log padrão barulhento
        pass


class Servidor(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Multi-thread: uma chamada de LLM lenta atende numa thread e NÃO trava as
    outras requisições (cliques, polling do painel). daemon_threads garante que
    o Ctrl+C encerre mesmo com requisições em voo."""
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    print(f"Arandu rodando em http://localhost:{PORTA}   (LLM: {NOME_LLM})   [{BUILD}]")
    print("Abra esse endereço no navegador. Ctrl+C para parar.")
    with Servidor(("", PORTA), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nparado.")
