#========= 1. IMPORTAÇÕES ==============
from RSTS.base import (
    montar_bloco_salvar_grafico,
    montar_cabecalho_pacotes,
    montar_helpers_grafico_r,
    montar_leitura_dados,
    montar_paleta_r,
    montar_rotulos_eixos_r,
    obter_config_grafico,
)


#========= 2. LEITURA E VALIDAÇÃO DOS PARÂMETROS ==============
def gerar_script_scott_knott(config: dict) -> str:
    caminho = config.get("caminho_arquivo", "")
    aba = config.get("aba", "")
    fatores = config.get("fatores", {})
    tratamento = fatores.get("tratamento", "")
    bloco = fatores.get("bloco", "")
    respostas = config.get("respostas", [])
    alfa = config.get("alfa", 0.05)
    cores = config.get("cores_graficos", [])
    cfg_graf = obter_config_grafico(config)

    if not tratamento:
        raise ValueError("Coluna de tratamento não informada para o Scott-Knott.")
    if not respostas:
        raise ValueError("Nenhuma variável resposta selecionada.")

    pacotes = ["ScottKnott", "ggplot2"]
    if aba:
        pacotes.append("readxl")

    vetor_vars = ", ".join(f'"{v}"' for v in respostas)
    paleta_r = montar_paleta_r(cores)
    cor_txt = cfg_graf["cor_texto"]
    barra_erro = cfg_graf["barra_erro"]
    expr_x, expr_y = montar_rotulos_eixos_r(cfg_graf, "col_trat", "v")

    if barra_erro == "sd":
        expr_erro_agg = "if (length(x) > 1) sd(x) else 0"
    elif barra_erro == "ci":
        expr_erro_agg = "if (length(x) > 1) qt(0.975, df = length(x) - 1) * (sd(x) / sqrt(length(x))) else 0"
    elif barra_erro == "none":
        expr_erro_agg = "0"
    else:
        expr_erro_agg = "if (length(x) > 1) sd(x) / sqrt(length(x)) else 0"

    camada_erro = (
        [f'    geom_errorbar(aes(ymin = Media - Erro_Plot, ymax = Media + Erro_Plot), width = 0.18, linewidth = 0.5, color = "{cor_txt}") +']
        if barra_erro != "none"
        else []
    )
    camada_letras = (
        [f'    geom_text(aes(y = Media + erro_vis + offset_letra, label = Grupo), fontface = "bold", size = 4, color = "{cor_txt}") +']
        if cfg_graf["mostrar_letras"]
        else []
    )
    camada_pontos = (
        [f'    geom_jitter(data = subdados, aes(x = Tratamento, y = Valor_Y), width = 0.14, size = 2.0, alpha = 0.72, color = "{cor_txt}", inherit.aes = FALSE) +']
        if cfg_graf["mostrar_pontos"]
        else []
    )

    if cfg_graf["ancorar_zero"]:
        bloco_escala_y = [
            "  limite_inf <- min(0, min(vals_min, na.rm = TRUE) * 1.15)",
            "  limite_sup <- max(0.0001, max(vals_max, na.rm = TRUE) * 1.22)",
            "  offset_letra <- (limite_sup - limite_inf) * 0.04",
            "  escala_y <- scale_y_continuous(limits = c(limite_inf, limite_sup), expand = c(0, 0))",
        ]
    else:
        bloco_escala_y = [
            "  amplitude_y <- max(0.0001, max(vals_max, na.rm = TRUE) - min(vals_min, na.rm = TRUE))",
            "  offset_letra <- amplitude_y * 0.06",
            "  escala_y <- scale_y_continuous(expand = expansion(mult = c(0.08, 0.18)))",
        ]

    #========= 3. PREPARAÇÃO DE BLOCO E FÓRMULA ==============
    if bloco:
        bloco_prep = [
            f'col_bloco <- resolver_coluna_easyr(dados, "{bloco}")',
            "dados$Bloco <- as.factor(trimws(as.character(dados[[col_bloco]])))",
        ]
        filtro_extra = " & !is.na(dados$Bloco)"
        bloco_sub = "Bloco = droplevels(dados$Bloco[validos]),"
        formula_r = "Valor_Y ~ Tratamento + Bloco"
    else:
        bloco_prep = []
        filtro_extra = ""
        bloco_sub = ""
        formula_r = "Valor_Y ~ Tratamento"

    #========= 4. CABEÇALHO R E INICIALIZAÇÃO ==============
    linhas = [
        *montar_cabecalho_pacotes(pacotes),
        "",
        *montar_leitura_dados(caminho, aba),
        f'col_trat <- resolver_coluna_easyr(dados, "{tratamento}")',
        "dados$Tratamento <- as.factor(trimws(as.character(dados[[col_trat]])))",
        *bloco_prep,
        "",
        *montar_helpers_grafico_r(config),
        "",
        *montar_bloco_salvar_grafico(config, "ScottKnott"),
        "",
        f"variaveis <- c({vetor_vars})",
        f"alfa <- {alfa}",
        f"paleta_base <- {paleta_r}",
        "resultados_anova_sk <- list()",
        "resultados_scott_knott <- list()",
        "graficos_scott_knott <- list()",
        "",

        #========= 5. LOOP POR VARIÁVEL: ANOVA E AGRUPAMENTO SCOTT-KNOTT ==============
        "for (v in variaveis) {",
        "  col_y <- resolver_coluna_easyr(dados, v)",
        '  y_num <- suppressWarnings(as.numeric(gsub(",", ".", as.character(dados[[col_y]]))))',
        f"  validos <- !is.na(y_num) & !is.na(dados$Tratamento){filtro_extra}",
        "  subdados <- data.frame(",
        "    Tratamento = droplevels(dados$Tratamento[validos]),",
        f"    {bloco_sub}",
        "    Valor_Y = y_num[validos]",
        "  )",
        "",
        f"  modelo <- aov({formula_r}, data = subdados)",
        '  if (df.residual(modelo) == 0) stop("Sem repeticoes suficientes para estimar o residuo.")',
        "",
        "  tab_anova <- as.data.frame(anova(modelo))",
        '  qm_res <- tab_anova[nrow(tab_anova), "Mean Sq"]',
        "  if (is.na(qm_res) || qm_res <= 1e-12) {",
        '    warning(paste("Variavel sem variancia residual (dados constantes):", v))',
        "    next",
        "  }",
        "  resultados_anova_sk[[v]] <- tab_anova",
        "  cv_pct <- round((sqrt(qm_res) / mean(subdados$Valor_Y, na.rm = TRUE)) * 100, 2)",
        "",
        '  sk <- SK(modelo, which = "Tratamento", sig.level = alfa)',
        "  grupos_num <- sk$groups",
        "  trats_ord <- names(grupos_num)",
        "  letras_sk <- letters[grupos_num]",
        "",
        f"  resumo <- aggregate(subdados$Valor_Y, by = list(Tratamento = subdados$Tratamento), FUN = function(x) c(media = mean(x), ep = sd(x) / sqrt(length(x)), erro = {expr_erro_agg}))",
        "  rownames(resumo) <- as.character(resumo$Tratamento)",
        "  mat_resumo <- resumo[trats_ord, 'x', drop = FALSE]",
        "",
        "  tabela <- data.frame(",
        "    Variavel = v,",
        "    Tratamento = factor(trats_ord, levels = levels(subdados$Tratamento)),",
        '    Media = round(mat_resumo[, "media"], 4),',
        '    EP = round(mat_resumo[, "ep"], 4),',
        '    Erro_Plot = mat_resumo[, "erro"],',
        "    Grupo = letras_sk,",
        "    CV_pct = cv_pct,",
        "    row.names = NULL",
        "  )",
        "  tabela <- tabela[order(tabela$Tratamento), ]",
        '  resultados_scott_knott[[v]] <- tabela[, c("Variavel", "Tratamento", "Media", "EP", "Grupo", "CV_pct")]',
        "",
        '  cat("\\n==============================================\\n")',
        '  cat("SCOTT-KNOTT - Variavel:", v, "| alfa =", alfa, "\\n")',
        '  cat("==============================================\\n")',
        "  print(tab_anova)",
        '  cat("\\nAgrupamento de Medias (Scott-Knott):\\n")',
        "  print(resultados_scott_knott[[v]], row.names = FALSE)",
        "",

        #========= 6. GRÁFICO DE COLUNAS E CONSOLIDAÇÃO FINAL ==============
        "  cores_trat <- colorRampPalette(paleta_base)(nlevels(tabela$Tratamento))",
        "  erro_vis <- ifelse(is.na(tabela$Erro_Plot), 0, tabela$Erro_Plot)",
        "  vals_min <- c(tabela$Media - erro_vis, subdados$Valor_Y)",
        "  vals_max <- c(tabela$Media + erro_vis, subdados$Valor_Y)",
        *bloco_escala_y,
        "",
        "  p <- ggplot(tabela, aes(x = Tratamento, y = Media, fill = Tratamento)) +",
        f'    geom_col(width = 0.62, color = "{cor_txt}", linewidth = 0.4) +',
        *camada_erro,
        *camada_pontos,
        *camada_letras,
        "    scale_fill_manual(values = cores_trat) +",
        "    escala_y +",
        f'    labs(title = paste("Scott-Knott -", v), x = {expr_x}, y = {expr_y})',
        "  p <- aplicar_tema_easyr(p, tem_legenda = FALSE, girar_eixo_x = TRUE)",
        "",
        "  graficos_scott_knott[[v]] <- p",
        "  print(p)",
        "  salvar_grafico_easyr(p, v)",
        "}",
        "",
        "tabela_final_scott_knott <- do.call(rbind, resultados_scott_knott)",
        "rownames(tabela_final_scott_knott) <- NULL",
    ]
    return "\n".join(linhas) + "\n"