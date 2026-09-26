"use strict";
(function () {
  var ROTULOS_DEP = {
    forma_hipotese: "Forma hipóteses",
    testa_entrada_discriminante: "Testa entradas que expõem o erro",
    le_variaveis: "Lê os valores das variáveis",
    localiza_antes_de_editar: "Localiza o erro antes de editar",
  };
  var ORDEM_DEP = [
    "forma_hipotese",
    "testa_entrada_discriminante",
    "le_variaveis",
    "localiza_antes_de_editar",
  ];

  var selecionada = "";
  var sessoesAtuais = [];
  var detalheAoVivo = false;
  var emVoo = false;
  var pedidoDetalhe = 0;

  function $(id) { return document.getElementById(id); }

  function clonar(id) {
    var tpl = $(id);
    if (!tpl || !tpl.content || !tpl.content.firstElementChild) return null;
    return tpl.content.firstElementChild.cloneNode(true);
  }

  function num(v) {
    var n = Number(v);
    return Number.isFinite(n) ? n : 0;
  }

  function pct(v) {
    if (v == null || v === "") return null;
    var n = Number(v);
    if (!Number.isFinite(n)) return null;
    return Math.round(n * 100);
  }

  function quando(epoch) {
    var n = Number(epoch);
    var d = new Date((Number.isFinite(n) ? n : 0) * 1000);
    var data = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit" }).format(d);
    var hora = new Intl.DateTimeFormat("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hourCycle: "h23",
    }).format(d);
    return data + " às " + hora;
  }

  function formatarDuracao(segundos) {
    var s = Math.floor(Number(segundos));
    if (!Number.isFinite(s) || s < 0) s = 0;
    if (s < 60) return s + " s";
    var minTotal = Math.floor(s / 60);
    if (minTotal < 60) return minTotal + " min";
    var h = Math.floor(minTotal / 60);
    var m = minTotal % 60;
    var mm = (m < 10 ? "0" : "") + m;
    return h + " h " + mm + " min";
  }

  function motivoHumano(m) {
    if (m === "aluno pediu para sair") return "encerrada pelo aluno";
    if (m === "inatividade") return "encerrada por inatividade";
    if (m === "resolveu todos os bugs disponíveis") return "resolveu todos os desafios";
    if (m === "abandonada") return "aba fechada sem encerrar";
    if (m == null || m === "") return "—";
    return String(m);
  }

  function api(rota) {
    return fetch(rota, { cache: "no-store" }).then(function (resp) {
      return resp.json().catch(function () { return null; }).then(function (data) {
        if (!resp.ok || data == null) throw new Error("http");
        return data;
      });
    });
  }

  function gravarQuery(id) {
    var params = new URLSearchParams(location.search);
    if (id) params.set("sessao", id);
    else params.delete("sessao");
    var qs = params.toString();
    history.replaceState(null, "", location.pathname + (qs ? "?" + qs : "") + location.hash);
  }

  function listaViva(id) {
    var i;
    for (i = 0; i < sessoesAtuais.length; i++) {
      if (sessoesAtuais[i].id === id) return !!sessoesAtuais[i].em_andamento;
    }
    return false;
  }

  function marcarSelecao() {
    var linhas = $("listaSessoes").children;
    var i;
    for (i = 0; i < linhas.length; i++) {
      if (linhas[i].dataset.id === selecionada) linhas[i].setAttribute("aria-selected", "true");
      else linhas[i].removeAttribute("aria-selected");
    }
  }

  function montarLinha(s) {
    var tr = clonar("tpl-sessao");
    if (!tr) return null;
    tr.dataset.id = s.id || "";
    if (s.id === selecionada) tr.setAttribute("aria-selected", "true");
    tr.querySelector(".sessao__quando").textContent = quando(s.inicio);
    var est = tr.querySelector(".sessao__estado");
    if (s.em_andamento) {
      est.textContent = "em andamento";
      est.classList.add("sessao__estado--vivo");
    } else {
      est.textContent = motivoHumano(s.motivo_fim);
    }
    tr.querySelector(".sessao__duracao").textContent = formatarDuracao(s.duracao_s);
    tr.querySelector(".sessao__resolvidos").textContent = num(s.desafios_resolvidos) + "/" + num(s.desafios_iniciados);
    tr.querySelector(".sessao__dicas").textContent = String(num(s.dicas));
    var nota = pct(s.nota_media_explicacao);
    tr.querySelector(".sessao__nota").textContent = nota == null ? "—" : nota + "%";
    return tr;
  }

  function renderLista(lista) {
    var conhecidas = {};
    sessoesAtuais.forEach(function (s) { if (s.id) conhecidas[s.id] = true; });
    var tinha = sessoesAtuais.length > 0;
    sessoesAtuais = lista;
    var n = lista.length;
    $("contSessoes").textContent = n + (n === 1 ? " sessão" : " sessões");
    var vazio = $("sessoesVazio");
    var tabela = $("tabelaSessoes");
    if (!n) {
      vazio.hidden = false;
      tabela.hidden = true;
      $("listaSessoes").replaceChildren();
      return;
    }
    vazio.hidden = true;
    tabela.hidden = false;
    var rolagem = tabela.parentElement;
    var topo = rolagem ? rolagem.scrollTop : 0;
    var tb = $("listaSessoes");
    tb.replaceChildren();
    lista.forEach(function (s) {
      var tr = montarLinha(s);
      if (tr) tb.appendChild(tr);
    });
    if (rolagem) rolagem.scrollTop = topo;
    var topoLista = lista[0] && lista[0].id;
    if (topoLista && !selecionada) escolher(topoLista);
    else if (topoLista && tinha && !conhecidas[topoLista]) escolher(topoLista);
  }

  function pintarPill(el, tipo, texto) {
    el.classList.remove("pill--ok", "pill--sol", "pill--neutro");
    el.classList.add(tipo);
    el.textContent = texto;
  }

  function barra(box, nome, id, valor, sol) {
    var node = clonar("tpl-barra");
    if (!node) return;
    node.querySelector(".equivoco__nome").textContent = nome;
    node.querySelector(".equivoco__id").textContent = id || "";
    node.querySelector("b").textContent = valor + "%";
    var el = node.querySelector(".barra__valor");
    if (sol) el.classList.add("barra__valor--sol");
    el.style.setProperty("--v", String(valor));
    box.appendChild(node);
  }

  function preencherDominio(dom, rotulos) {
    var box = $("detDominio");
    box.replaceChildren();
    var mapa = dom && typeof dom === "object" ? dom : {};
    var ids = Object.keys(mapa);
    if (!ids.length) {
      var p = document.createElement("p");
      p.className = "stat__nota";
      p.textContent = "Sem dados ainda. O domínio aparece depois da primeira explicação.";
      box.appendChild(p);
      return;
    }
    ids.forEach(function (id) {
      var valor = pct(mapa[id]);
      if (valor == null) valor = 0;
      var nome = (rotulos && rotulos[id]) || id;
      barra(box, nome, id, valor, false);
    });
  }

  function preencherDepuracao(dep) {
    var box = $("detDepuracao");
    box.replaceChildren();
    var mapa = dep && typeof dep === "object" ? dep : {};
    var vistos = {};
    var chaves = [];
    ORDEM_DEP.forEach(function (k) {
      if (Object.prototype.hasOwnProperty.call(mapa, k)) {
        chaves.push(k);
        vistos[k] = true;
      }
    });
    Object.keys(mapa).forEach(function (k) {
      if (!vistos[k]) chaves.push(k);
    });
    chaves.forEach(function (k) {
      var valor = pct(mapa[k]);
      if (valor == null) valor = 0;
      barra(box, ROTULOS_DEP[k] || k, "", valor, true);
    });
  }

  function renderDesafios(s) {
    var tb = $("tabelaDesafios");
    tb.replaceChildren();
    var lista = Array.isArray(s.desafios) ? s.desafios : [];
    lista.forEach(function (d) {
      var tr = clonar("tpl-desafio");
      if (!tr || !d) return;
      tr.querySelector(".equivoco__nome").textContent = d.rotulo || d.equivoco || "";
      tr.querySelector(".equivoco__id").textContent = d.bug_id == null ? "" : String(d.bug_id);
      tr.querySelector(".desafio__tempo").textContent = formatarDuracao(d.duracao_s);
      tr.querySelector(".desafio__execucoes").textContent = String(num(d.execucoes));
      tr.querySelector(".desafio__expuseram").textContent = String(num(d.entradas_que_expuseram_o_erro));
      tr.querySelector(".desafio__submissoes").textContent = String(num(d.submissoes));
      var interv = d.intervencoes || {};
      tr.querySelector(".desafio__dicas").textContent = String(num(d.dicas_pedidas) + num(interv.DAR_DICA));
      var rub = d.rubrica;
      var nota = rub && rub.nota != null ? pct(rub.nota) : null;
      tr.querySelector(".desafio__nota").textContent = nota == null ? "—" : nota + "%";
      var sit = tr.querySelector(".desafio__situacao");
      if (d.resolvido) pintarPill(sit, "pill--ok", "resolvido");
      else if (d.fim == null && s.em_andamento) pintarPill(sit, "pill--sol", "em andamento");
      else pintarPill(sit, "pill--neutro", "não resolvido");
      tb.appendChild(tr);
    });
  }

  function renderDetalhe(s) {
    if (!s || typeof s !== "object") return;
    detalheAoVivo = !!s.em_andamento;
    $("detalheVazio").hidden = true;
    $("detalhe").hidden = false;
    $("detTitulo").textContent = "Sessão de " + quando(s.inicio);
    $("detMeta").textContent = (s.id || "") + " · " + (s.llm || "") + " · " + formatarDuracao(s.duracao_s);
    if (s.em_andamento) pintarPill($("detEstado"), "pill--sol", "em andamento");
    else pintarPill($("detEstado"), "pill--neutro", motivoHumano(s.motivo_fim));
    $("detResolvidos").textContent = String(num(s.desafios_resolvidos));
    $("detIniciados").textContent = "de " + num(s.desafios_iniciados) + " iniciados";
    $("detSubmissoes").textContent = String(num(s.submissoes));
    $("detDicas").textContent = String(num(s.dicas));
    var nota = pct(s.nota_media_explicacao);
    $("detNota").textContent = nota == null ? "—" : nota + "%";
    var custo = s.custo || {};
    var te = Number(custo.tokens_entrada) || 0;
    var ts = Number(custo.tokens_saida) || 0;
    var chamadas = custo.chamadas == null ? 0 : custo.chamadas;
    if (te + ts > 0) {
      $("detTokens").textContent = (te + ts).toLocaleString("pt-BR");
      $("detChamadas").textContent = chamadas + " chamadas ao modelo";
    } else {
      $("detTokens").textContent = String(chamadas);
      $("detChamadas").textContent = "chamadas (este modelo não conta tokens)";
    }
    renderDesafios(s);
    preencherDominio(s.dominio_por_equivoco, s.rotulos_equivocos);
    preencherDepuracao(s.depuracao);
  }

  function carregarLista() {
    return api("/sessoes").then(function (data) {
      if (!data || !Array.isArray(data.sessoes)) throw new Error("http");
      renderLista(data.sessoes);
    }).catch(function () { /* mantém a última lista */ });
  }

  function carregarDetalhe(id) {
    if (!id) return Promise.resolve();
    var ticket = ++pedidoDetalhe;
    return api("/sessoes/" + encodeURIComponent(id)).then(function (data) {
      if (ticket !== pedidoDetalhe || id !== selecionada) return;
      renderDetalhe(data);
    }).catch(function () { /* mantém o último detalhe */ });
  }

  function escolher(id) {
    if (!id) return;
    selecionada = id;
    marcarSelecao();
    gravarQuery(id);
    carregarDetalhe(id);
  }

  function ciclo() {
    if (emVoo) return;
    emVoo = true;
    carregarLista().then(function () {
      if (selecionada && (detalheAoVivo || listaViva(selecionada))) return carregarDetalhe(selecionada);
    }).then(function () {
      emVoo = false;
    }, function () {
      emVoo = false;
    });
  }

  $("listaSessoes").addEventListener("click", function (e) {
    var tr = e.target.closest("tr");
    if (!tr || !tr.dataset.id) return;
    escolher(tr.dataset.id);
  });

  $("btnAtualizar").addEventListener("click", ciclo);

  var inicial = new URLSearchParams(location.search).get("sessao");
  if (inicial) selecionada = inicial;
  emVoo = true;
  carregarLista().then(function () {
    if (selecionada) return carregarDetalhe(selecionada);
  }).then(function () {
    emVoo = false;
  }, function () {
    emVoo = false;
  });
  setInterval(ciclo, 2500);
})();
