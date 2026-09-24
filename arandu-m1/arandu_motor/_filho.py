"""Processo-filho do sandbox do Arandu (M1 -- motor de execução).

Este arquivo não é importado pelo pacote: o sandbox.py o executa num processo
Python separado (`python -S -s -B _filho.py`). Ele lê um trabalho em JSON pela
entrada padrão, roda cada programa pedido e devolve um resultado JSON por linha
num canal privado. O que o programa do aluno imprime fica capturado à parte e
nunca se mistura com os resultados.

Proteções (defesa em profundidade: serve para o hackathon, mas não é um
isolamento forte -- em produção, rode este mesmo filho dentro de um container):
  1. processo separado, sem site-packages e com ambiente limpo;
  2. orçamento de linhas executadas: pega laço infinito e diz em que linha;
  3. vigia de tempo por execução e teto para o texto impresso;
  4. `import` só de módulos da lista PERMITIDOS;
  5. gancho de auditoria (sys.addaudithook), que não pode ser removido depois
     de instalado: barra escrita em arquivo, processos, rede, ctypes etc.

Usa só a biblioteca padrão, de propósito.
"""

import ast
import builtins
import io
import json
import os
import random
import re
import reprlib
import sys
import threading
import time
import types
import warnings  # noqa: F401 -- o C importa sob demanda; carregamos antes de travar o import

import _strptime  # noqa: F401 -- idem, para datetime.strptime e time.strptime

ARQUIVO = "<aluno>"  # "nome de arquivo" do código do aluno nos rastros e erros

PERMITIDOS = frozenset({
    "math", "cmath", "random", "string", "re", "collections", "itertools",
    "functools", "operator", "heapq", "bisect", "copy", "array", "datetime",
    "time", "calendar", "statistics", "fractions", "decimal", "numbers",
    "typing", "dataclasses", "enum", "abc", "textwrap", "unicodedata",
    "pprint", "sys", "_strptime",
})

# Mesmo que o próprio filho já tenha carregado, o aluno não importa estes.
PROIBIDOS = frozenset({
    "os", "nt", "posix", "io", "_io", "subprocess", "socket", "_socket",
    "ctypes", "_ctypes", "shutil", "pathlib", "importlib", "_imp",
    "_frozen_importlib", "_frozen_importlib_external", "zipimport", "marshal",
    "winreg", "_winapi", "msvcrt", "signal", "_signal", "threading", "_thread",
    "multiprocessing", "builtins", "gc", "inspect", "tempfile", "pickle",
    "resource", "mmap", "select",
})

# Eventos de auditoria barrados (por prefixo). "open" é tratado à parte.
EVENTOS_BLOQUEADOS = (
    "os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.fork",
    "os.forkpty", "os.kill", "os.killpg", "os.startfile", "os.remove",
    "os.unlink", "os.rename", "os.replace", "os.rmdir", "os.mkdir", "os.chmod",
    "os.chown", "os.lchown", "os.chflags", "os.truncate", "os.symlink",
    "os.link", "os.putenv", "os.unsetenv", "os.chdir", "os.utime",
    "os.setxattr", "os.add_dll_directory", "os.mkfifo", "os.mknod",
    "subprocess.", "socket.", "ctypes.", "shutil.", "winreg.", "_winapi.",
    "msvcrt.", "webbrowser.", "urllib.", "http.", "ftplib.", "smtplib.",
    "imaplib.", "poplib.", "nntplib.", "telnetlib.", "sqlite3.", "resource.",
    "signal.", "_thread.start",
)

_FLAGS_ESCRITA = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC

# Só se lê arquivo de dentro da instalação do Python (para `import math` etc.).
_RAIZES_LEITURA = tuple(sorted({
    os.path.normcase(os.path.abspath(p)).rstrip("\\/") + os.sep
    for p in (sys.base_prefix, sys.prefix, sys.base_exec_prefix, sys.exec_prefix)
    if p
}))

_ESCOPOS_IGNORADOS = frozenset({"<listcomp>", "<dictcomp>", "<setcomp>", "<genexpr>", "<lambda>"})
_OCULTOS = (types.ModuleType, types.FunctionType, types.BuiltinFunctionType, types.MethodType, type)
_ENDERECO = re.compile(r" at 0x[0-9a-fA-F]+")
_RECURSAO_PADRAO = sys.getrecursionlimit()


class _Limite(BaseException):
    """Interrompe o programa do aluno ao estourar um limite.

    Herda de BaseException para não ser engolida por um `except Exception`."""

    def __init__(self, motivo):
        super().__init__(motivo)
        self.motivo = motivo


# --------------------------------------------------------------------------
# Proteções


def _checar_abertura(caminho, modo, flags):
    escrita = bool(flags & _FLAGS_ESCRITA) if modo is None else any(c in modo for c in "wax+")
    if escrita:
        raise PermissionError("o Arandu não permite escrever em arquivos")
    if isinstance(caminho, int):
        return  # descritor já aberto: nada novo é aberto
    try:
        alvo = os.path.normcase(os.path.abspath(os.fsdecode(caminho)))
    except (TypeError, ValueError):
        raise PermissionError("o Arandu não permite abrir arquivos") from None
    if not alvo.startswith(_RAIZES_LEITURA):
        raise PermissionError("o Arandu não permite abrir arquivos")


def _auditoria(evento, args):
    if evento == "open":
        _checar_abertura(*args[:3])
    elif evento.startswith(EVENTOS_BLOQUEADOS):
        raise PermissionError(f"operação não permitida no Arandu ({evento})")


def _sair(codigo=None):
    raise SystemExit(codigo)


def _builtins_do_aluno():
    """Cópia dos builtins com `import` vigiado (os de verdade ficam intactos)."""
    importar = builtins.__import__

    def importar_vigiado(nome, globais=None, locais=None, lista=(), nivel=0):
        raiz = nome.partition(".")[0]
        if nivel == 0 and raiz not in PERMITIDOS and (raiz in PROIBIDOS or raiz not in sys.modules):
            raise ImportError(f"o módulo '{nome}' não está disponível no Arandu")
        return importar(nome, globais, locais, lista, nivel)

    b = dict(builtins.__dict__)
    b["__import__"] = importar_vigiado
    b["exit"] = b["quit"] = _sair  # o -S remove os originais
    b["breakpoint"] = lambda *args, **kwargs: None
    return b


def _limitar_recursos(limites):
    try:
        import resource  # só existe em Linux/macOS
    except ImportError:
        return
    memoria = int(limites.get("memoria_mb", 512)) * 1024 * 1024
    for nome, valor in (("RLIMIT_AS", memoria), ("RLIMIT_CORE", 0)):
        try:
            resource.setrlimit(getattr(resource, nome), (valor, valor))
        except (AttributeError, ValueError, OSError):
            pass


def _abrir_canal():
    """Guarda o stdout verdadeiro só para os resultados e cala o descritor 1."""
    canal = os.dup(1)
    nulo = os.open(os.devnull, os.O_WRONLY)
    os.dup2(nulo, 1)
    os.close(nulo)
    return canal


# --------------------------------------------------------------------------
# Captura de saída e representação de valores


class _Saida(io.TextIOBase):
    """sys.stdout do aluno: guarda o texto em partes, com teto de tamanho."""

    def __init__(self, limite):
        self.partes = []
        self.tamanho = 0
        self.limite = limite

    def writable(self):
        return True

    def write(self, texto):
        if not isinstance(texto, str):
            raise TypeError(f"write() argument must be str, not {type(texto).__name__}")
        restante = self.limite - self.tamanho
        if len(texto) > restante:
            if restante > 0:
                self.partes.append(texto[:restante])
                self.tamanho = self.limite
            raise _Limite("saida")
        self.partes.append(texto)
        self.tamanho += len(texto)
        return len(texto)

    def desde(self, parte):
        return "".join(self.partes[parte:])

    def valor(self):
        return "".join(self.partes)


class _Repr(reprlib.Repr):
    """repr com limites de tamanho, que mantém a ordem dos dicionários."""

    def __init__(self):
        super().__init__()
        self.maxlevel = 4
        self.maxlist = self.maxtuple = self.maxset = self.maxfrozenset = 30
        self.maxdeque = self.maxarray = 30
        self.maxdict = 20
        self.maxstring = 120
        self.maxlong = 60
        self.maxother = 120

    def repr_dict(self, x, level):  # o reprlib ordenaria as chaves
        if not x:
            return "{}"
        if level <= 0:
            return "{...}"
        itens = [f"{self.repr1(k, level - 1)}: {self.repr1(x[k], level - 1)}" for k in list(x)[: self.maxdict]]
        if len(x) > self.maxdict:
            itens.append("...")
        return "{" + ", ".join(itens) + "}"


_REPR = _Repr()


def _repr_curto(valor):
    try:
        texto = _REPR.repr(valor)
    except Exception:
        texto = f"<{type(valor).__name__}>"
    return _ENDERECO.sub("", texto)  # endereços mudam a cada execução e atrapalham o diff


def _variaveis(quadro):
    variaveis = {}
    for nome, valor in list(quadro.f_locals.items()):
        if nome.startswith(("__", ".")) or isinstance(valor, _OCULTOS):
            continue
        variaveis[nome] = _repr_curto(valor)
    return variaveis


def _mensagem(excecao):
    try:
        texto = str(excecao)
    except Exception:
        texto = ""
    nome = type(excecao).__name__
    return f"{nome}: {texto}" if texto else nome


# --------------------------------------------------------------------------
# Rastreio (sys.settrace)


class _Rastreador:
    """Conta as linhas executadas e, se pedido, grava os passos.

    Cada passo descreve o estado DEPOIS de a linha terminar de executar."""

    def __init__(self, saida, gravar, max_linhas, max_passos, filtro_linhas):
        self.saida = saida
        self.gravar = gravar
        self.max_linhas = max_linhas
        self.max_passos = max_passos
        self.filtro = frozenset(filtro_linhas) if filtro_linhas else None
        self.linhas = 0
        self.linha_atual = None
        self.passos = []
        self.truncado = False
        self._pendente = {}  # quadro -> linha em execução nele
        self._excecao = {}  # quadro -> exceção levantada nele e ainda não resolvida
        self._profundidade = {}  # quadro -> 0 no programa principal, 1 numa função...
        self._parte = 0  # partes da saída já atribuídas a algum passo
        self._local = self._local_gravando if gravar else self._local_contando

    def chamada(self, quadro, evento, arg):
        codigo = quadro.f_code
        if codigo.co_filename != ARQUIVO or codigo.co_name in _ESCOPOS_IGNORADOS:
            return None
        if self.gravar:
            self._pendente[quadro] = None
            self._profundidade[quadro] = self._calcular_profundidade(quadro)
        return self._local

    def _calcular_profundidade(self, quadro):
        acima = quadro.f_back
        while acima is not None:
            if acima in self._profundidade:
                return self._profundidade[acima] + 1
            acima = acima.f_back
        # chamado de fora do programa do aluno (ex.: pela `chamada`)
        return 0 if quadro.f_code.co_name == "<module>" else 1

    def _contar(self, quadro):
        self.linhas += 1
        self.linha_atual = quadro.f_lineno
        if self.linhas > self.max_linhas:
            raise _Limite("linhas")

    def _local_contando(self, quadro, evento, arg):
        if evento == "line":
            self._contar(quadro)
        return self._local

    def _local_gravando(self, quadro, evento, arg):
        if evento == "line":
            self._contar(quadro)
            anterior = self._pendente.get(quadro)
            if anterior is not None:
                excecao = self._excecao.pop(quadro, None) if self._excecao else None
                self._registrar(quadro, anterior, excecao=excecao)
            self._pendente[quadro] = quadro.f_lineno
        elif evento == "return":
            anterior = self._pendente.pop(quadro, None)
            excecao = self._excecao.pop(quadro, None)
            if anterior is not None:
                if excecao is not None:
                    self._registrar(quadro, anterior, excecao=excecao)
                elif quadro.f_code.co_name == "<module>":
                    self._registrar(quadro, anterior)
                else:
                    self._registrar(quadro, anterior, retorno=_repr_curto(arg))
            self._profundidade.pop(quadro, None)
        elif evento == "exception":
            self._excecao[quadro] = _mensagem(arg[1])
        return self._local

    def _registrar(self, quadro, linha, **extra):
        nova_saida = self.saida.desde(self._parte)
        self._parte = len(self.saida.partes)
        if self.truncado or (self.filtro is not None and linha not in self.filtro):
            return
        codigo = quadro.f_code
        passo = {
            "passo": len(self.passos) + 1,
            "linha": linha,
            "funcao": getattr(codigo, "co_qualname", codigo.co_name),
            "profundidade": self._profundidade.get(quadro, 0),
            "variaveis": _variaveis(quadro),
        }
        if nova_saida:
            passo["saida"] = nova_saida
        for chave, valor in extra.items():
            if valor is not None:
                passo[chave] = valor
        if self.passos and len(passo) == 5 and _mesmo_estado(self.passos[-1], passo):
            return  # repetição sem novidade (ex.: compreensão de lista no Python 3.12+)
        if len(self.passos) >= self.max_passos:
            self.truncado = True
            return
        self.passos.append(passo)


def _mesmo_estado(a, b):
    return len(a) == 5 and all(a[k] == b[k] for k in ("linha", "funcao", "profundidade", "variaveis"))


# --------------------------------------------------------------------------
# Execução


class _Estado:
    """O que o vigia de tempo precisa saber sobre a execução em andamento."""

    def __init__(self, canal, limite_s):
        self.trava = threading.Lock()
        self.canal = canal
        self.limite_s = limite_s
        self.i = None
        self.inicio = None
        self.saida = None
        self.rastreador = None

    def enviar(self, resultado):  # chamar com a trava na mão
        dados = (json.dumps(resultado) + "\n").encode("ascii")
        while dados:
            dados = dados[os.write(self.canal, dados):]


def _vigiar(estado):
    """Se uma execução passa do tempo, responde por ela e encerra o processo."""
    while True:
        time.sleep(0.02)
        with estado.trava:
            if estado.inicio is None or time.perf_counter() - estado.inicio <= estado.limite_s:
                continue
            rastreador = estado.rastreador
            linha = rastreador.linha_atual
            resultado = {
                "i": estado.i,
                "saida": estado.saida.valor(),
                "erro": f"Tempo limite de {estado.limite_s:g} s excedido"
                        + (f" (linha {linha} em execução)" if linha else ""),
                "tipo_erro": "LimiteDeTempo",
                "linha_erro": linha,
                "tempo_ms": round(estado.limite_s * 1000, 2),
                "linhas_executadas": rastreador.linhas,
                "fim_do_processo": True,
            }
            if rastreador.gravar:
                resultado["passos"] = rastreador.passos
                resultado["truncado"] = True
            estado.enviar(resultado)
            os._exit(0)


def _compilar_chamada(chamada):
    """Compila o código que chama o programa (estilo Refactory).

    Como no Refactory: se a última instrução é uma expressão sem print(), o
    valor dela é impresso."""
    arvore = ast.parse(chamada, filename="<chamada>", mode="exec")
    ultima = arvore.body[-1] if arvore.body else None
    if isinstance(ultima, ast.Expr) and "print(" not in (ast.get_source_segment(chamada, ultima) or ""):
        impressao = ast.Call(func=ast.Name(id="print", ctx=ast.Load()), args=[ultima.value], keywords=[])
        arvore.body[-1] = ast.copy_location(ast.Expr(value=impressao), ultima)
        ast.fix_missing_locations(arvore)
    return compile(arvore, "<chamada>", "exec", dont_inherit=True)


def _linha_no_aluno(excecao):
    linha = None
    tb = excecao.__traceback__
    while tb is not None:
        if tb.tb_frame.f_code.co_filename == ARQUIVO:
            linha = tb.tb_lineno
        tb = tb.tb_next
    return linha


def _executar(pedido, limites, estado, builtins_aluno, i):
    gravar = bool(pedido.get("rastrear"))
    resultado = {
        "i": i, "saida": "", "erro": None, "tipo_erro": None, "linha_erro": None,
        "tempo_ms": 0.0, "linhas_executadas": 0,
    }
    if gravar:
        resultado["passos"] = []
        resultado["truncado"] = False

    try:
        programa = compile(pedido.get("codigo") or "", ARQUIVO, "exec", dont_inherit=True)
    except SyntaxError as e:  # inclui IndentationError e TabError
        resultado.update(
            erro=f"{type(e).__name__}: {e.msg}" + (f" (linha {e.lineno})" if e.lineno else ""),
            tipo_erro=type(e).__name__, linha_erro=e.lineno,
        )
        return resultado
    except (ValueError, TypeError) as e:  # ex.: byte nulo no código
        resultado.update(erro=_mensagem(e), tipo_erro=type(e).__name__)
        return resultado

    chamada = pedido.get("chamada")
    try:
        codigo_chamada = _compilar_chamada(chamada) if chamada and chamada.strip() else None
    except SyntaxError as e:
        resultado.update(erro=f"Chamada inválida: {e.msg}", tipo_erro="ChamadaInvalida")
        return resultado

    saida = _Saida(int(limites.get("max_saida", 64_000)))
    rastreador = _Rastreador(
        saida, gravar,
        max_linhas=int(limites.get("max_linhas", 3_000_000)),
        max_passos=int(pedido.get("max_passos") or limites.get("max_passos", 500)),
        filtro_linhas=pedido.get("linhas"),
    )
    espaco = {"__name__": "__main__", "__builtins__": builtins_aluno}
    random.seed(0)  # aluno e referência sorteiam os mesmos números
    originais = sys.stdin, sys.stdout, sys.stderr
    sys.stdin = io.StringIO(pedido.get("entrada") or "")
    sys.stdout = saida
    sys.stderr = _Saida(4_000)  # descartado: os juízes só olham o stdout
    with estado.trava:
        estado.i, estado.saida, estado.rastreador = i, saida, rastreador
        estado.inicio = inicio = time.perf_counter()

    erro = None
    sys.settrace(rastreador.chamada)
    try:
        exec(programa, espaco)
        if codigo_chamada is not None:
            exec(codigo_chamada, espaco)
    except SystemExit as e:
        if e.code not in (None, 0):
            erro = e
    except BaseException as e:  # noqa: BLE001 -- inclui _Limite e erros do aluno
        erro = e
    finally:
        sys.settrace(None)
        fim = time.perf_counter()
        with estado.trava:
            estado.inicio = None
        sys.stdin, sys.stdout, sys.stderr = originais
        sys.setrecursionlimit(_RECURSAO_PADRAO)

    resultado.update(
        saida=saida.valor(),
        tempo_ms=round((fim - inicio) * 1000, 2),
        linhas_executadas=rastreador.linhas,
    )
    if gravar:
        resultado["passos"] = rastreador.passos
        resultado["truncado"] = rastreador.truncado

    if isinstance(erro, _Limite):
        linha = rastreador.linha_atual
        if erro.motivo == "linhas":
            texto = (f"Limite de {rastreador.max_linhas:,} linhas executadas atingido"
                     " -- provável laço infinito").replace(",", ".")
            tipo = "LimiteDeLinhas"
        else:
            texto = f"Limite de {saida.limite:,} caracteres impressos atingido".replace(",", ".")
            tipo = "LimiteDeSaida"
        if linha:
            texto += f" (linha {linha})"
        resultado.update(erro=texto, tipo_erro=tipo, linha_erro=linha)
        if gravar:
            resultado["truncado"] = True
    elif erro is not None:
        linha = _linha_no_aluno(erro)
        onde = f" (linha {linha})" if linha else (" (na chamada)" if codigo_chamada else "")
        resultado.update(erro=_mensagem(erro) + onde, tipo_erro=type(erro).__name__, linha_erro=linha)
    return resultado


def main():
    trabalho = json.loads(sys.stdin.buffer.read())
    canal = _abrir_canal()
    limites = trabalho.get("limites") or {}
    _limitar_recursos(limites)
    estado = _Estado(canal, float(limites.get("tempo_s", 5.0)))
    threading.Thread(target=_vigiar, args=(estado,), daemon=True).start()
    builtins_aluno = _builtins_do_aluno()
    sys.addaudithook(_auditoria)  # daqui em diante, não há volta

    for i, pedido in enumerate(trabalho.get("execucoes") or []):
        resultado = _executar(pedido, limites, estado, builtins_aluno, i)
        with estado.trava:
            estado.enviar(resultado)
    os._exit(0)  # não roda atexit nem espera threads do aluno


if __name__ == "__main__":
    main()
