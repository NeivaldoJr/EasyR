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
def gerar_script_subdividida(config: dict) -> str:
    caminho = config.get("caminho_arquivo", "")
    aba = config.get("aba", "")
    fatores = config.get("fatores", {})
    parcela = fatores.get("parcela", "")
    subparcela = fatores.get("subparcela", "")
    bloco = fatores.get("bloco", "")
    respostas = config.get("respostas", [])
    alfa = config.get("alfa", 0.05)
    cores = config.get("cores_graficos", [])
    cfg_graf = obter_config_grafico(config)

    if not parcela:
        raise ValueError("Coluna de parcela (tratamento principal) não informada.")
    if not subparcela:
        raise ValueError("Coluna de subparcela (tempo/época/fator B) não informada.")
    if not bloco:
        raise ValueError("Coluna de bloco/repetição não informada.")
    if len({parcela, subparcela, bloco}) < 3:
        raise ValueError("Parcela, subparcela e bloco devem ser colunas distintas.")
    if not respostas:
        raise ValueError("Nenhuma variável resposta selecionada.")

    pacotes = ["agricolae", "ggplot2"]
    if aba:
        pacotes.append("readxl")

    vetor_vars = ", ".join(f'"{v}"' for v in respostas)
    paleta_r = montar_paleta_r(cores)
    barra_erro = cfg_graf["barra_erro"]
    expr_x, expr_y = montar_rotulos_eixos_r(cfg_graf, "col_sub", "v")

    if barra_erro == "sd":
        expr_erro_agg = "if (length(x) > 1) sd(x) else 0"
    elif barra_erro == "ci":
        expr_erro_agg = "if (length(x) > 1) qt(0.975, df = length(x) - 1) * (sd(x) / sqrt(length(x))) else 0"
    elif barra_erro == "none":
        expr_erro_agg = "0"
    else:
        expr_erro_agg = "if (length(x) > 1) sd(x) / sqrt(length(x)) else 0"

    camada_erro = (
        ["    geom_errorbar(aes(ymin = Media - Erro_Plot, ymax = Media + Erro_Plot), width = 0.14, linewidth = 0.5) +"]
        if barra_erro != "none"
        else []
    )
    camada_pontos = (
        ["    geom_jitter(data = subdados, aes(x = Subparcela, y = Valor_Y, color = Parcela), width = 0.12, size = 1.9, alpha = 0.55, inherit.aes = FALSE) +"]
        if cfg_graf["mostrar_pontos"]
        else []
    )
    camada_zero = ["    expand_limits(y = 0) +"] if cfg_graf["ancorar_zero"] else []

    #========= 3. CABEÇALHO R E PREPARAÇÃO DOS FATORES ==============
    linhas = [
        *montar_cabecalho_pacotes(pacotes),
        "",
        *montar_leitura_dados(caminho, aba),
        f'col_parc <- resolver_coluna_easyr(dados, "{parcela}")',
        f'col_sub <- resolver_coluna_easyr(dados, "{subparcela}")',
        f'col_bloco <- resolver_coluna_easyr(dados, "{bloco}")',
        "",
        "dados$Parcela <- as.factor(trimws(as.character(dados[[col_parc]])))",
        "dados$Bloco <- as.factor(trimws(as.character(dados[[col_bloco]])))",
        "sub_txt <- trimws(as.character(dados[[col_sub]]))",
        'sub_num <- suppressWarnings(as.numeric(gsub(",", ".", sub_txt)))',
        "if (!any(is.na(sub_num[!is.na(sub_txt) & sub_txt != '']))) {",
        "  niveis_sub <- as.character(sort(unique(sub_num[!is.na(sub_num)])))",
        "  sub_txt <- ifelse(is.na(sub_num), NA_character_, as.character(sub_num))",
        "} else {",
        "  niveis_sub <- unique(sub_txt[!is.na(sub_txt) & sub_txt != ''])",
        "}",
        "dados$Subparcela <- factor(sub_txt, levels = niveis_sub)",
        "",
        *montar_helpers_grafico_r(config),
        "",
        *montar_bloco_salvar_grafico(config, "Subdividida"),
        "",
        f"variaveis <- c({vetor_vars})",
        f"alfa <- {alfa}",
        f"paleta_base <- {paleta_r}",
        "resultados_anova_sub <- list()",
        "resultados_parcela <- list()",
        "resultados_tempo <- list()",
        "resultados_interacao <- list()",
        "graficos_subdividida <- list()",
        "",

        #========= 4. LOOP POR VARIÁVEL: QUADRO DA ANOVA EM PARCELA SUBDIVIDIDA ==============
        "for (v in variaveis) {",
        "  col_y <- resolver_coluna_easyr(dados, v)",
        '  y_num <- suppressWarnings(as.numeric(gsub(",", ".", as.character(dados[[col_y]]))))',
        "  validos <- !is.na(y_num) & !is.na(dados$Parcela) & !is.na(dados$Subparcela) & !is.na(dados$Bloco)",
        "  subdados <- data.frame(",
        "    Parcela = droplevels(dados$Parcela[validos]),",
        "    Subparcela = droplevels(dados$Subparcela[validos]),",
        "    Bloco = droplevels(dados$Bloco[validos]),",
        "    Valor_Y = y_num[validos]",
        "  )",
        "",
        "  modelo <- aov(Valor_Y ~ Bloco + Parcela + Bloco:Parcela + Subparcela + Parcela:Subparcela, data = subdados)",
        "  tab_bruta <- as.data.frame(anova(modelo))",
        "",
        '  gl_bloco <- tab_bruta["Bloco", "Df"]',
        '  sq_bloco <- tab_bruta["Bloco", "Sum Sq"]',
        '  qm_bloco <- tab_bruta["Bloco", "Mean Sq"]',
        '  gl_parc <- tab_bruta["Parcela", "Df"]',
        '  sq_parc <- tab_bruta["Parcela", "Sum Sq"]',
        '  qm_parc <- tab_bruta["Parcela", "Mean Sq"]',
        '  gl_res_a <- tab_bruta["Bloco:Parcela", "Df"]',
        '  sq_res_a <- tab_bruta["Bloco:Parcela", "Sum Sq"]',
        '  qm_res_a <- tab_bruta["Bloco:Parcela", "Mean Sq"]',
        '  gl_sub <- tab_bruta["Subparcela", "Df"]',
        '  sq_sub <- tab_bruta["Subparcela", "Sum Sq"]',
        '  qm_sub <- tab_bruta["Subparcela", "Mean Sq"]',
        '  gl_int <- tab_bruta["Parcela:Subparcela", "Df"]',
        '  sq_int <- tab_bruta["Parcela:Subparcela", "Sum Sq"]',
        '  qm_int <- tab_bruta["Parcela:Subparcela", "Mean Sq"]',
        '  gl_res_b <- tab_bruta["Residuals", "Df"]',
        '  sq_res_b <- tab_bruta["Residuals", "Sum Sq"]',
        '  qm_res_b <- tab_bruta["Residuals", "Mean Sq"]',
        "",
        "  if (is.na(gl_res_a) || gl_res_a == 0 || is.na(gl_res_b) || gl_res_b == 0) {",
        '    stop("Graus de liberdade insuficientes nos residuos da parcela subdividida.")',
        "  }",
        "",
        "  f_bloco <- qm_bloco / qm_res_a",
        "  p_bloco <- pf(f_bloco, gl_bloco, gl_res_a, lower.tail = FALSE)",
        "  f_parc <- qm_parc / qm_res_a",
        "  p_parc <- pf(f_parc, gl_parc, gl_res_a, lower.tail = FALSE)",
        "  f_sub <- qm_sub / qm_res_b",
        "  p_sub <- pf(f_sub, gl_sub, gl_res_b, lower.tail = FALSE)",
        "  f_int <- qm_int / qm_res_b",
        "  p_int <- pf(f_int, gl_int, gl_res_b, lower.tail = FALSE)",
        "",
        "  quadro_anova <- data.frame(",
        '    Fonte = c(col_bloco, col_parc, "Residuo (a)", col_sub, paste0(col_parc, ":", col_sub), "Residuo (b)"),',
        "    GL = c(gl_bloco, gl_parc, gl_res_a, gl_sub, gl_int, gl_res_b),",
        "    SQ = round(c(sq_bloco, sq_parc, sq_res_a, sq_sub, sq_int, sq_res_b), 4),",
        "    QM = round(c(qm_bloco, qm_parc, qm_res_a, qm_sub, qm_int, qm_res_b), 4),",
        "    F_calc = round(c(f_bloco, f_parc, NA, f_sub, f_int, NA), 4),",
        "    p_valor = round(c(p_bloco, p_parc, NA, p_sub, p_int, NA), 6),",
        "    row.names = NULL",
        "  )",
        "  resultados_anova_sub[[v]] <- quadro_anova",
        "",
        "  media_geral <- mean(subdados$Valor_Y, na.rm = TRUE)",
        "  cv_a <- round((sqrt(qm_res_a) / media_geral) * 100, 2)",
        "  cv_b <- round((sqrt(qm_res_b) / media_geral) * 100, 2)",
        "",

        #========= 5. TESTES DE MÉDIAS (EFEITOS PRINCIPAIS E DESDOBRAMENTO) ==============
        "  tukey_p <- HSD.test(subdados$Valor_Y, subdados$Parcela, gl_res_a, qm_res_a, alpha = alfa, group = TRUE, console = FALSE)",
        "  gp_p <- tukey_p$groups",
        "  mi_p <- tukey_p$means",
        "  niveis_p <- rownames(gp_p)",
        '  ep_p <- mi_p[niveis_p, "std"] / sqrt(mi_p[niveis_p, "r"])',
        "  tab_p <- data.frame(",
        "    Variavel = v,",
        "    Parcela = factor(niveis_p, levels = levels(subdados$Parcela)),",
        "    Media = round(gp_p[[1]], 4),",
        "    EP = round(ep_p, 4),",
        '    Grupo = gp_p[["groups"]],',
        "    CV_a_pct = cv_a,",
        "    row.names = NULL",
        "  )",
        "  tab_p <- tab_p[order(tab_p$Parcela), ]",
        "  resultados_parcela[[v]] <- tab_p",
        "",
        "  tukey_t <- HSD.test(subdados$Valor_Y, subdados$Subparcela, gl_res_b, qm_res_b, alpha = alfa, group = TRUE, console = FALSE)",
        "  gp_t <- tukey_t$groups",
        "  mi_t <- tukey_t$means",
        "  niveis_t <- rownames(gp_t)",
        '  ep_t <- mi_t[niveis_t, "std"] / sqrt(mi_t[niveis_t, "r"])',
        "  tab_t <- data.frame(",
        "    Variavel = v,",
        "    Subparcela = factor(niveis_t, levels = levels(subdados$Subparcela)),",
        "    Media = round(gp_t[[1]], 4),",
        "    EP = round(ep_t, 4),",
        '    Grupo = gp_t[["groups"]],',
        "    CV_b_pct = cv_b,",
        "    row.names = NULL",
        "  )",
        "  tab_t <- tab_t[order(tab_t$Subparcela), ]",
        "  resultados_tempo[[v]] <- tab_t",
        "",
        '  cat("\\n==============================================\\n")',
        '  cat("PARCELA SUBDIVIDIDA - Variavel:", v, "| alfa =", alfa, "\\n")',
        '  cat("CV (a) =", cv_a, "% | CV (b) =", cv_b, "%\\n")',
        '  cat("==============================================\\n")',
        "  print(quadro_anova, row.names = FALSE)",
        '  cat("\\nMedias Principais - Parcela (", col_parc, "):\\n")',
        "  print(tab_p, row.names = FALSE)",
        '  cat("\\nMedias Principais - Subparcela (", col_sub, "):\\n")',
        "  print(tab_t, row.names = FALSE)",
        "",
        "  if (!is.na(p_int) && p_int <= alfa) {",
        "    n_sub <- nlevels(subdados$Subparcela)",
        "    qm_comb <- (qm_res_a + (n_sub - 1) * qm_res_b) / n_sub",
        "    gl_comb <- ((qm_res_a + (n_sub - 1) * qm_res_b)^2) / ((qm_res_a^2 / gl_res_a) + (((n_sub - 1) * qm_res_b)^2 / gl_res_b))",
        "",
        "    lista_p_em_t <- list()",
        "    for (nv_t in levels(subdados$Subparcela)) {",
        "      fatia <- subdados[subdados$Subparcela == nv_t, ]",
        "      tk_fatia <- HSD.test(fatia$Valor_Y, fatia$Parcela, gl_comb, qm_comb, alpha = alfa, group = TRUE, console = FALSE)",
        "      gf <- tk_fatia$groups",
        "      lista_p_em_t[[nv_t]] <- setNames(",
        '        data.frame(v, nv_t, rownames(gf), round(gf[[1]], 4), gf[["groups"]], row.names = NULL),',
        '        c("Variavel", col_sub, col_parc, "Media", "Grupo_no_Nivel")',
        "      )",
        "    }",
        "    tab_p_em_t <- do.call(rbind, lista_p_em_t)",
        "    rownames(tab_p_em_t) <- NULL",
        "    resultados_interacao[[paste0(v, '_Parc_em_Sub')]] <- tab_p_em_t",
        '    cat("\\nDesdobramento (", col_parc, "dentro de cada nivel de", col_sub, "- Erro Combinado):\\n")',
        "    print(tab_p_em_t, row.names = FALSE)",
        "",
        "    lista_t_em_p <- list()",
        "    for (nv_p in levels(subdados$Parcela)) {",
        "      fatia <- subdados[subdados$Parcela == nv_p, ]",
        "      tk_fatia <- HSD.test(fatia$Valor_Y, fatia$Subparcela, gl_res_b, qm_res_b, alpha = alfa, group = TRUE, console = FALSE)",
        "      gf <- tk_fatia$groups",
        "      lista_t_em_p[[nv_p]] <- setNames(",
        '        data.frame(v, nv_p, rownames(gf), round(gf[[1]], 4), gf[["groups"]], row.names = NULL),',
        '        c("Variavel", col_parc, col_sub, "Media", "Grupo_no_Nivel")',
        "      )",
        "    }",
        "    tab_t_em_p <- do.call(rbind, lista_t_em_p)",
        "    rownames(tab_t_em_p) <- NULL",
        "    resultados_interacao[[paste0(v, '_Sub_em_Parc')]] <- tab_t_em_p",
        '    cat("\\nDesdobramento (", col_sub, "dentro de cada nivel de", col_parc, "- Residuo b):\\n")',
        "    print(tab_t_em_p, row.names = FALSE)",
        "  }",
        "",

        #========= 6. GRÁFICO DE LINHAS E CONSOLIDAÇÃO FINAL ==============
        f"  resumo_plot <- aggregate(subdados$Valor_Y, by = list(Parcela = subdados$Parcela, Tempo = subdados$Subparcela), FUN = function(x) c(media = mean(x), erro = {expr_erro_agg}))",
        "  df_plot <- data.frame(",
        "    Parcela = resumo_plot$Parcela,",
        "    Tempo = resumo_plot$Tempo,",
        '    Media = resumo_plot$x[, "media"],',
        '    Erro_Plot = resumo_plot$x[, "erro"]',
        "  )",
        "  cores_parc <- colorRampPalette(paleta_base)(nlevels(df_plot$Parcela))",
        "  p <- ggplot(df_plot, aes(x = Tempo, y = Media, color = Parcela, group = Parcela)) +",
        *camada_pontos,
        "    geom_line(linewidth = 0.9) +",
        "    geom_point(size = 2.8) +",
        *camada_erro,
        *camada_zero,
        "    scale_color_manual(values = cores_parc) +",
        f'    labs(title = paste("Parcela Subdividida -", v), subtitle = paste0("p(", col_parc, ") = ", round(p_parc, 4), " | p(", col_sub, ") = ", round(p_sub, 4), " | p(Interacao) = ", round(p_int, 4)), x = {expr_x}, y = {expr_y}, color = col_parc)',
        "  p <- aplicar_tema_easyr(p, tem_legenda = TRUE, girar_eixo_x = TRUE)",
        "",
        "  graficos_subdividida[[v]] <- p",
        "  print(p)",
        "  salvar_grafico_easyr(p, v)",
        "}",
        "",
        "tabela_parcelas_sub <- do.call(rbind, resultados_parcela)",
        "tabela_tempos_sub <- do.call(rbind, resultados_tempo)",
        "rownames(tabela_parcelas_sub) <- NULL",
        "rownames(tabela_tempos_sub) <- NULL",
    ]
    return "\n".join(linhas) + "\n"