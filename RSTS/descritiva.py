#========= 1. IMPORTAÇÕES ==============
from RSTS.base import montar_cabecalho_pacotes, montar_leitura_dados


#========= 2. LEITURA E VALIDAÇÃO DOS PARÂMETROS ==============
def gerar_script_descritiva(config: dict) -> str:
    caminho = config.get("caminho_arquivo", "")
    aba = config.get("aba", "")
    fatores = config.get("fatores", {})
    grupo = fatores.get("grupo", "")
    respostas = config.get("respostas", [])

    if not respostas:
        raise ValueError("Nenhuma variável resposta selecionada.")

    pacotes = ["readxl"] if aba else []
    vetor_vars = ", ".join(f'"{v}"' for v in respostas)

    cabecalho_pac = montar_cabecalho_pacotes(pacotes) if pacotes else []

    #========= 3. CABEÇALHO R E FUNÇÃO DE ESTATÍSTICAS (calc_stats) ==============
    linhas = [
        *cabecalho_pac,
        *([""] if cabecalho_pac else []),
        *montar_leitura_dados(caminho, aba),
        "",
        f"variaveis <- c({vetor_vars})",
        "resultados_descritiva <- list()",
        "",
        "calc_stats <- function(x) {",
        "  x <- x[!is.na(x)]",
        "  n <- length(x)",
        "  if (n == 0) {",
        "    return(c(n = 0, Media = NA, DP = NA, EP = NA, Mediana = NA, Min = NA, Max = NA, Amplitude = NA, CV_pct = NA))",
        "  }",
        "  m <- mean(x)",
        "  s <- if (n > 1) sd(x) else NA_real_",
        "  ep <- if (n > 1) s / sqrt(n) else NA_real_",
        "  cv <- if (!is.na(s) && m != 0) (s / abs(m)) * 100 else NA_real_",
        "  mn <- min(x)",
        "  mx <- max(x)",
        "  c(",
        "    n = n,",
        "    Media = round(m, 4),",
        "    DP = round(s, 4),",
        "    EP = round(ep, 4),",
        "    Mediana = round(median(x), 4),",
        "    Min = round(mn, 4),",
        "    Max = round(mx, 4),",
        "    Amplitude = round(mx - mn, 4),",
        "    CV_pct = round(cv, 2)",
        "  )",
        "}",
        "",
    ]

    #========= 4. CÁLCULO AGRUPADO OU GERAL ==============
    if grupo:
        linhas.extend([
            f'col_grupo_alvo <- resolver_coluna_easyr(dados, "{grupo}")',
            "",
            "for (v in variaveis) {",
            "  col_y <- resolver_coluna_easyr(dados, v)",
            '  y_num <- suppressWarnings(as.numeric(gsub(",", ".", as.character(dados[[col_y]]))))',
            "  g_chr <- trimws(as.character(dados[[col_grupo_alvo]]))",
            '  validos <- !is.na(y_num) & !is.na(g_chr) & g_chr != "" & tolower(g_chr) != "na"',
            "",
            "  subdados <- data.frame(",
            "    Grupo_Plot = factor(g_chr[validos], levels = unique(g_chr[validos])),",
            "    Valor_Y = y_num[validos],",
            "    stringsAsFactors = FALSE",
            "  )",
            "",
            "  if (nrow(subdados) == 0) {",
            '    warning(paste("Sem dados numericos validos para:", v))',
            "    next",
            "  }",
            "",
            "  agg <- aggregate(subdados$Valor_Y, by = list(Grupo = subdados$Grupo_Plot), FUN = calc_stats)",
            "  tab_desc <- cbind(Variavel = v, Grupo = agg$Grupo, as.data.frame(agg$x))",
            "  names(tab_desc)[2] <- col_grupo_alvo",
            "  resultados_descritiva[[v]] <- tab_desc",
            "",
            '  cat("\\n==============================================\\n")',
            '  cat("ESTATISTICA DESCRITIVA - Variavel:", v, "| Agrupado por:", col_grupo_alvo, "\\n")',
            '  cat("==============================================\\n")',
            "  print(tab_desc, row.names = FALSE)",
            "}",
            "",
            "if (length(resultados_descritiva) > 0) {",
            "  tabela_final_descritiva <- do.call(rbind, resultados_descritiva)",
            "  rownames(tabela_final_descritiva) <- NULL",
            "}",
        ])
    else:
        linhas.extend([
            "for (v in variaveis) {",
            "  col_y <- resolver_coluna_easyr(dados, v)",
            '  y_num <- suppressWarnings(as.numeric(gsub(",", ".", as.character(dados[[col_y]]))))',
            "  y_valid <- y_num[!is.na(y_num)]",
            "  if (length(y_valid) == 0) next",
            "",
            "  st <- calc_stats(y_valid)",
            "  resultados_descritiva[[v]] <- data.frame(Variavel = v, t(st), row.names = NULL)",
            "}",
            "",
            "if (length(resultados_descritiva) > 0) {",
            "  tabela_final_descritiva <- do.call(rbind, resultados_descritiva)",
            "  rownames(tabela_final_descritiva) <- NULL",
            '  cat("\\n==============================================\\n")',
            '  cat("ESTATISTICA DESCRITIVA GERAL\\n")',
            '  cat("==============================================\\n")',
            "  print(tabela_final_descritiva, row.names = FALSE)",
            "}",
        ])

    return "\n".join(linhas) + "\n"