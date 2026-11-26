//========= 1. MEMÓRIA E CONSTANTES GLOBAIS ==============
function criarConfigGraficoPadrao() {
  return {
    tema: "classic",
    grid: "none",
    fundo: "white",
    ancorar_zero: true,
    fonte_familia: "sans",
    fonte_tamanho: 12,
    cor_texto: "#000000",
    angulo_x: 0,
    barra_erro: "se",
    mostrar_letras: true,
    mostrar_pontos: false,
    reg_equacao: true,
    reg_ic: true,
    reg_linetype: true,
    multi_rotulos: true,
    pca_elipse: true,
    legenda: "top",
    exportacao: "300_png",
    rotulo_x: "",
    rotulo_y: ""
  };
}

let catalogo = [];
let estado = {
  analiseAtual: null,
  dados: null,
  mostrarTabela: false,
  opcoesModelo: {},
  fatoresSelecionados: {},
  varsSelecionadas: new Set(),
  alfa: 0.05,
  paletaGraficos: ["#F2A33A", "#503C2C", "#2E7D6B", "#3B6998", "#C84B31"],
  indiceCorAtiva: 0,
  matizAtual: 34,
  graficoConfig: criarConfigGraficoPadrao()
};

const TITULOS_TOPO = {
  1: "Seleção de Análise",
  2: "Conexão e Leitura de Dados",
  3: "Mapeamento de Variáveis",
  4: "Parâmetros e Estúdio Gráfico",
  5: "Script R Gerado"
};

const SWATCHES_BASE = [
  "#000000", "#1C1C1C", "#383838", "#555555", "#717171", "#8E8E8E",
  "#AAAAAA", "#C6C6C6", "#DCDCDC", "#EBEBEB", "#F5F5F5", "#FFFFFF",
  "#503C2C", "#8C5832", "#C86D1F", "#F2A33A", "#F3CF8F", "#2E7D32",
  "#1B5E20", "#00838F", "#1565C0", "#283593", "#6A1B9A", "#AD1457"
];

const LABELS_RESUMO_GRAFICO = {
  tema: {
    classic: "Clássico (theme_classic)",
    bw: "Caixa Fechada (theme_bw)",
    minimal: "Minimalista (theme_minimal)",
    light: "Claro Suave (theme_light)"
  },
  grid: {
    none: "Sem grade",
    major_y: "Horizontais principais",
    major: "Principais (X e Y)",
    both: "Grade completa"
  },
  barra_erro: {
    se: "Erro Padrão (EPM)",
    sd: "Desvio Padrão (DP)",
    ci: "IC 95%",
    none: "Oculta"
  },
  exportacao: {
    "300_png": "PNG 300 DPI",
    "600_png": "PNG 600 DPI",
    "600_tiff": "TIFF 600 DPI",
    "pdf": "PDF Vetorial"
  }
};


//========= 2. SEGURANÇA HTML E IGNIÇÃO DO APP ==============
function escaparHtml(valor) {
  return String(valor ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function iniciarEasyR() {
  document.body.classList.add("theme-amber");
  const btnTema = document.getElementById("btn-tema");
  if (btnTema) btnTema.innerText = "Modo: Horizonte Âmbar";

  inicializarTooltips();
  sincronizarFormularioGrafico();

  if (!window.pywebview || !window.pywebview.api) return;
  catalogo = await window.pywebview.api.obter_catalogo();
  renderizarCatalogo();
  inicializarSeletorCores();
}

if (window.pywebview && window.pywebview.api) {
  iniciarEasyR();
} else {
  window.addEventListener("pywebviewready", iniciarEasyR);
}


//========= 3. NAVEGAÇÃO, TEMA E GUIA 1 (CATÁLOGO) ==============
function renderizarCatalogo() {
  const grid = document.getElementById("grid-delineamentos");
  grid.innerHTML = catalogo.map(item => {
    const tipCard = item.ajuda
      ? `<span class="help-tip" onclick="event.stopPropagation()" data-help="${escaparHtml(item.ajuda)}">?</span>`
      : "";

    return `
      <div class="design-card" onclick="escolherAnalise('${item.id}')">
        <div>
          <span class="tag">${escaparHtml(item.tag)}</span>
          <h3>${escaparHtml(item.nome)}${tipCard}</h3>
        </div>
        <span>${escaparHtml(item.descricao)}</span>
      </div>
    `;
  }).join("");
}

function escolherAnalise(id) {
  estado.analiseAtual = catalogo.find(c => c.id === id);
  estado.opcoesModelo = {};
  estado.fatoresSelecionados = {};
  estado.varsSelecionadas.clear();

  if (Array.isArray(estado.analiseAtual.opcoes_modelo)) {
    estado.analiseAtual.opcoes_modelo.forEach(op => {
      estado.opcoesModelo[op.chave] = op.padrao || (op.opcoes[0] ? op.opcoes[0].valor : "");
    });
  }

  document.getElementById("titulo-guia-2").innerText = `${estado.analiseAtual.nome} — Planilha`;
  abrirGuia(2);
}

function abrirGuia(numero) {
  [1, 2, 3, 4, 5].forEach(n => {
    document.getElementById(`guia-${n}`).classList.toggle("ativa", n === numero);
  });
  document.getElementById("subtitulo-topo").innerText = TITULOS_TOPO[numero];

  const btnNova = document.getElementById("btn-nova-analise");
  if (btnNova) {
    btnNova.style.display = numero === 1 ? "none" : "inline-flex";
  }
}

function alternarTema() {
  document.body.classList.toggle("theme-amber");
  const ativo = document.body.classList.contains("theme-amber");
  document.getElementById("btn-tema").innerText = ativo ? "Modo: Horizonte Âmbar" : "Modo: Claro Smooth";
}


//========= 4. GUIA 2 (PLANILHA, TABELA E ALERTAS) ==============
async function abrirPlanilha() {
  if (!window.pywebview) return;
  const res = await window.pywebview.api.selecionar_arquivo();
  if (res && res.ok) {
    aplicarDados(res);
  } else if (res && res.erro) {
    alert(res.erro);
  }
}

async function mudarAba(nomeAba) {
  if (!window.pywebview) return;
  const res = await window.pywebview.api.trocar_aba(nomeAba);
  if (res && res.ok) {
    aplicarDados(res);
  } else if (res && res.erro) {
    alert(res.erro);
  }
}

function aplicarDados(res) {
  estado.dados = res;
  estado.fatoresSelecionados = {};
  estado.varsSelecionadas.clear();

  document.getElementById("info-arquivo").innerHTML = `
    ${escaparHtml(res.nome_arquivo)} ${res.aba_atual ? `— Aba [${escaparHtml(res.aba_atual)}]` : ""}
    <small>${res.total_linhas} linhas × ${res.total_colunas} colunas identificadas</small>
  `;

  const selAba = document.getElementById("select-aba");
  if (res.abas && res.abas.length > 0) {
    selAba.disabled = false;
    selAba.innerHTML = res.abas.map(a =>
      `<option value="${escaparHtml(a)}" ${a === res.aba_atual ? "selected" : ""}>${escaparHtml(a)}</option>`
    ).join("");
  } else {
    selAba.disabled = true;
    selAba.innerHTML = `<option>CSV</option>`;
  }

  renderizarAreaTabela();
  renderizarAlertas();
}

function alternarVisualizacaoTabela() {
  estado.mostrarTabela = document.getElementById("chk-visualizar").checked;
  renderizarAreaTabela();
}

function renderizarAreaTabela() {
  const container = document.getElementById("container-tabela");
  if (!estado.dados) {
    container.innerHTML = `
      <div class="placeholder-box">
        <strong>Nenhuma planilha carregada</strong>
        <span>A visualização inicia desligada por padrão. Marque "Visualizar dados" acima caso queira inspecionar a tabela.</span>
      </div>
    `;
    return;
  }

  if (!estado.mostrarTabela) {
    container.innerHTML = `
      <div class="placeholder-box">
        <strong>Pré-visualização desligada</strong>
        <span>Arquivo "${escaparHtml(estado.dados.nome_arquivo)}" ativo (${estado.dados.total_linhas} linhas × ${estado.dados.total_colunas} colunas). Marque "Visualizar dados" acima para exibir a tabela.</span>
      </div>
    `;
    return;
  }

  const cabecalhos = estado.dados.cabecalhos || estado.dados.colunas.map(c => c.nome);
  const ths = cabecalhos.map(c => `<th>${escaparHtml(c)}</th>`).join("");
  const trs = estado.dados.linhas.map(linha =>
    `<tr>${linha.map(v => `<td>${escaparHtml(v)}</td>`).join("")}</tr>`
  ).join("");
  container.innerHTML = `<table><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table>`;
}

function renderizarAlertas() {
  const strip = document.getElementById("strip-alertas");
  if (!estado.dados) {
    strip.innerHTML = "";
    return;
  }
  const avisos = [];
  estado.dados.colunas.forEach(c => {
    if (c.alerta_texto) {
      avisos.push(`<span class="badge-warn">Coluna "${escaparHtml(c.nome)}" contém números em formato de texto</span>`);
    }
    if (c.nulos > 0) {
      avisos.push(`<span class="badge-warn">Coluna "${escaparHtml(c.nome)}" possui ${c.nulos} célula(s) vazia(s)</span>`);
    }
  });
  strip.innerHTML = avisos.join("");
}


//========= 5. GUIA 3 (FATORES, DUNNETT E VARIÁVEIS) ==============
//--- 5.1 Regras de Visibilidade e Dunnett ---
function campoVisivel(campo) {
  if (!campo.depende_de) return true;
  return Object.entries(campo.depende_de).every(
    ([chaveOp, valEsperado]) => estado.opcoesModelo[chaveOp] === valEsperado
  );
}

function ehAnaliseDunnett() {
  return (
    (estado.analiseAtual && estado.analiseAtual.id === "DUNNETT") ||
    estado.opcoesModelo.teste_posthoc === "DUNNETT"
  );
}

//--- 5.2 Abertura e Montagem dos Fatores ---
function irParaVariaveis() {
  if (!estado.dados) {
    alert("Selecione uma planilha antes de continuar.");
    return;
  }

  document.getElementById("titulo-guia-3").innerText = `${estado.analiseAtual.nome} — Variáveis`;
  renderizarControlesFatores();
  atualizarCheckboxes();
  abrirGuia(3);
}

function renderizarControlesFatores() {
  const boxFatores = document.getElementById("container-fatores");
  const cols = estado.dados.colunas || [];
  let html = "";

  if (Array.isArray(estado.analiseAtual.opcoes_modelo)) {
    estado.analiseAtual.opcoes_modelo.forEach(op => {
      const tipOp = op.ajuda
        ? `<span class="help-tip" data-help="${escaparHtml(op.ajuda)}">?</span>`
        : "";
      const opcoesHtml = op.opcoes.map(item =>
        `<option value="${escaparHtml(item.valor)}" ${estado.opcoesModelo[op.chave] === item.valor ? "selected" : ""}>${escaparHtml(item.texto)}</option>`
      ).join("");

      html += `
        <div class="campo-fator">
          <label>${escaparHtml(op.rotulo)}${tipOp}</label>
          <select class="dune-select dune-select-full" onchange="alterarOpcaoModelo('${op.chave}', this.value)">
            ${opcoesHtml}
          </select>
        </div>
      `;
    });
  }

  (estado.analiseAtual.campos || []).forEach(campo => {
    if (!campoVisivel(campo)) return;

    const tipCampo = campo.ajuda
      ? `<span class="help-tip" data-help="${escaparHtml(campo.ajuda)}">?</span>`
      : "";
    const valorAtual = estado.fatoresSelecionados[campo.chave] || "";
    const placeholder = campo.obrigatorio ? "— Selecione uma coluna —" : "(Nenhuma)";
    const opcoesCols = cols.map(c => {
      const usadoEmOutro = Object.entries(estado.fatoresSelecionados).some(
        ([k, v]) => k !== campo.chave && k !== "controle" && v === c.nome
      );
      const infoNiveis = typeof c.n_unicos === "number" ? ` (${c.n_unicos} níveis)` : "";
      return `<option value="${escaparHtml(c.nome)}" ${valorAtual === c.nome ? "selected" : ""} ${usadoEmOutro ? "disabled" : ""}>${escaparHtml(c.nome)}${infoNiveis}${usadoEmOutro ? " [já usado]" : ""}</option>`;
    }).join("");

    html += `
      <div class="campo-fator">
        <label>${escaparHtml(campo.rotulo)}${tipCampo}</label>
        <select class="dune-select dune-select-full" id="fator-${campo.chave}" onchange="alterarFator('${campo.chave}', this.value)">
          <option value="">${placeholder}</option>
          ${opcoesCols}
        </select>
      </div>
    `;
  });

  if (ehAnaliseDunnett()) {
    const colTrat = estado.fatoresSelecionados.tratamento || "";
    const colObj = cols.find(c => c.nome === colTrat);
    const niveis = colObj && Array.isArray(colObj.valores_unicos) ? colObj.valores_unicos : [];
    const ctrlAtual = estado.fatoresSelecionados.controle || "";

    const opcoesCtrl = colTrat
      ? `<option value="">— Escolha qual nível é o Controle —</option>` +
        niveis.map(nv => `<option value="${escaparHtml(nv)}" ${ctrlAtual === nv ? "selected" : ""}>${escaparHtml(nv)}</option>`).join("")
      : `<option value="">— Selecione primeiro a Coluna de Tratamento —</option>`;

    html += `
      <div class="campo-fator">
        <label>Tratamento Controle / Testemunha *<span class="help-tip" data-help="Selecione qual nível da coluna de tratamentos corresponde à testemunha (controle) contra a qual todos os demais serão comparados.">?</span></label>
        <select class="dune-select dune-select-full" id="fator-controle" ${colTrat ? "" : "disabled"} onchange="alterarFator('controle', this.value)">
          ${opcoesCtrl}
        </select>
      </div>
    `;
  }

  boxFatores.innerHTML = html;
}

function alterarOpcaoModelo(chave, valor) {
  estado.opcoesModelo[chave] = valor;
  (estado.analiseAtual.campos || []).forEach(c => {
    if (!campoVisivel(c)) {
      delete estado.fatoresSelecionados[c.chave];
    }
  });
  if (!ehAnaliseDunnett()) {
    delete estado.fatoresSelecionados.controle;
  }
  renderizarControlesFatores();
  atualizarCheckboxes();
}

function alterarFator(chave, valor) {
  if (valor) {
    estado.fatoresSelecionados[chave] = valor;
    if (chave !== "controle") {
      estado.varsSelecionadas.delete(valor);
    }
  } else {
    delete estado.fatoresSelecionados[chave];
  }
  if (chave === "tratamento") {
    delete estado.fatoresSelecionados.controle;
  }
  renderizarControlesFatores();
  atualizarCheckboxes();
}

//--- 5.3 Checkboxes das Variáveis Resposta ---
function fatoresEmUso() {
  const usados = new Set();
  Object.entries(estado.fatoresSelecionados).forEach(([chave, val]) => {
    if (chave !== "controle" && val) usados.add(val);
  });
  return usados;
}

function marcarTodasNumericas() {
  const usados = fatoresEmUso();
  estado.varsSelecionadas.clear();
  estado.dados.colunas.forEach(c => {
    if ((c.numerica || c.alerta_texto) && !usados.has(c.nome)) {
      estado.varsSelecionadas.add(c.nome);
    }
  });
  atualizarCheckboxes();
}

function limparSelecaoVars() {
  estado.varsSelecionadas.clear();
  atualizarCheckboxes();
}

function atualizarCheckboxes() {
  const box = document.getElementById("lista-variaveis");
  const usados = fatoresEmUso();

  box.innerHTML = estado.dados.colunas.map(c => {
    const ehFator = usados.has(c.nome);
    if (ehFator) estado.varsSelecionadas.delete(c.nome);

    const checked = estado.varsSelecionadas.has(c.nome) ? "checked" : "";
    const disabled = ehFator ? "disabled" : "";
    const tipo = ehFator ? "fator" : (c.numerica ? "num" : (c.alerta_texto ? "txt/num" : "txt"));
    const nomeEsc = c.nome.replace(/\\/g, "\\\\").replace(/'/g, "\\'");

    return `
      <label class="var-chip" style="${ehFator ? "opacity:0.45; cursor:not-allowed;" : ""}">
        <input type="checkbox" ${checked} ${disabled} onchange="alternarVar('${nomeEsc}', this.checked)" />
        <span>${escaparHtml(c.nome)} <small class="var-tipo">(${tipo})</small></span>
      </label>
    `;
  }).join("");
}

function alternarVar(nome, ativo) {
  if (ativo) estado.varsSelecionadas.add(nome);
  else estado.varsSelecionadas.delete(nome);
}


//========= 6. GUIA 4 (SIGNIFICÂNCIA, CORES E ESTÚDIO GRÁFICO) ==============
//--- 6.1 Validação da Guia 3 e Adaptação da Guia 4 ---
function irParaParametros() {
  for (const campo of (estado.analiseAtual.campos || [])) {
    if (campoVisivel(campo) && campo.obrigatorio && !estado.fatoresSelecionados[campo.chave]) {
      alert(`Selecione a coluna correspondente a: ${campo.rotulo}`);
      return;
    }
  }

  if (ehAnaliseDunnett() && !estado.fatoresSelecionados.controle) {
    alert("Selecione qual nível é o Tratamento Controle / Testemunha para o teste de Dunnett.");
    return;
  }

  const minResp = estado.analiseAtual.min_respostas || 1;
  if (estado.varsSelecionadas.size < minResp) {
    alert(minResp > 1
      ? `Selecione pelo menos ${minResp} variáveis resposta antes de prosseguir.`
      : "Selecione pelo menos uma variável resposta antes de prosseguir."
    );
    return;
  }

  const idAnalise = estado.analiseAtual.id;
  const usaAlfa = Boolean(estado.analiseAtual.usa_pvalor);
  const usaGrafico = Boolean(estado.analiseAtual.usa_grafico);

  if (usaAlfa && usaGrafico) {
    document.getElementById("titulo-guia-4").innerText = `${estado.analiseAtual.nome} — Significância e Estúdio Gráfico`;
    document.getElementById("desc-guia-4").innerText =
      "Defina o nível de significância (α), a paleta de cores e os detalhes científicos das figuras.";
  } else if (usaAlfa) {
    document.getElementById("titulo-guia-4").innerText = `${estado.analiseAtual.nome} — Parâmetros Estatísticos`;
    document.getElementById("desc-guia-4").innerText =
      "Defina o nível de significância (α) para o teste de hipóteses e comparação de médias.";
  } else if (usaGrafico) {
    document.getElementById("titulo-guia-4").innerText = `${estado.analiseAtual.nome} — Estúdio Gráfico Científico`;
    document.getElementById("desc-guia-4").innerText =
      "Análise exploratória sem teste de hipóteses (sem α). Personalize as cores, eixos, fonte e resolução das figuras.";
  } else {
    document.getElementById("titulo-guia-4").innerText = `${estado.analiseAtual.nome} — Configuração`;
    document.getElementById("desc-guia-4").innerText =
      "Esta análise gera tabelas estatísticas completas sem figuras.";
  }

  document.getElementById("bloco-pvalor").style.display = usaAlfa ? "block" : "none";
  document.getElementById("bloco-paleta").style.display = usaGrafico ? "block" : "none";
  document.getElementById("bloco-estilo-grafico").style.display = usaGrafico ? "flex" : "none";
  document.getElementById("aviso-sem-grafico").style.display = (!usaAlfa && !usaGrafico) ? "block" : "none";

  const gridParam = document.getElementById("grid-parametros");
  if (usaGrafico) {
    gridParam.style.gridTemplateColumns = "0.92fr 1.08fr";
    gridParam.style.maxWidth = "none";
    adaptarCamadasEstatisticas(idAnalise);
    sincronizarFormularioGrafico();
    renderizarPaleta();
    desenharEspectro(estado.matizAtual);
  } else {
    gridParam.style.gridTemplateColumns = "1fr";
    gridParam.style.maxWidth = "560px";
  }

  abrirGuia(4);
}

function adaptarCamadasEstatisticas(idAnalise) {
  const ehMedias = ["DIC", "DBC", "FATORIAL", "SUBDIVIDIDA", "TUKEY", "SCOTT_KNOTT", "DUNNETT", "SCHEFFE"].includes(idAnalise);
  const ehRegressao = idAnalise === "REGRESSAO";
  const ehBoxplot = idAnalise === "BOXPLOT";
  const ehMultivariada = ["PCA", "CORRELACAO", "AGRUPAMENTO"].includes(idAnalise);
  const ehPca = idAnalise === "PCA";

  document.getElementById("grp-barras-erro").style.display = (ehMedias || ehRegressao) ? "flex" : "none";
  document.getElementById("grp-letras").style.display = ehMedias ? "flex" : "none";
  document.getElementById("grp-pontos").style.display = (ehMedias || ehBoxplot || ehRegressao) ? "flex" : "none";
  document.getElementById("grp-reg-eq").style.display = ehRegressao ? "flex" : "none";
  document.getElementById("grp-reg-ic").style.display = ehRegressao ? "flex" : "none";
  document.getElementById("grp-reg-linetype").style.display = ehRegressao ? "flex" : "none";
  document.getElementById("grp-multi-rotulos").style.display = ehMultivariada ? "flex" : "none";
  document.getElementById("grp-pca-elipse").style.display = ehPca ? "flex" : "none";
}

function atualizarConfigGrafico(chave, valor) {
  estado.graficoConfig[chave] = valor;
}

function resetarConfigGrafico() {
  estado.graficoConfig = criarConfigGraficoPadrao();
  sincronizarFormularioGrafico();
}

function sincronizarFormularioGrafico() {
  const c = estado.graficoConfig;
  const setVal = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.value = String(val);
  };

  setVal("cfg-tema", c.tema);
  setVal("cfg-grid", c.grid);
  setVal("cfg-fundo", c.fundo);
  setVal("cfg-ancorar-zero", c.ancorar_zero);
  setVal("cfg-fonte-familia", c.fonte_familia);
  setVal("cfg-fonte-tamanho", c.fonte_tamanho);
  setVal("cfg-cor-texto", c.cor_texto);
  setVal("cfg-angulo-x", c.angulo_x);
  setVal("cfg-barra-erro", c.barra_erro);
  setVal("cfg-mostrar-letras", c.mostrar_letras);
  setVal("cfg-mostrar-pontos", c.mostrar_pontos);
  setVal("cfg-reg-equacao", c.reg_equacao);
  setVal("cfg-reg-ic", c.reg_ic);
  setVal("cfg-reg-linetype", c.reg_linetype);
  setVal("cfg-multi-rotulos", c.multi_rotulos);
  setVal("cfg-pca-elipse", c.pca_elipse);
  setVal("cfg-legenda", c.legenda);
  setVal("cfg-exportacao", c.exportacao);
  setVal("cfg-rotulo-x", c.rotulo_x);
  setVal("cfg-rotulo-y", c.rotulo_y);
}

//--- 6.2 Controles de Nível de Significância (α) ---
function selecionarAlfa(valor) {
  estado.alfa = valor;
  document.getElementById("input-alfa").value = valor;
  document.querySelectorAll(".alfa-pill").forEach(pill => {
    pill.classList.toggle("ativo", parseFloat(pill.dataset.val) === valor);
  });
}

function atualizarAlfaManual(valorStr) {
  const num = parseFloat(valorStr);
  if (!isNaN(num) && num > 0 && num < 1) {
    estado.alfa = num;
    document.querySelectorAll(".alfa-pill").forEach(pill => {
      pill.classList.toggle("ativo", Math.abs(parseFloat(pill.dataset.val) - num) < 0.0001);
    });
  }
}

//--- 6.3 Motor Gráfico do Espectro Canvas e Swatches ---
function inicializarSeletorCores() {
  const grid = document.getElementById("grid-swatches");
  if (!grid) return;
  grid.innerHTML = SWATCHES_BASE.map(hex => `
    <div class="swatch-btn" style="background:${hex};" title="${hex}" onclick="aplicarCorSelecionada('${hex}')"></div>
  `).join("");

  const canvas = document.getElementById("canvas-espectro");
  const clicarCanvas = (evento) => {
    const rect = canvas.getBoundingClientRect();
    const x = Math.max(0, Math.min(canvas.width - 1, Math.round((evento.clientX - rect.left) * (canvas.width / rect.width))));
    const y = Math.max(0, Math.min(canvas.height - 1, Math.round((evento.clientY - rect.top) * (canvas.height / rect.height))));
    const ctx = canvas.getContext("2d");
    const pixel = ctx.getImageData(x, y, 1, 1).data;
    const hex = rgbParaHex(pixel[0], pixel[1], pixel[2]);
    aplicarCorSelecionada(hex);
  };

  let arrastando = false;
  canvas.addEventListener("mousedown", (e) => { arrastando = true; clicarCanvas(e); });
  window.addEventListener("mousemove", (e) => { if (arrastando) clicarCanvas(e); });
  window.addEventListener("mouseup", () => { arrastando = false; });

  desenharEspectro(estado.matizAtual);
  renderizarPaleta();
}

function desenharEspectro(matiz) {
  const canvas = document.getElementById("canvas-espectro");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;

  ctx.fillStyle = `hsl(${matiz}, 100%, 50%)`;
  ctx.fillRect(0, 0, w, h);

  const gradBranco = ctx.createLinearGradient(0, 0, w, 0);
  gradBranco.addColorStop(0, "#FFFFFF");
  gradBranco.addColorStop(1, "rgba(255, 255, 255, 0)");
  ctx.fillStyle = gradBranco;
  ctx.fillRect(0, 0, w, h);

  const gradPreto = ctx.createLinearGradient(0, 0, 0, h);
  gradPreto.addColorStop(0, "rgba(0, 0, 0, 0)");
  gradPreto.addColorStop(1, "#000000");
  ctx.fillStyle = gradPreto;
  ctx.fillRect(0, 0, w, h);
}

function mudarMatiz(valor) {
  estado.matizAtual = Number(valor);
  desenharEspectro(estado.matizAtual);
}

function rgbParaHex(r, g, b) {
  return "#" + [r, g, b].map(v => v.toString(16).padStart(2, "0")).join("").toUpperCase();
}

//--- 6.4 Gerenciamento dos Slots da Paleta ---
function aplicarCorSelecionada(hex) {
  const formatado = hex.toUpperCase();
  estado.paletaGraficos[estado.indiceCorAtiva] = formatado;
  document.getElementById("input-hex").value = formatado;
  document.getElementById("preview-cor").style.background = formatado;
  renderizarPaleta();
}

function digitarHex(texto) {
  let limpo = texto.trim().toUpperCase();
  if (!limpo.startsWith("#")) limpo = "#" + limpo;
  if (/^#[0-9A-F]{6}$/.test(limpo)) {
    estado.paletaGraficos[estado.indiceCorAtiva] = limpo;
    document.getElementById("preview-cor").style.background = limpo;
    renderizarPaleta();
  }
}

function selecionarSlotCor(indice) {
  estado.indiceCorAtiva = indice;
  const cor = estado.paletaGraficos[indice];
  document.getElementById("lbl-slot-ativo").innerText = `Cor ${indice + 1}`;
  document.getElementById("input-hex").value = cor;
  document.getElementById("preview-cor").style.background = cor;
  renderizarPaleta();
}

function adicionarSlotCor() {
  if (estado.paletaGraficos.length >= 10) return;
  estado.paletaGraficos.push("#8C5832");
  selecionarSlotCor(estado.paletaGraficos.length - 1);
}

function removerSlotCor(evento, indice) {
  evento.stopPropagation();
  if (estado.paletaGraficos.length <= 1) return;
  estado.paletaGraficos.splice(indice, 1);
  if (estado.indiceCorAtiva >= estado.paletaGraficos.length) {
    estado.indiceCorAtiva = estado.paletaGraficos.length - 1;
  }
  selecionarSlotCor(estado.indiceCorAtiva);
}

function renderizarPaleta() {
  const box = document.getElementById("container-paleta");
  if (!box) return;
  const corAtual = estado.paletaGraficos[estado.indiceCorAtiva] || "#F2A33A";
  document.getElementById("preview-cor").style.background = corAtual;
  document.getElementById("input-hex").value = corAtual;
  document.getElementById("lbl-slot-ativo").innerText = `Cor ${estado.indiceCorAtiva + 1}`;

  box.innerHTML = estado.paletaGraficos.map((cor, idx) => `
    <div class="cor-slot ${idx === estado.indiceCorAtiva ? "selecionado" : ""}" onclick="selecionarSlotCor(${idx})">
      <span class="cor-bolinha" style="background:${cor};"></span>
      <span>${cor}</span>
      ${estado.paletaGraficos.length > 1 ? `<span class="cor-remover" onclick="removerSlotCor(event, ${idx})">×</span>` : ""}
    </div>
  `).join("");
}


//========= 7. GUIA 5 (GERAÇÃO, RESUMO E EXPORTAÇÃO DO SCRIPT R) ==============
async function concluirConfiguracao() {
  if (!window.pywebview) return;

  const usaGrafico = Boolean(estado.analiseAtual.usa_grafico);
  const respostas = Array.from(estado.varsSelecionadas);
  const fatores = { ...estado.fatoresSelecionados };
  const cfgGraf = usaGrafico ? { ...estado.graficoConfig } : null;

  const payload = {
    analise_id: estado.analiseAtual.id,
    analise_nome: estado.analiseAtual.nome,
    arquivo: estado.dados.nome_arquivo,
    caminho_arquivo: estado.dados.caminho_arquivo,
    aba: estado.dados.aba_atual,
    ...estado.opcoesModelo,
    fatores: fatores,
    respostas: respostas,
    alfa: estado.analiseAtual.usa_pvalor ? estado.alfa : null,
    cores_graficos: usaGrafico ? [...estado.paletaGraficos] : [],
    grafico_config: cfgGraf
  };

  const res = await window.pywebview.api.registrar_mapeamento(payload);
  if (!res || !res.ok) {
    alert(res && res.erro ? res.erro : "Não foi possível gerar o código R.");
    return;
  }

  const chipsCores = payload.cores_graficos.map(c =>
    `<span class="chip-resumo-cor"><span class="bolinha-resumo-cor" style="background:${c};"></span>${c}</span>`
  ).join("");

  const fatoresTexto = Object.entries(fatores)
    .filter(([, v]) => v)
    .map(([k, v]) => `${escaparHtml(k)} = ${escaparHtml(v)}`)
    .join(" | ");

  const opcoesTexto = (estado.analiseAtual.opcoes_modelo || [])
    .map(op => {
      const val = estado.opcoesModelo[op.chave];
      const achado = op.opcoes.find(o => o.valor === val);
      return achado ? `<div><strong>${escaparHtml(op.rotulo)}:</strong> ${escaparHtml(achado.texto)}</div>` : "";
    })
    .join("");

  const pctAlfa = payload.alfa !== null
    ? Number((payload.alfa * 100).toFixed(2))
    : null;

  let resumoGraficoHtml = "";
  if (usaGrafico && cfgGraf) {
    const temaTxt = LABELS_RESUMO_GRAFICO.tema[cfgGraf.tema] || cfgGraf.tema;
    const gridTxt = LABELS_RESUMO_GRAFICO.grid[cfgGraf.grid] || cfgGraf.grid;
    const expTxt = LABELS_RESUMO_GRAFICO.exportacao[cfgGraf.exportacao] || cfgGraf.exportacao;
    const fonteTxt = cfgGraf.fonte_familia === "serif" ? "Times New Roman" : "Arial/Helvetica";

    resumoGraficoHtml = `
      <div><strong>Paleta:</strong> ${chipsCores}</div>
      <div><strong>Tema / Grade:</strong> ${escaparHtml(temaTxt)} · ${escaparHtml(gridTxt)}</div>
      <div><strong>Tipografia:</strong> ${escaparHtml(fonteTxt)} (${cfgGraf.fonte_tamanho} pt, cor ${escaparHtml(cfgGraf.cor_texto)})</div>
      <div><strong>Exportação:</strong> ${escaparHtml(expTxt)}</div>
    `;
  }

  document.getElementById("box-resumo-final").innerHTML = `
    <div><strong>Análise:</strong> ${escaparHtml(payload.analise_nome)} (${escaparHtml(payload.analise_id)})</div>
    <div><strong>Planilha:</strong> ${escaparHtml(payload.arquivo)} ${payload.aba ? `[Aba: ${escaparHtml(payload.aba)}]` : ""}</div>
    ${opcoesTexto}
    ${fatoresTexto ? `<div><strong>Fatores / Estrutura:</strong> ${fatoresTexto}</div>` : ""}
    <div><strong>Variáveis (${respostas.length}):</strong> ${escaparHtml(respostas.join(", "))}</div>
    ${payload.alfa !== null ? `<div><strong>Significância (α):</strong> ${payload.alfa} (${pctAlfa}%)</div>` : ""}
    ${resumoGraficoHtml}
  `;

  document.getElementById("titulo-guia-5").innerText = `${payload.analise_nome} — Script R`;
  document.getElementById("output-script-r").value = res.script;
  abrirGuia(5);
}

async function copiarScriptR() {
  const texto = document.getElementById("output-script-r").value;
  if (!texto) return;
  await navigator.clipboard.writeText(texto);
  const btn = document.getElementById("btn-copiar-r");
  btn.innerText = "Copiado!";
  setTimeout(() => { btn.innerText = "Copiar Código"; }, 1800);
}

async function salvarScriptR() {
  if (!window.pywebview) return;
  const texto = document.getElementById("output-script-r").value;
  if (!texto) return;
  const nomeBase = `${estado.analiseAtual.id.toLowerCase()}_easyr.R`;
  const res = await window.pywebview.api.salvar_script_r(texto, nomeBase);
  if (res && res.ok) {
    alert(`Script salvo em:\n${res.caminho}`);
  } else if (res && res.erro) {
    alert(res.erro);
  }
}


//========= 8. POP-UP DE AJUDA INSTANTÂNEO (TOOLTIPS) ==============
function inicializarTooltips() {
  if (document.getElementById("easyr-tooltip")) return;

  const box = document.createElement("div");
  box.id = "easyr-tooltip";
  box.className = "easyr-tooltip-box";
  document.body.appendChild(box);

  document.addEventListener("mouseover", (e) => {
    const alvo = e.target.closest(".help-tip");
    if (!alvo) return;

    const texto = alvo.getAttribute("data-help") || "";
    if (!texto) return;

    box.textContent = texto;
    box.style.display = "block";

    const rect = alvo.getBoundingClientRect();
    const tipRect = box.getBoundingClientRect();

    let top = rect.top - tipRect.height - 8;
    if (top < 8) {
      top = rect.bottom + 8;
    }

    let left = rect.left + (rect.width / 2) - (tipRect.width / 2);
    left = Math.max(8, Math.min(window.innerWidth - tipRect.width - 8, left));

    box.style.top = `${Math.round(top)}px`;
    box.style.left = `${Math.round(left)}px`;
  });

  document.addEventListener("mouseout", (e) => {
    if (e.target.closest(".help-tip")) {
      box.style.display = "none";
    }
  });
}

//========= 9. CONTROLE DOS MODAIS DE SUPORTE, CONTATO E LICENÇA ==============
const TEXTO_PLACEHOLDER_VIDEO = "Assista a tutoriais passo a passo para aprender a importar suas planilhas e gerar seus scripts no EasyR com segurança. ";
const TEXTO_PLACEHOLDER_CONTATO = "Dúvidas, sugestões de novas análises estatísticas ou parcerias acadêmicas? Entre  em contato pelo e-mail abaixo! Caso queira saber mais sobre minha persona acesse meu Currículo Lattes.";
const TEXTO_PLACEHOLDER_LICENCA = `EasyR — Copyright © 2026 Neivaldo Messias M. Ribeiro Júnior. Este software é livre e de código aberto, distribuído sem fins lucrativos à comunidade acadêmica sob a licença GNU GPL-3.0. Você pode usar, compartilhar e adaptar o programa livremente, desde que eventuais versões modificadas mantenham o código aberto sob a mesma licença. Não há obrigação de citação, mas uma menção opcional nos agradecimentos do seu trabalho ajuda a espalhar a ferramenta para outros pesquisadores.`;

function preencherPlaceholdersModais() {
  const elVideo = document.getElementById("txt-modal-video");
  const elContato = document.getElementById("txt-modal-contato");
  const elLicenca = document.getElementById("txt-modal-licenca");

  if (elVideo) elVideo.textContent = TEXTO_PLACEHOLDER_VIDEO;
  if (elContato) elContato.textContent = TEXTO_PLACEHOLDER_CONTATO;
  if (elLicenca) elLicenca.textContent = TEXTO_PLACEHOLDER_LICENCA;
}

function abrirModalInfo(tipo) {
  preencherPlaceholdersModais();

  const secoes = {
    video: "modal-sec-video",
    contato: "modal-sec-contato",
    licenca: "modal-sec-licenca"
  };

  Object.entries(secoes).forEach(([chave, idSec]) => {
    const el = document.getElementById(idSec);
    if (el) el.style.display = chave === tipo ? "block" : "none";
  });

  if (tipo === "licenca") {
    trocarAbaLicenca(1);
  }

  const overlay = document.getElementById("modal-info-overlay");
  if (overlay) overlay.classList.add("aberto");
}

function fecharModalInfo() {
  const overlay = document.getElementById("modal-info-overlay");
  if (overlay) overlay.classList.remove("aberto");
}

function fecharModalInfoPorFora(evento) {
  if (evento.target && evento.target.id === "modal-info-overlay") {
    fecharModalInfo();
  }
}

function trocarAbaLicenca(numero) {
  const p1 = document.getElementById("painel-lic-1");
  const p2 = document.getElementById("painel-lic-2");
  const t1 = document.getElementById("tab-lic-1");
  const t2 = document.getElementById("tab-lic-2");

  if (p1) p1.style.display = numero === 1 ? "flex" : "none";
  if (p2) p2.style.display = numero === 2 ? "flex" : "none";
  if (t1) t1.classList.toggle("ativo", numero === 1);
  if (t2) t2.classList.toggle("ativo", numero === 2);
}

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    fecharModalInfo();
  }
});