"""Servidor do M1: as quatro ferramentas via MCP (agentes) e via REST (front).

    python -m arandu_motor                          MCP por stdio (Claude Desktop/Code, MCP Inspector)
    python -m arandu_motor --http                   MCP e REST no host/porta do m1.config ([servidor])
    python -m arandu_motor --http --host 0.0.0.0    idem, acessível pela rede local da equipe

REST: POST /api/<ferramenta> com os argumentos num objeto JSON, ex.:
    POST /api/executar   {"codigo": "print(1 + 1)", "entrada": ""}
"""

import argparse
from typing import Annotated

import anyio
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp_types import ToolAnnotations
from pydantic import Field
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from . import __version__, ferramentas
from .config import SERVIDOR
from .contrato import Comparacao, Execucao, Rastro, Suite, Teste

INSTRUCOES = """\
Motor de execução do Arandu, um treinador de depuração para iniciantes em Python.
Estas ferramentas rodam programas de verdade, num sandbox, e relatam o que aconteceu.
Regra do projeto: não afirme nada sobre o comportamento de um código sem antes rodá-lo aqui.

- Programas que leem do teclado recebem `entrada` (o texto do stdin). Programas no estilo
  Refactory (funções) recebem `chamada`, ex.: "search(42, (1, 5, 9))"; o valor da última
  expressão é impresso.
- No trace, cada passo traz a linha, o texto dela (codigo) e as variáveis DEPOIS de ela
  executar; os valores vêm como repr do Python ("5", "'Ana'", "[1, 2]").
- tipo_erro LimiteDeLinhas ou LimiteDeTempo indica provável laço infinito; linha_erro diz onde.
- diff_comportamental roda o código do aluno e o de referência com a entrada que você escolher
  (por exemplo, a que separa as suas hipóteses) e devolve divergiu, a saída e o trace de cada um.
  O motor não interpreta: a conclusão sobre as hipóteses é sua.
"""

mcp = MCPServer(
    "arandu-motor",
    title="Arandu: motor de execução (M1)",
    instructions=INSTRUCOES,
    version=__version__,
)

_SO_LEITURA = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=False)

Codigo = Annotated[str, Field(description="Código-fonte Python completo do programa.")]
CodigoAluno = Annotated[str, Field(description="Código do aluno (a versão atual, com o erro).")]
CodigoRef = Annotated[str, Field(description="Código de referência (a versão correta).")]
Entrada = Annotated[str, Field(description="Texto enviado ao stdin, o que o input() lê. Separe as linhas com \\n.")]
Chamada = Annotated[
    str | None,
    Field(description="Opcional, para testar funções (estilo Refactory): código executado depois do programa, "
                      'ex.: "search(42, (1, 5, 9))". O valor da última expressão é impresso.'),
]


@mcp.tool(title="Executar programa", annotations=_SO_LEITURA)
def executar(codigo: Codigo, entrada: Entrada = "", chamada: Chamada = None) -> Execucao:
    """Roda o programa uma vez: o que ele imprimiu, o erro (tipo e linha, se houve) e o tempo."""
    return ferramentas.executar(codigo, entrada, chamada)


@mcp.tool(title="Rastrear execução", annotations=_SO_LEITURA)
def trace(
    codigo: Codigo,
    entrada: Entrada = "",
    chamada: Chamada = None,
    max_passos: Annotated[int, Field(ge=1, le=5000, description="Máximo de passos gravados.")] = 200,
    linhas: Annotated[list[int] | None, Field(description="Opcional: grava só os passos destas linhas.")] = None,
) -> Rastro:
    """Roda o programa gravando o valor das variáveis a cada linha executada.

    Cada passo traz a linha, o texto dela (codigo) e as variáveis DEPOIS de ela
    executar; imprimiu, retornou e erro só aparecem quando acontecem."""
    return ferramentas.trace(codigo, entrada, chamada, max_passos=max_passos, linhas=linhas)


@mcp.tool(title="Rodar suíte de testes", annotations=_SO_LEITURA)
def rodar_suite(
    codigo: Codigo,
    testes: Annotated[list[Teste], Field(description="Casos de teste: {id?, entrada?, chamada?, saida_esperada}.")],
) -> Suite:
    """Roda o programa em cada teste e diz quais passaram.

    Compara com a saída esperada ignorando espaços no fim das linhas; teste com
    erro de execução não passa."""
    return ferramentas.rodar_suite(codigo, testes)


@mcp.tool(title="Diff comportamental", annotations=_SO_LEITURA)
def diff_comportamental(
    codigo_aluno: CodigoAluno,
    codigo_ref: CodigoRef,
    entrada: Entrada = "",
    chamada: Chamada = None,
    id_chamada: Annotated[
        str | None,
        Field(description="Opcional: um identificador seu (ex.: da hipótese testada); volta igual na resposta."),
    ] = None,
) -> Comparacao:
    """Roda o código do aluno e o de referência com a mesma entrada e compara.

    Devolve: divergiu (saída ou erro final diferentes) e, para aluno e
    referencia, a saída, o erro e o trace completo. O motor não interpreta:
    a análise dos traces é sua."""
    return ferramentas.diff_comportamental(codigo_aluno, codigo_ref, entrada, chamada, id_chamada)


# ---- REST (mesmas funções, para o front do M4) ----------------------------

_API = {
    "executar": ferramentas.executar,
    "trace": ferramentas.trace,
    "rodar_suite": ferramentas.rodar_suite,
    "diff_comportamental": ferramentas.diff_comportamental,
}


@mcp.custom_route("/api", methods=["GET"])
async def api_indice(request: Request) -> JSONResponse:
    return JSONResponse({"servico": "arandu-motor", "versao": __version__, "ferramentas": list(_API)})


@mcp.custom_route("/api/{ferramenta}", methods=["POST"])
async def api_ferramenta(request: Request) -> JSONResponse:
    funcao = _API.get(request.path_params["ferramenta"])
    if funcao is None:
        return JSONResponse({"erro": "ferramenta desconhecida", "ferramentas": list(_API)}, status_code=404)
    try:
        argumentos = await request.json()
    except ValueError:
        argumentos = None
    if not isinstance(argumentos, dict):
        return JSONResponse({"erro": "o corpo precisa ser um objeto JSON com os argumentos"}, status_code=400)
    argumentos.pop("limites", None)  # os limites ficam do lado do servidor
    try:
        resultado = await anyio.to_thread.run_sync(lambda: funcao(**argumentos))
    except (TypeError, ValueError) as e:
        return JSONResponse({"erro": str(e)}, status_code=400)
    return JSONResponse(resultado)


def criar_app_http(host: str = SERVIDOR["host"]):
    """App ASGI com MCP em /mcp e REST em /api (com CORS liberado para o front)."""
    local = host in ("127.0.0.1", "localhost", "::1")
    # Fora do localhost, desliga a checagem do cabeçalho Host para a equipe
    # acessar pelo IP da máquina. Tudo bem num hackathon; em produção, não.
    seguranca = None if local else TransportSecuritySettings(enable_dns_rebinding_protection=False)
    app = mcp.streamable_http_app(transport_security=seguranca, host=host)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Mcp-Session-Id"],
    )
    return app


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m arandu_motor", description="Servidor do M1 do Arandu (MCP + REST).")
    parser.add_argument("--http", action="store_true", help="servir por HTTP (padrão: stdio, para clientes MCP locais)")
    parser.add_argument("--host", default=SERVIDOR["host"], help="use 0.0.0.0 para a equipe acessar pela rede")
    parser.add_argument("--porta", type=int, default=SERVIDOR["porta"])
    args = parser.parse_args(argv)
    if not args.http:
        mcp.run()  # stdio
        return
    import uvicorn

    print(f"Arandu M1: MCP em http://{args.host}:{args.porta}/mcp  |  REST em http://{args.host}:{args.porta}/api",
          flush=True)
    uvicorn.run(criar_app_http(args.host), host=args.host, port=args.porta)


if __name__ == "__main__":
    main()
