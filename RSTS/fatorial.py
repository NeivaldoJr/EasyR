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
def gerar_script_fatorial(config: dict) -> str:
    caminho = config.get("caminho_arquivo", "")
    aba = config.get("aba", "")
    fatores = config.get("fatores", {})
    fator_a = fatores.get("fator_a", "")
    fator_b = fatores.get("fator_b", "")
    fator_c = fatores.get("fator_c", "")
    bloco = fatores.get("bloco", "")
    delin_base = config.get("delineamento_base", "DIC")
    respostas = config.get("respostas", [])
    alfa = config.get("alfa", 0.05)
    cores = config.get("cores_graficos", [])
    cfg_graf = obter_config_grafico(config)

    if not fator_a or not fator_b:
        raise ValueError("Selecione pelo menos o Fator A e o Fator B para o esquema fatorial.")
    selecionados = [f for f in [fator_a, fator_b, fator_c, bloco] if f]
    if len(set(selecionados)) < len(selecionados):
        raise ValueError("Os fatores e o bloco devem ser colunas distintas.")
    if delin_base == "DBC" and not bloco:
        raise ValueError("Informe a coluna de Bloco para o esquema fatorial em DBC.")
    if not respostas:
        raise ValueError("Nenhuma variável resposta selecionada.")

    #========= 3. PREPARAÇÃO DOS FATORES E FÓRMULA DO MODELO ==============
    pacotes = ["agricolae", "ggplot2"]
    if aba:
        pacotes.append("readxl")

    vetor_vars = ", ".join(f'"{v}"' for v in respostas)
    paleta_r = montar_paleta_r(cores)
    cor_txt = cfg_graf["cor_texto"]
    barra_erro = cfg_graf["barra_erro"]
    expr_x, expr_y = montar_rotulos_eixos_r(cfg_graf, "col_fat_a", "v")

    if barra_erro == "sd":
        expr_erro_agg = "if (length(x) > 1) sd(x) else 0"
    elif barra_erro == "ci":
        expr_erro_agg = "if (length(x) > 1) qt(0.975, df = length(x) - 1) * (sd(x) / sqrt(length(x))) else 0"
    elif barra_erro == "none":
        expr_erro_agg = "0"
    else:
        expr_erro_agg = "if (length(x) > 1) sd(x) / sqrt(length(x)) else 0"

    camada_erro = (
        [f'    geom_errorbar(aes(ymin = Media - Erro_Plot, ymax = Media + Erro_Plot), position = pos_dodge, width = 0.2, linewidth = 0.5, color = "{cor_txt}") +']
        if barra_erro != "none"
        else []
    )
    camada_pontos = (
        [f'    geom_point(data = subdados, aes(x = FatA, y = Valor_Y, group = FatB), position = position_jitterdodge(jitter.width = 0.12, dodge.width = 0.72), size = 1.9, alpha = 0.72, color = "{cor_txt}", inherit.aes = FALSE) +']
        if cfg_graf["mostrar_pontos"]
        else []
    )

    if cfg_graf["ancorar_zero"]:
        bloco_escala_y = [
            "  limite_inf <- min(0, min(vals_min, na.rm = TRUE) * 1.15)",
            "  limite_sup <- max(0.0001, max(vals_max, na.rm = TRUE) * 1.18)",
            "  escala_y <- scale_y_continuous(limits = c(limite_inf, limite_sup), expand = c(0, 0))",
        ]
    else:
        bloco_escala_y = [
            "  escala_y <- scale_y_continuous(expand = expansion(mult = c(0.08, 0.16)))",
        ]

    prep_c = [
        f'col_fat_c <- resolver_coluna_easyr(dados, "{fator_c}")',
        "dados$FatC <- as.factor(trimws(as.character(dados[[col_fat_c]])))",
    ] if fator_c else []

    prep_b = [
        f'col_bloco <- resolver_coluna_easyr(dados, "{bloco}")',
        "dados$Bloco_Fat <- as.factor(trimws(as.character(dados[[col_bloco]])))",
    ] if (delin_base == "DBC" and bloco) else []

    filtro_extra = (" & !is.na(dados$FatC)" if fator_c else "") + (" & !is.na(dados$Bloco_Fat)" if (delin_base == "DBC" and bloco) else "")
    sub_c = "FatC = droplevels(dados$FatC[validos])," if fator_c else ""
    sub_b = "Bloco_Fat = droplevels(dados$Bloco_Fat[validos])," if (delin_base == "DBC" and bloco) else ""

    termo_interacao = "FatA * FatB" + (" * FatC" if fator_c else "")
    formula_r = f"Valor_Y ~ {'Bloco_Fat + ' if (delin_base == 'DBC' and bloco) else ''}{termo_interacao}"

    #========= 4. CABEÇALHO R, LEITURA DE DADOS E SALVAMENTO ==============
    linhas = [
        *montar_cabecalho_pacotes(pacotes),
        "",
        *montar_leitura_dados(caminho, aba),
        f'col_fat_a <- resolver_coluna_easyr(dados, "{fator_a}")',
        f'col_fat_b <- resolver_coluna_easyr(dados, "{fator_b}")',
        "dados$FatA <- as.factor(trimws(as.character(dados[[col_fat_a]])))",
        "dados$FatB <- as.factor(trimws(as.character(dados[[col_fat_b]])))",
        *prep_c,
        *prep_b,
        "",
        *montar_helpers_grafico_r(config),
        "",
        *montar_bloco_salvar_grafico(config, f"Fatorial_{delin_base}"),
        "",
        f"variaveis <- c({vetor_vars})",
        f"alfa <- {alfa}",
        f"paleta_base <- {paleta_r}",
        'mapa_nomes_fatores <- c(FatA = col_fat_a, FatB = col_fat_b' + (', FatC = col_fat_c)' if fator_c else ')'),
        "resultados_anova_fat <- list()",
        "resultados_medias_fat <- list()",
        "desdobramentos_fat <- list()",
        "graficos_fatorial <- list()",
        "",

        #========= 5. LOOP POR VARIÁVEL: ANOVA E EFEITOS PRINCIPAIS ==============
        "for (v in variaveis) {",
        "  col_y <- resolver_coluna_easyr(dados, v)",
        '  y_num <- suppressWarnings(as.numeric(gsub(",", ".", as.character(dados[[col_y]]))))',
        f"  validos <- !is.na(y_num) & !is.na(dados$FatA) & !is.na(dados$FatB){filtro_extra}",
        "  subdados <- data.frame(",
        "    FatA = droplevels(dados$FatA[validos]),",
        "    FatB = droplevels(dados$FatB[validos]),",
        f"    {sub_c}",
        f"    {sub_b}",
        "    Valor_Y = y_num[validos]",
        "  )",
        "",
        f"  mod_fat <- aov({formula_r}, data = subdados)",
        "  gl_res <- df.residual(mod_fat)",
        '  if (gl_res == 0) stop("Sem graus de liberdade suficientes para estimar o residuo.")',
        "",
        "  tab_anova <- as.data.frame(anova(mod_fat))",
        '  qm_res <- tab_anova[nrow(tab_anova), "Mean Sq"]',
        "  if (is.na(qm_res) || qm_res <= 1e-12) {",
        '    warning(paste("Variavel sem variancia residual (dados constantes):", v))',
        "    next",
        "  }",
        "  cv_pct <- round((sqrt(qm_res) / mean(subdados$Valor_Y, na.rm = TRUE)) * 100, 2)",
        "  resultados_anova_fat[[v]] <- tab_anova",
        "",
        '  cat("\\n==============================================\\n")',
        f'  cat("ESQUEMA FATORIAL ({delin_base}) - Variavel:", v, "| CV =", cv_pct, "% | alfa =", alfa, "\\n")',
        '  cat("==============================================\\n")',
        "  print(tab_anova)",
        "",
        "  for (fat_cod in names(mapa_nomes_fatores)) {",
        "    fat_real <- unname(mapa_nomes_fatores[fat_cod])",
        "    tk <- HSD.test(mod_fat, fat_cod, alpha = alfa, group = TRUE, unbalanced = TRUE, console = FALSE)",
        "    gp <- tk$groups",
        "    mi <- tk$means",
        "    niveis_ord <- rownames(gp)",
        '    ep_v <- mi[niveis_ord, "std"] / sqrt(mi[niveis_ord, "r"])',
        "    tab_f <- data.frame(",
        "      Variavel = v,",
        "      Fator = fat_real,",
        "      Nivel = factor(niveis_ord, levels = levels(subdados[[fat_cod]])),",
        "      Media = round(gp[[1]], 4),",
        "      EP = round(ep_v, 4),",
        '      Grupo = gp[["groups"]],',
        "      row.names = NULL",
        "    )",
        "    tab_f <- tab_f[order(tab_f$Nivel), ]",
        '    cat("\\nEfeito Principal (Tukey) -", fat_real, ":\\n")',
        "    print(tab_f, row.names = FALSE)",
        "    resultados_medias_fat[[paste(v, fat_real, sep = '_')]] <- tab_f",
        "  }",
        "",

        #========= 6. DESDOBRAMENTO DA INTERAÇÃO (A x B) ==============
        '  p_int_ab <- if ("FatA:FatB" %in% rownames(tab_anova)) tab_anova["FatA:FatB", "Pr(>F)"] else NA',
        "  if (!is.na(p_int_ab) && p_int_ab <= alfa) {",
        "    lista_a_em_b <- list()",
        "    for (nv_b in levels(subdados$FatB)) {",
        "      fatia <- droplevels(subdados[subdados$FatB == nv_b, ])",
        "      if (nrow(fatia) < 2 || nlevels(fatia$FatA) < 2) next",
        "      tk_ab <- HSD.test(fatia$Valor_Y, fatia$FatA, gl_res, qm_res, alpha = alfa, group = TRUE, console = FALSE)",
        "      gab <- tk_ab$groups",
        "      lista_a_em_b[[nv_b]] <- setNames(",
        '        data.frame(v, nv_b, rownames(gab), round(gab[[1]], 4), gab[["groups"]], row.names = NULL),',
        '        c("Variavel", col_fat_b, col_fat_a, "Media", "Grupo_no_Nivel")',
        "      )",
        "    }",
        "    if (length(lista_a_em_b) > 0) {",
        "      tab_a_em_b <- do.call(rbind, lista_a_em_b)",
        "      rownames(tab_a_em_b) <- NULL",
        "      desdobramentos_fat[[paste0(v, '_A_em_B')]] <- tab_a_em_b",
        '      cat("\\nDesdobramento (", col_fat_a, "dentro de cada nivel de", col_fat_b, "- p =", round(p_int_ab, 5), "):\\n")',
        "      print(tab_a_em_b, row.names = FALSE)",
        "    }",
        "",
        "    lista_b_em_a <- list()",
        "    for (nv_a in levels(subdados$FatA)) {",
        "      fatia <- droplevels(subdados[subdados$FatA == nv_a, ])",
        "      if (nrow(fatia) < 2 || nlevels(fatia$FatB) < 2) next",
        "      tk_ba <- HSD.test(fatia$Valor_Y, fatia$FatB, gl_res, qm_res, alpha = alfa, group = TRUE, console = FALSE)",
        "      gba <- tk_ba$groups",
        "      lista_b_em_a[[nv_a]] <- setNames(",
        '        data.frame(v, nv_a, rownames(gba), round(gba[[1]], 4), gba[["groups"]], row.names = NULL),',
        '        c("Variavel", col_fat_a, col_fat_b, "Media", "Grupo_no_Nivel")',
        "      )",
        "    }",
        "    if (length(lista_b_em_a) > 0) {",
        "      tab_b_em_a <- do.call(rbind, lista_b_em_a)",
        "      rownames(tab_b_em_a) <- NULL",
        "      desdobramentos_fat[[paste0(v, '_B_em_A')]] <- tab_b_em_a",
        '      cat("\\nDesdobramento (", col_fat_b, "dentro de cada nivel de", col_fat_a, "- p =", round(p_int_ab, 5), "):\\n")',
        "      print(tab_b_em_a, row.names = FALSE)",
        "    }",
        "  }",
        "",

        #========= 7. GRÁFICO DE BARRAS AGRUPADAS PERSONALIZADO (GGPLOT2) ==============
        f"  resumo_plot <- aggregate(subdados$Valor_Y, by = list(FatorA = subdados$FatA, FatorB = subdados$FatB), FUN = function(x) c(media = mean(x), erro = {expr_erro_agg}))",
        "  df_plot <- data.frame(",
        "    FatorA = resumo_plot$FatorA,",
        "    FatorB = resumo_plot$FatorB,",
        '    Media = resumo_plot$x[, "media"],',
        '    Erro_Plot = resumo_plot$x[, "erro"]',
        "  )",
        "  cores_b <- colorRampPalette(paleta_base)(nlevels(df_plot$FatorB))",
        "  erro_vis <- ifelse(is.na(df_plot$Erro_Plot), 0, df_plot$Erro_Plot)",
        "  vals_min <- c(df_plot$Media - erro_vis, subdados$Valor_Y)",
        "  vals_max <- c(df_plot$Media + erro_vis, subdados$Valor_Y)",
        *bloco_escala_y,
        "  pos_dodge <- position_dodge(width = 0.72)",
        "",
        "  p <- ggplot(df_plot, aes(x = FatorA, y = Media, fill = FatorB)) +",
        f'    geom_col(position = pos_dodge, width = 0.65, color = "{cor_txt}", linewidth = 0.4) +',
        *camada_erro,
        *camada_pontos,
        "    scale_fill_manual(values = cores_b) +",
        "    escala_y +",
        f'    labs(title = paste("Fatorial ({delin_base}) -", v), x = {expr_x}, y = {expr_y}, fill = col_fat_b)',
        "  p <- aplicar_tema_easyr(p, tem_legenda = TRUE, girar_eixo_x = TRUE)",
        "",
        "  graficos_fatorial[[v]] <- p",
        "  print(p)",
        "  salvar_grafico_easyr(p, v)",
        "}",
    ]
    return "\n".join(linhas) + "\n"