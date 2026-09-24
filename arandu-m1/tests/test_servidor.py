"""O servidor expõe as mesmas ferramentas por MCP e por REST."""

import anyio
from starlette.testclient import TestClient

from arandu_motor.servidor import criar_app_http, mcp

FERRAMENTAS = {"executar", "trace", "rodar_suite", "diff_comportamental"}


def test_mcp_chama_diff_como_o_m3_vai_chamar():
    async def chamar():
        return await mcp.call_tool("diff_comportamental", {
            "codigo_aluno": "print(int(input()) + 1)",
            "codigo_ref": "print(int(input()) * 2)",
            "entrada": "3",
            "id_chamada": "hipotese-A",
        })

    d = anyio.run(chamar).structured_content
    assert d["id_chamada"] == "hipotese-A"
    assert d["divergiu"] is True
    assert (d["aluno"]["saida"], d["referencia"]["saida"]) == ("4", "6")
    assert d["aluno"]["trace"] == [{"linha": 1, "codigo": "print(int(input()) + 1)", "variaveis": {}, "imprimiu": "4"}]


def test_mcp_lista_as_quatro_ferramentas_com_esquema_de_saida():
    ferramentas = anyio.run(mcp.list_tools)
    assert {f.name for f in ferramentas} == FERRAMENTAS
    for f in ferramentas:
        assert f.description and f.output_schema, f.name
        assert f.annotations.read_only_hint is True


def test_mcp_chama_executar():
    async def chamar():
        return await mcp.call_tool("executar", {"codigo": "print(6 * 7)"})

    resultado = anyio.run(chamar)
    assert not resultado.is_error
    assert resultado.structured_content["saida"] == "42"


def test_mcp_chama_rodar_suite_com_testes():
    async def chamar():
        return await mcp.call_tool("rodar_suite", {
            "codigo": "print(int(input()) * 2)",
            "testes": [{"entrada": "2", "saida_esperada": "4"}, {"id": "x", "entrada": "3", "saida_esperada": "7"}],
        })

    suite = anyio.run(chamar).structured_content
    assert (suite["aprovados"], suite["total"]) == (1, 2)
    assert suite["resultados"][1]["teste_id"] == "x"


def test_rest_para_o_front():
    with TestClient(criar_app_http()) as cliente:
        assert set(cliente.get("/api").json()["ferramentas"]) == FERRAMENTAS
        r = cliente.post("/api/executar", json={"codigo": "print(input()[::-1])", "entrada": "arandu"})
        assert r.status_code == 200
        assert r.json()["saida"] == "udnara"
        assert cliente.post("/api/nao_existe", json={}).status_code == 404
        assert cliente.post("/api/executar", json={"cod": "x"}).status_code == 400
        assert cliente.post("/api/executar", content=b"isso nao e json").status_code == 400
