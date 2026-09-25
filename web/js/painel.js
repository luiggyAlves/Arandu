"use strict";
(function () {
  var filtroAtual = "todos";
  var vistos = 0;
  var ultimo = null;
  var emVoo = false;

  function $(id) { return document.getElementById(id); }

  function clonar(id) {
    return $(id).content.firstElementChild.cloneNode(true);
  }

  function relogio(ts) {
    var d = new Date((typeof ts === "number" ? ts : 0) * 1000);
    var p = function (n) { return String(n).padStart(2, "0"); };
    return p(d.getHours()) + ":" + p(d.getMinutes()) + ":" + p(d.getSeconds());
  }

  function pct(v) {
    var n = Number(v);
    if (!Number.isFinite(n)) return null;
    return Math.round(n * 100);
  }

  function api(rota) {
    return fetch(rota, { cache: "no-store" }).then(function (resp) {
      return resp.json().catch(function () { return null; }).then(function (data) {
        if (!resp.ok || data == null) throw new Error("http");
        return data;
      });
    });
  }

  function tipoEfetivo(ev) {
    if (ev.tipo) return ev.tipo;
    if (ev.icone === "🔒") return "guard";
    if (ev.icone === "🔬") return "invest";
    return "aluno";
  }

  function casaFiltro(tipo, filtro) {
    if (filtro === "todos") return true;
    if (filtro === "dica") return tipo === "dica" || tipo === "fala";
    if (filtro === "aluno") return tipo === "aluno" || tipo === "trace";
    return tipo === filtro;
  }

  function montarEvento(ev) {
    var node = clonar("tpl-evento");
    var tipo = tipoEfetivo(ev);
    node.dataset.tipo = tipo;
    node.hidden = !casaFiltro(tipo, filtroAtual);
    node.querySelector(".evento__ic").textContent = ev.icone || "•";
    node.querySelector(".evento__tx").textContent = ev.texto || "";
    var time = node.querySelector("time");
    time.textContent = relogio(ev.ts);
    var tag = "";
    if (ev.acao) tag = String(ev.acao);
    else if (ev.rotulo) tag = String(ev.rotulo);
    else if (ev.nivel != null && ev.nivel !== "") tag = "nível " + ev.nivel;
    var tagEl = node.querySelector(".evento__tag");
    if (tag) {
      tagEl.hidden = false;
      tagEl.textContent = tag;
    }
    if (ev.confianca != null && ev.confianca !== "") {
      var c = Number(ev.confianca);
      if (Number.isFinite(c)) {
        var conf = node.querySelector(".conf");
        conf.hidden = false;
        conf.querySelector("i").style.setProperty("--v", String(Math.round(c * 100)));
        conf.querySelector(".conf__tx").textContent = Math.round(c * 100) + "%";
      }
    }
    window.AranduEvidencia && AranduEvidencia.preencher(node, ev);
    return node;
  }

  function mesmoEv(a, b) {
    return a && b && a.ts === b.ts && a.texto === b.texto && a.icone === b.icone;
  }

  function aplicarFiltro() {
    var feed = $("feed");
    Array.prototype.forEach.call(feed.children, function (el) {
      el.hidden = !casaFiltro(el.dataset.tipo || "", filtroAtual);
    });
  }

  function sincronizarFeed(eventos) {
    var feed = $("feed");
    var ok = vistos === 0 || (eventos.length >= vistos && mesmoEv(eventos[vistos - 1], ultimo));
    if (!ok) {
      feed.replaceChildren();
      vistos = 0;
      ultimo = null;
    }
    var i;
    for (i = vistos; i < eventos.length; i++) feed.appendChild(montarEvento(eventos[i]));
    vistos = eventos.length;
    ultimo = eventos.length ? eventos[eventos.length - 1] : null;
    $("feedVazio").hidden = eventos.length > 0;
    if ($("autoRolar").checked) {
      var sc = feed.closest(".card__corpo") || feed;
      sc.scrollTop = sc.scrollHeight;
    }
  }

  function contar(eventos, filtro) {
    var n = 0;
    eventos.forEach(function (ev) {
      if (casaFiltro(tipoEfetivo(ev), filtro)) n++;
    });
    return n;
  }

  function estadoLegivel(estado) {
    var map = {
      aluno_trabalhando: "Investigando",
      aguardando_explicacao: "Explicando",
      encerrada: "Encerrada",
      escolhendo_bug: "Aguardando",
    };
    return map[estado] || estado || "—";
  }

  function desafioAtual(eventos) {
    var i;
    for (i = eventos.length - 1; i >= 0; i--) {
      var t = eventos[i].texto || "";
      if (t.toLowerCase().indexOf("novo desafio") < 0) continue;
      var m = t.match(/novo desafio\s*\(([^)]+)\)/i);
      return m ? m[1] : "—";
    }
    return "—";
  }

  function renderStats(eventos, modelo, estado) {
    var decisoes = 0;
    var silencio = 0;
    var interv = 0;
    var experimentos = 0;
    var barradas = 0;
    var somaNivel = 0;
    var nNivel = 0;
    eventos.forEach(function (ev) {
      var tipo = tipoEfetivo(ev);
      if (tipo === "decisao") {
        decisoes++;
        if (ev.acao === "OBSERVAR") silencio++;
      }
      if (tipo === "dica" || tipo === "fala") interv++;
      if (tipo === "invest" && (ev.experimento || String(ev.texto || "").indexOf("experimento") === 0)) experimentos++;
      if (tipo === "guard") barradas++;
      if (ev.nivel != null && ev.nivel !== "") {
        var nv = Number(ev.nivel);
        if (Number.isFinite(nv)) {
          somaNivel += nv;
          nNivel++;
        }
      }
    });
    $("statDecisoes").textContent = String(decisoes);
    $("statSilencio").textContent = silencio + " foram de ficar em silêncio";
    $("statIntervencoes").textContent = String(interv);
    $("statExperimentos").textContent = String(experimentos);
    $("statBarradas").textContent = String(barradas);
    $("statNivel").textContent = nNivel ? (somaNivel / nNivel).toFixed(1) : "—";
    var resolvidos = (modelo && modelo.bugs_resolvidos) ? modelo.bugs_resolvidos.length : 0;
    $("statResolvidos").textContent = String(resolvidos);
    var qual = modelo ? pct(modelo.explicacao_qualidade) : null;
    $("statExplicacao").textContent = qual == null
      ? "qualidade da explicação: —"
      : "qualidade da explicação: " + qual + "%";
    $("estadoSessao").textContent = estadoLegivel(estado);
    $("bugAtual").textContent = desafioAtual(eventos);
    ["todos", "leitura", "decisao", "invest", "dica", "guard", "aluno"].forEach(function (f) {
      var el = document.querySelector('[data-cont="' + f + '"]');
      if (el) el.textContent = String(f === "todos" ? eventos.length : contar(eventos, f));
    });
  }

  function renderModelo(m) {
    if (!m) return;
    $("alunoId").textContent = m.id_aluno || "—";
    var box = $("dominio");
    box.replaceChildren();
    var dom = m.dominio_por_equivoco || {};
    var rot = m.rotulos_equivocos || {};
    var ids = Object.keys(dom);
    if (!ids.length) {
      var vazio = document.createElement("p");
      vazio.className = "stat__nota";
      vazio.textContent = "Sem dados ainda.";
      box.appendChild(vazio);
    } else {
      ids.forEach(function (id) {
        var node = clonar("tpl-dominio");
        node.querySelector(".equivoco__nome").textContent = rot[id] || id;
        node.querySelector(".equivoco__id").textContent = id;
        var valor = pct(dom[id]);
        if (valor == null) valor = 0;
        node.querySelector("b").textContent = valor + "%";
        node.querySelector(".barra__valor").style.setProperty("--v", String(valor));
        box.appendChild(node);
      });
    }
    var dep = m.depuracao || {};
    document.querySelectorAll("[data-hab]").forEach(function (el) {
      var v = pct(dep[el.getAttribute("data-hab")]);
      el.style.setProperty("--v", String(v == null ? 0 : v));
    });
    document.querySelectorAll("[data-hab-tx]").forEach(function (el) {
      var v = pct(dep[el.getAttribute("data-hab-tx")]);
      el.textContent = v == null ? "—" : v + "%";
    });
    var sinais = m.sinais_interface || {};
    document.querySelectorAll("[data-sinal]").forEach(function (el) {
      var v = sinais[el.getAttribute("data-sinal")];
      el.textContent = v == null ? "—" : String(v);
    });
  }

  function renderCusto(metricas) {
    if (!metricas || !metricas.custo) return;
    var c = metricas.custo;
    var te = Number(c.tokens_entrada) || 0;
    var ts = Number(c.tokens_saida) || 0;
    var chamadas = c.chamadas == null ? 0 : c.chamadas;
    var limite = c.limite == null ? 0 : c.limite;
    var el = $("metCusto");
    var nota = $("metCustoNota");
    if (te + ts > 0) {
      el.textContent = (te + ts).toLocaleString("pt-BR") + " tokens";
      nota.textContent = chamadas + " de " + limite + " chamadas ao modelo · "
        + te.toLocaleString("pt-BR") + " entrada / "
        + ts.toLocaleString("pt-BR") + " saída";
    } else {
      el.textContent = chamadas + " chamadas";
      nota.textContent = "de " + limite + " permitidas · o " + (metricas.llm || "") + " não conta tokens";
    }
    el.classList.add("metrica-exp__valor--medido");
  }

  function itemBanco(item, reprovado) {
    var li = clonar("tpl-item-banco");
    if (!item.valido) li.classList.add("item-banco--invalido");
    li.querySelector(".item-banco__id").textContent = item.bug_id == null ? "" : String(item.bug_id);
    li.querySelector(".item-banco__detalhe").textContent = item.valido ? "" : (item.detalhe || "");
    var origem = item.origem === "refactory" ? "real" : "gerado";
    if (reprovado) origem = "gerado · reprovado no M2";
    li.querySelector(".item-banco__origem").textContent = origem;
    var falhando = item.testes_falhando == null ? 0 : item.testes_falhando;
    var testes = item.testes_total == null ? 0 : item.testes_total;
    var linhas = item.linhas_alteradas == null ? 0 : item.linhas_alteradas;
    li.title = "testes falhando: " + falhando + " de " + testes + " · linhas alteradas: " + linhas;
    return li;
  }

  function renderBugs(data) {
    var geradas = data.geradas || {};
    var banco = data.banco || {};
    var total = Number(geradas.total) || 0;
    var aprov = Number(geradas.aprovadas_pelo_validador_m2) || 0;
    var el = $("metBugs");
    el.textContent = (total > 0 ? Math.round((aprov * 100) / total) : 0) + "%";
    el.classList.add("metrica-exp__valor--medido");
    var reval = geradas.revalidadas_validas == null ? 0 : geradas.revalidadas_validas;
    $("metBugsNota").textContent = aprov + " de " + total
      + " bugs gerados aprovados pelo Validador do M2 · "
      + reval + " confirmados rodando de novo agora";
    $("detBanco").hidden = false;
    $("detBancoResumo").textContent = "(" + (banco.validos || 0) + " de " + (banco.total || 0) + " em uso)";
    var lista = $("listaBanco");
    lista.replaceChildren();
    (banco.itens || []).forEach(function (item) {
      lista.appendChild(itemBanco(item, false));
    });
    (geradas.itens || []).forEach(function (item) {
      if (item && item.aprovado_por_validador_m2 === false) lista.appendChild(itemBanco(item, true));
    });
  }

  function carregarBugs() {
    api("/metricas/bugs").then(function (data) {
      if (!data || data.estado === "calculando") {
        setTimeout(carregarBugs, 3000);
        return;
      }
      if (data.estado === "erro") {
        var el = $("metBugs");
        el.textContent = "—";
        el.classList.remove("metrica-exp__valor--medido");
        $("metBugsNota").textContent = data.detalhe || "";
        return;
      }
      renderBugs(data);
    }).catch(function () {
      setTimeout(carregarBugs, 3000);
    });
  }

  function tick() {
    if (emVoo) return;
    emVoo = true;
    Promise.all([
      api("/painel").catch(function () { return null; }),
      api("/modelo").catch(function () { return null; }),
    ]).then(function (par) {
      var painel = par[0];
      var modelo = par[1];
      if (painel) {
        var eventos = painel.eventos || [];
        sincronizarFeed(eventos);
        renderStats(eventos, modelo, painel.estado);
        renderCusto(painel.metricas);
      }
      if (modelo) renderModelo(modelo);
    }).then(function () {
      emVoo = false;
    }, function () {
      emVoo = false;
    });
  }

  $("filtros").addEventListener("click", function (e) {
    var btn = e.target.closest(".chip[data-filtro]");
    if (!btn) return;
    filtroAtual = btn.getAttribute("data-filtro") || "todos";
    $("filtros").querySelectorAll(".chip[data-filtro]").forEach(function (chip) {
      chip.setAttribute("aria-pressed", chip === btn ? "true" : "false");
    });
    aplicarFiltro();
  });

  var ab = $("metAblacao");
  ab.textContent = "—";
  ab.title = "ainda não medido";

  api("/info").then(function (info) {
    $("infoLLM").textContent = "LLM: " + (info.llm || "") + " · " + (info.build || "");
  }).catch(function () { /* o painel segue sem o selo */ });

  carregarBugs();
  tick();
  setInterval(tick, 2500);
})();
