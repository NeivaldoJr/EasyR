#========= 1. GERENCIAMENTO DE PACOTES R ==============
def montar_cabecalho_pacotes(pacotes: list[str]) -> list[str]:
    itens = ", ".join(f'"{p}"' for p in pacotes)
    return [
        f"pacotes <- c({itens})",
        "instalar <- pacotes[!(pacotes %in% rownames(installed.packages()))]",
        'if (length(instalar) > 0) install.packages(instalar, repos = "https://cloud.r-project.org")',
        "invisible(lapply(pacotes, library, character.only = TRUE))",
    ]


#========= 2. LEITURA DE PLANILHA E RESOLUÇÃO DE COLUNAS ==============
def montar_leitura_dados(caminho: str, aba: str) -> list[str]:
    caminho_limpo = caminho.replace("\\", "/")
    linhas = []
    if aba:
        linhas.append(f'dados <- as.data.frame(read_excel("{caminho_limpo}", sheet = "{aba}"))')
    else:
        linhas.extend([
            f'primeira_linha <- readLines("{caminho_limpo}", n = 1, warn = FALSE)',
            'sep_csv <- ifelse(grepl(";", primeira_linha), ";", ",")',
            'dec_csv <- ifelse(sep_csv == ";", ",", ".")',
            f'dados <- read.csv("{caminho_limpo}", sep = sep_csv, dec = dec_csv, check.names = FALSE)',
        ])

    linhas.extend([
        "dados <- as.data.frame(dados)",
        'names(dados) <- trimws(sub("^\\ufeff", "", names(dados)))',
        "resolver_coluna_easyr <- function(df, alvo) {",
        "  alvo <- trimws(alvo)",
        "  if (alvo %in% names(df)) return(alvo)",
        "  idx_ci <- which(tolower(trimws(names(df))) == tolower(alvo))",
        "  if (length(idx_ci) > 0) return(names(df)[idx_ci[1]])",
        "  idx_mn <- which(make.names(names(df)) == make.names(alvo))",
        "  if (length(idx_mn) > 0) return(names(df)[idx_mn[1]])",
        '  stop(paste0("Coluna nao encontrada: \'", alvo, "\'. Disponiveis: ", paste(names(df), collapse = ", ")))',
        "}",
    ])
    return linhas


#========= 3. FORMATAÇÃO DA PALETA E CONFIGURAÇÃO GRÁFICA ==============
def montar_paleta_r(cores: list[str]) -> str:
    cores_validas = [c.strip() for c in cores if isinstance(c, str) and c.strip()]
    if not cores_validas:
        cores_validas = ["#F2A33A", "#503C2C", "#2E7D6B", "#3B6998", "#C84B31"]
    itens = ", ".join(f'"{c}"' for c in cores_validas)
    return f"c({itens})"


def escapar_texto_r(texto: str) -> str:
    return str(texto).replace("\\", "\\\\").replace('"', '\\"')


def obter_config_grafico(config: dict) -> dict:
    bruto = config.get("grafico_config")
    if not isinstance(bruto, dict):
        bruto = {}

    tema = str(bruto.get("tema", "classic")).strip().lower()
    if tema not in ("classic", "bw", "minimal", "light"):
        tema = "classic"

    grid = str(bruto.get("grid", "none")).strip().lower()
    if grid not in ("none", "major_y", "major", "both"):
        grid = "none"

    fundo = str(bruto.get("fundo", "white")).strip().lower()
    if fundo not in ("white", "transparent"):
        fundo = "white"

    fonte_familia = str(bruto.get("fonte_familia", "sans")).strip().lower()
    if fonte_familia not in ("sans", "serif"):
        fonte_familia = "sans"

    try:
        fonte_tamanho = int(bruto.get("fonte_tamanho", 12))
    except (TypeError, ValueError):
        fonte_tamanho = 12
    fonte_tamanho = max(8, min(24, fonte_tamanho))

    cor_texto = str(bruto.get("cor_texto", "#000000")).strip()
    if not cor_texto.startswith("#") or len(cor_texto) not in (4, 7):
        cor_texto = "#000000"

    try:
        angulo_x = int(bruto.get("angulo_x", 0))
    except (TypeError, ValueError):
        angulo_x = 0
    if angulo_x not in (0, 45, 90):
        angulo_x = 0

    barra_erro = str(bruto.get("barra_erro", "se")).strip().lower()
    if barra_erro not in ("se", "sd", "ci", "none"):
        barra_erro = "se"

    legenda = str(bruto.get("legenda", "top")).strip().lower()
    if legenda not in ("top", "bottom", "right", "none"):
        legenda = "top"

    exportacao = str(bruto.get("exportacao", "300_png")).strip().lower()
    if exportacao not in ("300_png", "600_png", "600_tiff", "pdf"):
        exportacao = "300_png"

    return {
        "tema": tema,
        "grid": grid,
        "fundo": fundo,
        "ancorar_zero": bool(bruto.get("ancorar_zero", True)),
        "fonte_familia": fonte_familia,
        "fonte_tamanho": fonte_tamanho,
        "cor_texto": cor_texto,
        "angulo_x": angulo_x,
        "barra_erro": barra_erro,
        "mostrar_letras": bool(bruto.get("mostrar_letras", True)),
        "mostrar_pontos": bool(bruto.get("mostrar_pontos", False)),
        "reg_equacao": bool(bruto.get("reg_equacao", True)),
        "reg_ic": bool(bruto.get("reg_ic", True)),
        "reg_linetype": bool(bruto.get("reg_linetype", True)),
        "multi_rotulos": bool(bruto.get("multi_rotulos", True)),
        "pca_elipse": bool(bruto.get("pca_elipse", True)),
        "legenda": legenda,
        "exportacao": exportacao,
        "rotulo_x": str(bruto.get("rotulo_x", "")).strip(),
        "rotulo_y": str(bruto.get("rotulo_y", "")).strip(),
    }


def montar_rotulos_eixos_r(cfg_graf: dict, expr_x_padrao: str, expr_y_padrao: str) -> tuple[str, str]:
    rx = cfg_graf.get("rotulo_x", "").strip()
    ry = cfg_graf.get("rotulo_y", "").strip()
    expr_x = f'"{escapar_texto_r(rx)}"' if rx else expr_x_padrao
    expr_y = f'"{escapar_texto_r(ry)}"' if ry else expr_y_padrao
    return expr_x, expr_y


#========= 4. MOTOR DE ESTILO CIENTÍFICO GGPLOT2 ==============
def montar_helpers_grafico_r(config: dict) -> list[str]:
    cfg = obter_config_grafico(config)
    tema = cfg["tema"]
    grid = cfg["grid"]
    fundo = cfg["fundo"]
    familia = cfg["fonte_familia"]
    tam = cfg["fonte_tamanho"]
    cor_txt = cfg["cor_texto"]
    angulo_x = cfg["angulo_x"]
    legenda = cfg["legenda"]

    mapa_temas = {
        "classic": f'theme_classic(base_size = {tam}, base_family = "{familia}")',
        "bw": f'theme_bw(base_size = {tam}, base_family = "{familia}")',
        "minimal": f'theme_minimal(base_size = {tam}, base_family = "{familia}")',
        "light": f'theme_light(base_size = {tam}, base_family = "{familia}")',
    }
    chamada_tema = mapa_temas[tema]

    if grid == "none":
        linhas_grid = [
            "    panel.grid.major = element_blank(),",
            "    panel.grid.minor = element_blank(),",
        ]
    elif grid == "major_y":
        linhas_grid = [
            "    panel.grid.major.x = element_blank(),",
            '    panel.grid.major.y = element_line(color = "#D9D9D9", linewidth = 0.35),',
            "    panel.grid.minor = element_blank(),",
        ]
    elif grid == "major":
        linhas_grid = [
            '    panel.grid.major = element_line(color = "#D9D9D9", linewidth = 0.35),',
            "    panel.grid.minor = element_blank(),",
        ]
    else:
        linhas_grid = [
            '    panel.grid.major = element_line(color = "#D0D0D0", linewidth = 0.35),',
            '    panel.grid.minor = element_line(color = "#EAEAEA", linewidth = 0.2),',
        ]

    fill_bg = '"transparent"' if fundo == "transparent" else '"white"'
    borda_painel = f'element_rect(fill = {fill_bg}, color = "{cor_txt}", linewidth = 0.5)' if tema in ("bw", "light") else f"element_rect(fill = {fill_bg}, color = NA)"

    tam_tick = max(8, tam - 1)
    if angulo_x == 45:
        estilo_rotado = f'element_text(angle = 45, hjust = 1, vjust = 1, color = "{cor_txt}", size = {tam_tick})'
    elif angulo_x == 90:
        estilo_rotado = f'element_text(angle = 90, hjust = 1, vjust = 0.5, color = "{cor_txt}", size = {tam_tick})'
    else:
        estilo_rotado = f'element_text(angle = 0, hjust = 0.5, color = "{cor_txt}", size = {tam_tick})'

    estilo_reto = f'element_text(angle = 0, hjust = 0.5, color = "{cor_txt}", size = {tam_tick})'
    linha_ang_x = f"    axis.text.x = if (!mostrar_eixo_x) element_blank() else if (girar_eixo_x) {estilo_rotado} else {estilo_reto},"

    linha_eixo_x = (
        f'    axis.line.x = if (mostrar_eixo_x) element_line(color = "{cor_txt}", linewidth = 0.5) else element_blank(),'
        if tema == "classic"
        else "    axis.line.x = if (mostrar_eixo_x) element_line() else element_blank(),"
    )
    linha_ticks_x = (
        f'    axis.ticks.x = if (mostrar_eixo_x) element_line(color = "{cor_txt}", linewidth = 0.45) else element_blank(),'
    )

    return [
        "aplicar_tema_easyr <- function(grafico, tem_legenda = TRUE, girar_eixo_x = TRUE, mostrar_eixo_x = TRUE) {",
        f'  pos_legenda <- if (tem_legenda) "{legenda}" else "none"',
        "  grafico +",
        f"    {chamada_tema} +",
        "    theme(",
        *linhas_grid,
        f"      plot.background = element_rect(fill = {fill_bg}, color = NA),",
        f"      panel.background = {borda_painel},",
        f"      legend.background = element_rect(fill = {fill_bg}, color = NA),",
        f"      legend.key = element_rect(fill = {fill_bg}, color = NA),",
        f'      text = element_text(color = "{cor_txt}", family = "{familia}"),',
        f'      plot.title = element_text(face = "bold", hjust = 0.5, color = "{cor_txt}", size = {tam + 2}),',
        f'      plot.subtitle = element_text(hjust = 0.5, color = "{cor_txt}", size = {max(8, tam - 2)}),',
        f'      axis.title = element_text(face = "bold", color = "{cor_txt}", size = {tam}),',
        f'      axis.text.y = element_text(color = "{cor_txt}", size = {tam_tick}),',
        linha_ang_x,
        linha_eixo_x,
        linha_ticks_x,
        f'      axis.ticks.y = element_line(color = "{cor_txt}", linewidth = 0.45),',
        f'      legend.title = element_text(face = "bold", color = "{cor_txt}", size = {tam_tick}),',
        f'      legend.text = element_text(color = "{cor_txt}", size = {max(8, tam - 2)}),',
        "      legend.position = pos_legenda",
        "    )",
        "}",
    ]


#========= 5. EXPORTAÇÃO AUTOMÁTICA DE GRÁFICOS (GGSAVE) ==============
def montar_bloco_salvar_grafico(config: dict, prefixo: str) -> list[str]:
    cfg = obter_config_grafico(config)
    exportacao = cfg["exportacao"]
    fundo = cfg["fundo"]
    bg_save = "transparent" if fundo == "transparent" else "white"

    mapa_export = {
        "300_png": ("png", 300, ""),
        "600_png": ("png", 600, ""),
        "600_tiff": ("tiff", 600, ', compression = "lzw"'),
        "pdf": ("pdf", 300, ""),
    }
    ext, dpi, extra_args = mapa_export.get(exportacao, ("png", 300, ""))

    pasta = str(config.get("pasta_graficos", "")).strip()
    if pasta:
        pasta_r = pasta.replace("\\", "/")
        linha_dir = f'pasta_saida_graficos <- "{pasta_r}"'
    else:
        caminho_arq = str(config.get("caminho_arquivo", "")).replace("\\", "/").strip()
        if caminho_arq:
            linha_dir = f'pasta_saida_graficos <- file.path(dirname("{caminho_arq}"), "Graficos_EasyR")'
        else:
            linha_dir = 'pasta_saida_graficos <- file.path(getwd(), "Graficos_EasyR")'

    return [
        linha_dir,
        'dir.create(pasta_saida_graficos, recursive = TRUE, showWarnings = FALSE)',
        "salvar_grafico_easyr <- function(grafico, sufixo) {",
        '  nome_limpo <- gsub("[^A-Za-z0-9_-]+", "_", sufixo)',
        f'  arq <- file.path(pasta_saida_graficos, paste0("{prefixo}_", nome_limpo, ".{ext}"))',
        "  tryCatch({",
        f'    ggsave(filename = arq, plot = grafico, width = 8.5, height = 5.5, units = "in", dpi = {dpi}, bg = "{bg_save}"{extra_args})',
        '    cat("Grafico salvo em:", arq, "\\n")',
        "  }, error = function(e) {",
        '    warning(paste0("Nao foi possivel salvar o grafico \'", arq, "\' (feche o arquivo se estiver aberto): ", conditionMessage(e)))',
        "  })",
        "}",
    ]