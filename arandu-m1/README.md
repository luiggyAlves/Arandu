# Arandu: M1, motor de execução + ferramentas (MCP)

A fundação do Arandu: roda o código do aluno num sandbox e expõe as quatro ferramentas do
[Contrato A](CONTRATO_A.md): `executar`, `trace`, `rodar_suite` e `diff_comportamental`. O agente (M3) as usa via
**MCP**, e o front (M4) via **REST**. O M1 só executa e relata; não levanta hipóteses nem tira conclusões (isso é
do M3).

**Configuração:** o [`m1.config`](m1.config) guarda os limites do sandbox, o endereço do servidor e as fronteiras
entre os módulos (o que é do M1 e o que é de cada um dos outros).

## Instalação

Só precisa de Python 3.10 ou mais novo. A única dependência é o pacote `mcp` (SDK oficial do protocolo, v2).

**Windows:**
- Evite pastas muito fundas: o `pip` falha nelas se o suporte a caminhos longos do Windows não estiver ligado.
- Se o projeto estiver no OneDrive, crie o venv **fora** dele (ex.: `C:\venvs\arandu-m1`); senão o OneDrive tenta
  sincronizar milhares de arquivos de pacotes.

Na pasta do projeto:

```bash
python -m venv C:\venvs\arandu-m1
C:\venvs\arandu-m1\Scripts\activate    # Linux/macOS: python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                              # 44 testes, cerca de 10 s
python exemplos/exemplo_diff.py     # o que o M1 devolve quando o M3 manda uma entrada
```

## Como cada módulo usa

**M2 (Python direto).** O Validador do laço Construtor↔Validador usa `rodar_suite`: o bug tem que falhar em algum
teste sem travar, e a referência tem que passar em todos. Veja a nota sobre os testes do Refactory no
[CONTRATO_A.md](CONTRATO_A.md).

```python
from arandu_motor import rodar_suite
rodar_suite(codigo, [{"entrada": "5\n", "saida_esperada": "15"}])
```

**M3 (agente, MCP).** O M3 escolhe a entrada a partir das hipóteses dele e chama `diff_comportamental` com o
código do aluno, o de referência e essa entrada. Recebe de volta `divergiu` e a saída e o trace de cada código;
a análise e a conclusão sobre as hipóteses são dele. Por stdio, o cliente sobe o servidor sozinho. Configuração no formato do Claude Desktop, do
Claude Agent SDK e da maioria dos clientes:

```json
{
  "mcpServers": {
    "arandu-motor": {
      "command": "C:\\venvs\\arandu-m1\\Scripts\\python.exe",
      "args": ["-m", "arandu_motor"]
    }
  }
}
```

Por HTTP: `python -m arandu_motor --http` e conectar em `http://127.0.0.1:8000/mcp`. Há um cliente de exemplo em
[`exemplos/cliente_mcp.py`](exemplos/cliente_mcp.py).

**M4 (front, REST).** Com o servidor HTTP no ar, `POST /api/<ferramenta>` com os argumentos em JSON (CORS liberado):

```js
const resp = await fetch("http://127.0.0.1:8000/api/trace", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ codigo, entrada: "5\n" }),
});
const { passos, saida, erro } = await resp.json();
```

**Equipe na mesma rede:** `python -m arandu_motor --http --host 0.0.0.0` e usem o IP da máquina. A porta padrão é
8000 (seção `[servidor]` do `m1.config`); se estiver ocupada, use `--porta`.

## Decisões de projeto

- **Trace = estado depois da linha**, com valores em `repr` (texto), gravado com o `sys.settrace` do próprio
  Python (o mesmo mecanismo do depurador `pdb`). Nenhuma LLM no M1.
- **O M1 não analisa os traces**: devolve os fatos (divergiu, saídas, traces) e o M3 interpreta.
- **O trace vai sempre junto** na resposta do `diff_comportamental`, com ou sem divergência (combinado com o M3).
- As mudanças em relação ao documento v1 estão no fim do [CONTRATO_A.md](CONTRATO_A.md), para discutir com a equipe.

## Sandbox: o que protege e o que não protege

Cada execução roda num processo Python separado, sem site-packages e com ambiente limpo:

- **Limites** (seção `[limites]` do `m1.config`): 5 s de relógio, 3 milhões de linhas executadas (pega laço infinito
  e diz a linha), 64 mil caracteres impressos e 512 MB de memória (este último só em Linux/macOS).
- **Módulos**: `import` só de uma lista de módulos seguros (`math`, `random`, `collections`...).
- **Operações**: um gancho de auditoria do Python barra escrita em arquivo, `os.system`/`subprocess`, rede e `ctypes`.
- **Tolerância a falhas**: um programa que trava não derruba os outros; o sandbox retoma num processo novo.

Isso é defesa em profundidade, suficiente para o hackathon (código de alunos e do LLM, em ambiente controlado).
**Não** é isolamento forte. Em produção, rode o processo-filho dentro de um container
(`docker run --network none --read-only --memory 256m ...`).

## Estrutura

```
arandu_motor/
  ferramentas.py     as 4 ferramentas (API Python)
  config.py          lê o m1.config
  contrato.py        formatos de entrada/saída (Contrato A em código)
  sandbox.py         lança e supervisiona os processos-filhos
  _filho.py          roda o código do aluno: limites, rastreio, proteções
  saidas.py          regras de comparação de saída
  servidor.py        MCP (stdio/HTTP) + REST
tests/               pytest (ferramentas e servidor)
exemplos/            exemplo_diff.py, cliente_mcp.py (para o M3)
m1.config            limites, servidor e fronteiras entre módulos
```
