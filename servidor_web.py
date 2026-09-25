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
import re
import threading
import http.server
import socketserver
from urllib.parse import unquote, urlparse

import catalogo
import validacao_banco
from sessao import Sessao
from treinador import Treinador
from llm import MockLLM, OpenAILLM

PORTA = 8002   # trocada de 8001 -> 8002 para escapar de um servidor antigo preso na porta
AQUI = os.path.dirname(os.path.abspath(__file__))
# selo de versão: aparece no topo da página e no boot. Se não bater, o servidor
# que está no ar é antigo -> Ctrl+C e rode "py servidor_web.py" de novo.
BUILD = "build 12 · porta 8002 · registro de sessão + métricas"

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
    # começa sempre um aluno do zero (carregar_modelo=False) para a demo poder repetir.
    # nome_llm é do registro de sessão (outro módulo); se a Sessao ainda não aceitar, segue sem ele.
    try:
        return Sessao(id_aluno="aluno_web", banco=BANCO, treinador=Treinador(_llm),
                      carregar_modelo=False, nome_llm=NOME_LLM)
    except TypeError:
        return Sessao(id_aluno="aluno_web", banco=BANCO, treinador=Treinador(_llm),
                      carregar_modelo=False)


SESSAO = nova_sessao()

# Métricas de bugs: calculadas uma vez, em thread daemon, no boot.
# Enquanto não termina, GET /metricas/bugs devolve {"estado":"calculando"}.
_METRICAS_BUGS = {"estado": "calculando"}
_METRICAS_LOCK = threading.Lock()
_ID_SESSAO = re.compile(r"^[0-9A-Za-z_-]{1,64}$")
_CAMINHO_VARIACOES = os.path.join(
    AQUI, "Arandu-m2", "Mod2", "data", "bugs", "variacoes_etapa3.json")


def _calcular_metricas_bugs(banco, caminho):
    global _METRICAS_BUGS
    try:
        resultado = validacao_banco.calcular(banco, caminho)
    except Exception as e:
        resultado = {"estado": "erro", "detalhe": str(e)}
    with _METRICAS_LOCK:
        _METRICAS_BUGS = resultado


def _metricas_bugs_atual():
    with _METRICAS_LOCK:
        return _METRICAS_BUGS


threading.Thread(
    target=_calcular_metricas_bugs,
    args=(list(BANCO), _CAMINHO_VARIACOES),
    name="metricas-bugs",
    daemon=True,
).start()


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

    def _rota(self):
        """Caminho sem query string. None se houver tentativa de path traversal."""
        bruto = urlparse(self.path).path
        if "\x00" in bruto:
            return None
        decodificado = unquote(bruto)
        if "\\" in decodificado:
            return None
        partes = []
        for p in decodificado.split("/"):
            if p in ("", "."):
                continue
            if p == "..":
                return None
            partes.append(p)
        return "/" + "/".join(partes) if partes else "/"

    def _enviar_arquivo(self, caminho, mime):
        try:
            with open(caminho, "rb") as f:
                corpo = f.read()
        except OSError:
            self._json({"erro": "rota desconhecida"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def _estatico(self, rota):
        prefixo = "css" if rota.startswith("/css/") else "js"
        base = os.path.realpath(os.path.join(AQUI, "web", prefixo))
        alvo = os.path.realpath(os.path.join(AQUI, "web", rota.lstrip("/")))
        if not alvo.startswith(base + os.sep) or not os.path.isfile(alvo):
            self._json({"erro": "rota desconhecida"}, 404)
            return
        ext = os.path.splitext(alvo)[1].lower()
        if ext == ".css":
            mime = "text/css; charset=utf-8"
        elif ext == ".js":
            mime = "application/javascript; charset=utf-8"
        elif ext == ".html":
            mime = "text/html; charset=utf-8"
        else:
            mime = "application/octet-stream"
        self._enviar_arquivo(alvo, mime)

    def _responder_painel(self):
        snap = SESSAO.snapshot_painel()
        custo = None
        if hasattr(SESSAO, "custo"):
            try:
                custo = SESSAO.custo()
            except Exception:
                custo = None
        snap["metricas"] = {"custo": custo, "llm": NOME_LLM}
        snap["sessao_id"] = getattr(getattr(SESSAO, "registro", None), "id", None)
        self._json(snap)

    def _importar_registro(self):
        """Import tardio: registro.py pode ainda não existir. None se indisponível."""
        try:
            import registro
        except ImportError:
            return None
        return registro

    def _listar_sessoes(self):
        registro = self._importar_registro()
        listar = getattr(registro, "listar_sessoes", None) if registro is not None else None
        if not callable(listar):
            self._json({"erro": "registro indisponível"}, 503)
            return
        self._json({"sessoes": listar()})

    def _uma_sessao(self, id_sessao):
        if not _ID_SESSAO.fullmatch(id_sessao or ""):
            self._json({"erro": "sessão não encontrada"}, 404)
            return
        registro = self._importar_registro()
        carregar = getattr(registro, "carregar_sessao", None) if registro is not None else None
        if not callable(carregar):
            self._json({"erro": "registro indisponível"}, 503)
            return
        try:
            dados = carregar(id_sessao)
        except FileNotFoundError:
            self._json({"erro": "sessão não encontrada"}, 404)
            return
        if not dados:
            self._json({"erro": "sessão não encontrada"}, 404)
            return
        self._json(dados)

    def do_GET(self):
        rota = self._rota()
        if rota is None:
            self._json({"erro": "rota desconhecida"}, 404)
            return
        if rota in ("/", "/index.html"):
            self._enviar_arquivo(os.path.join(AQUI, "web", "index.html"), "text/html; charset=utf-8")
        elif rota == "/painel.html":
            self._enviar_arquivo(os.path.join(AQUI, "web", "painel.html"), "text/html; charset=utf-8")
        elif rota == "/professor.html":
            self._enviar_arquivo(os.path.join(AQUI, "web", "professor.html"), "text/html; charset=utf-8")
        elif rota.startswith("/css/") or rota.startswith("/js/"):
            self._estatico(rota)
        elif rota == "/modelo":
            resumo = SESSAO.resumo_modelo()
            dominio = resumo.get("dominio_por_equivoco") or {}
            resumo["rotulos_equivocos"] = {
                eid: catalogo.CATALOGO[eid]["nome"]
                for eid in dominio
                if eid in catalogo.CATALOGO and catalogo.CATALOGO[eid].get("nome")
            }
            self._json(resumo)
        elif rota == "/painel":
            self._responder_painel()
        elif rota == "/metricas/bugs":
            self._json(_metricas_bugs_atual())
        elif rota == "/sessoes":
            self._listar_sessoes()
        elif rota.startswith("/sessoes/"):
            self._uma_sessao(rota[len("/sessoes/"):])
        elif rota == "/info":
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
