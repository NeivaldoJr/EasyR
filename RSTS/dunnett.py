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
def gerar_script_dunnett(config: dict) -> str:
    caminho = config.get("caminho_arquivo", "")
    aba = config.get("aba", "")
    fatores = config.get("fatores", {})
    tratamento = fatores.get("tratamento", "")
    controle = str(fatores.get("controle", "")).strip()
    bloco = fatores.get("bloco", "")
    respostas = config.get("respostas", [])
    alfa = config.get("alfa", 0.05)
    cores = config.get("cores_graficos", [])
    cfg_graf = obter_config_grafico(config)

    if not tratamento:
        raise ValueError("Coluna de tratamento não informada para o Dunnett.")
    if not respostas:
        raise ValueError("Nenhuma variável resposta selecionada.")

    pacotes = ["multcomp", "ggplot2"]
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
        [f'    geom_text(aes(y = Media + erro_vis + offset_lbl, label = Status_vs_Controle), fontface = "bold", size = 3.8, color = "{cor_txt}") +']
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
            "  offset_lbl <- (limite_sup - limite_inf) * 0.04",
            "  escala_y <- scale_y_continuous(limits = c(limite_inf, limite_sup), expand = c(0, 0))",
        ]
    else:
        bloco_escala_y = [
            "  amplitude_y <- max(0.0001, max(vals_max, na.rm = TRUE) - min(vals_min, na.rm = TRUE))",
            "  offset_lbl <- amplitude_y * 0.06",
            "  escala_y <- scale_y_continuous(expand = expansion(mult = c(0.08, 0.18)))",
        ]

    #========= 3. PREPARAÇÃO DE BLOCO E TRATAMENTO CONTROLE ==============
    if bloco:
        bloco_prep = [
            f'col_bloco <- resolver_coluna_easyr(dados, "{bloco}")',
            "dados$Bloco <- as.factor(trimws(as.character(dados[[col_bloco]])))",
        ]
        filtro_extra = " & !is.na(dados$Bloco)"
        bloco_sub = "Bloco = droplevels(dados$Bloco[validos]),"
        formula_r = "Valor_Y ~ Trat_Dunnett + Bloco"
    else:
        bloco_prep = []
        filtro_extra = ""
        bloco_sub = ""
        formula_r = "Valor_Y ~ Trat_Dunnett"

    if controle:
        bloco_controle = [
            f'tratamento_controle <- "{controle}"',
            "if (!(tratamento_controle %in% levels(dados$Tratamento))) {",
            '  stop(paste("Controle nao encontrado nos tratamentos:", tratamento_controle))',
            "}",
        ]
    else:
        bloco_controle = [
            "tratamento_controle <- levels(dados$Tratamento)[1]",
        ]

    #========= 4. CABEÇALHO R E INICIALIZAÇÃO ==============
    linhas = [
        *montar_cabecalho_pacotes(pacotes),
        "",
        *montar_leitura_dados(caminho, aba),
        f'col_trat <- resolver_coluna_easyr(dados, "{tratamento}")',
        "dados$Tratamento <- as.factor(trimws(as.character(dados[[col_trat]])))",
        *bloco_prep,
        *bloco_controle,
        "",
        *montar_helpers_grafico_r(config),
        "",
        *montar_bloco_salvar_grafico(config, "Dunnett"),
        "",
        f"variaveis <- c({vetor_vars})",
        f"alfa <- {alfa}",
        f"paleta_base <- {paleta_r}",
        "resultados_anova_dunnett <- list()",
        "resultados_dunnett <- list()",
        "medias_dunnett <- list()",
        "graficos_dunnett <- list()",
        "",

        #========= 5. LOOP POR VARIÁVEL: ANOVA E CONTRASTES DE DUNNETT ==============
        "for (v in variaveis) {",
        "  col_y <- resolver_coluna_easyr(dados, v)",
        '  y_num <- suppressWarnings(as.numeric(gsub(",", ".", as.character(dados[[col_y]]))))',
        f"  validos <- !is.na(y_num) & !is.na(dados$Tratamento){filtro_extra}",
        "  subdados <- data.frame(",
        "    Tratamento = droplevels(dados$Tratamento[validos]),",
        f"    {bloco_sub}",
        "    Valor_Y = y_num[validos]",
        "  )",
        "  subdados$Trat_Dunnett <- relevel(subdados$Tratamento, ref = tratamento_controle)",
        f"  modelo <- aov({formula_r}, data = subdados)",
        '  if (df.residual(modelo) == 0) stop("Sem repeticoes suficientes para estimar o residuo.")',
        "",
        "  tab_anova <- as.data.frame(anova(modelo))",
        "  resultados_anova_dunnett[[v]] <- tab_anova",
        "",
        '  dun <- glht(modelo, linfct = mcp(Trat_Dunnett = "Dunnett"))',
        '  res_dun <- summary(dun, test = adjusted("single-step"))',
        "  ci_dun <- confint(dun, level = 1 - alfa)$confint",
        "  p_vals <- as.numeric(res_dun$test$pvalues)",
        '  sig_vec <- ifelse(p_vals <= 0.001, "***", ifelse(p_vals <= 0.01, "**", ifelse(p_vals <= alfa, "*", "ns")))',
        "",
        "  tab_contrastes <- data.frame(",
        "    Variavel = v,",
        "    Contraste = names(res_dun$test$coefficients),",
        "    Diferenca = round(as.numeric(res_dun$test$coefficients), 4),",
        '    IC_Inf = round(ci_dun[, "lwr"], 4),',
        '    IC_Sup = round(ci_dun[, "upr"], 4),',
        "    t_calc = round(as.numeric(res_dun$test$tstat), 4),",
        "    p_valor = round(p_vals, 6),",
        "    Significancia = sig_vec,",
        "    row.names = NULL",
        "  )",
        "  resultados_dunnett[[v]] <- tab_contrastes",
        "",
        f"  resumo <- aggregate(subdados$Valor_Y, by = list(Tratamento = subdados$Trat_Dunnett), FUN = function(x) c(media = mean(x), ep = sd(x) / sqrt(length(x)), erro = {expr_erro_agg}))",
        "  niveis_ord <- as.character(resumo$Tratamento)",
        '  rotulos_sig <- c("Controle", sig_vec)',
        "  tabela_m <- data.frame(",
        "    Variavel = v,",
        "    Tratamento = factor(niveis_ord, levels = niveis_ord),",
        '    Media = round(resumo$x[, "media"], 4),',
        '    EP = round(resumo$x[, "ep"], 4),',
        '    Erro_Plot = resumo$x[, "erro"],',
        "    Status_vs_Controle = rotulos_sig,",
        "    row.names = NULL",
        "  )",
        '  medias_dunnett[[v]] <- tabela_m[, c("Variavel", "Tratamento", "Media", "EP", "Status_vs_Controle")]',
        "",
        '  cat("\\n==============================================\\n")',
        '  cat("DUNNETT - Variavel:", v, "| Controle:", tratamento_controle, "| alfa =", alfa, "\\n")',
        '  cat("==============================================\\n")',
        "  print(tab_anova)",
        '  cat("\\nContrastes vs Controle (Dunnett):\\n")',
        "  print(tab_contrastes, row.names = FALSE)",
        '  cat("\\nMedias e Significancia vs Controle:\\n")',
        "  print(medias_dunnett[[v]], row.names = FALSE)",
        "",

        #========= 6. GRÁFICO DE COMPARAÇÃO PERSONALIZADO (GGPLOT2) ==============
        '  cor_ctrl <- ifelse(length(paleta_base) >= 2, paleta_base[2], "#503C2C")',
        "  cor_trat <- paleta_base[1]",
        '  tabela_m$Tipo <- ifelse(as.character(tabela_m$Tratamento) == tratamento_controle, "Controle", "Tratamento")',
        "  erro_vis <- ifelse(is.na(tabela_m$Erro_Plot), 0, tabela_m$Erro_Plot)",
        "  vals_min <- c(tabela_m$Media - erro_vis, subdados$Valor_Y)",
        "  vals_max <- c(tabela_m$Media + erro_vis, subdados$Valor_Y)",
        *bloco_escala_y,
        "",
        "  p <- ggplot(tabela_m, aes(x = Tratamento, y = Media, fill = Tipo)) +",
        f'    geom_col(width = 0.62, color = "{cor_txt}", linewidth = 0.4) +',
        *camada_erro,
        *camada_pontos,
        *camada_letras,
        '    scale_fill_manual(values = c("Controle" = cor_ctrl, "Tratamento" = cor_trat)) +',
        "    escala_y +",
        f'    labs(title = paste("Dunnett -", v), subtitle = paste("Referencia (Controle):", tratamento_controle), x = {expr_x}, y = {expr_y})',
        "  p <- aplicar_tema_easyr(p, tem_legenda = FALSE, girar_eixo_x = TRUE)",
        "",
        "  graficos_dunnett[[v]] <- p",
        "  print(p)",
        "  salvar_grafico_easyr(p, v)",
        "}",
        "",

        #========= 7. CONSOLIDAÇÃO DA TABELA FINAL ==============
        "tabela_final_dunnett <- do.call(rbind, resultados_dunnett)",
        "rownames(tabela_final_dunnett) <- NULL",
    ]
    return "\n".join(linhas) + "\n"