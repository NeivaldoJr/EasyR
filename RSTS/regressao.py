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
def gerar_script_regressao(config: dict) -> str:
    caminho = config.get("caminho_arquivo", "")
    aba = config.get("aba", "")
    fatores = config.get("fatores", {})
    dose = fatores.get("dose", "")
    bloco = fatores.get("bloco", "")
    agrupador = fatores.get("agrupador", "")
    delin_base = config.get("delineamento_base", "DIC")
    grau_forcar = str(config.get("grau_forcar") or config.get("grau_maximo") or "AUTO").upper()
    respostas = config.get("respostas", [])
    alfa = config.get("alfa", 0.05)
    cores = config.get("cores_graficos", [])
    cfg_graf = obter_config_grafico(config)

    if not dose:
        raise ValueError("Coluna de fator quantitativo (doses) não informada.")
    if not respostas:
        raise ValueError("Nenhuma variável resposta selecionada.")

    pacotes = ["ggplot2"]
    if aba:
        pacotes.append("readxl")

    vetor_vars = ", ".join(f'"{v}"' for v in respostas)
    paleta_r = montar_paleta_r(cores)
    barra_erro = cfg_graf["barra_erro"]
    expr_x, expr_y = montar_rotulos_eixos_r(cfg_graf, "col_dose", "v")

    if barra_erro == "sd":
        expr_erro_agg = "if (length(x) > 1) sd(x) else 0"
    elif barra_erro == "ci":
        expr_erro_agg = "if (length(x) > 1) qt(0.975, df = length(x) - 1) * (sd(x) / sqrt(length(x))) else 0"
    elif barra_erro == "none":
        expr_erro_agg = "0"
    else:
        expr_erro_agg = "if (length(x) > 1) sd(x) / sqrt(length(x)) else 0"

    camada_zero = ["    expand_limits(y = 0) +"] if cfg_graf["ancorar_zero"] else []

    #========= 3. PREPARAÇÃO DE BLOCO E AGRUPADOR ==============
    preparo_bloco = []
    filtro_bloco = ""
    sub_bloco = ""
    termo_bloco = ""
    if delin_base == "DBC" and bloco:
        preparo_bloco = [
            f'col_bloco <- resolver_coluna_easyr(dados, "{bloco}")',
            "dados$Bloco_Reg <- as.factor(trimws(as.character(dados[[col_bloco]])))",
        ]
        filtro_bloco = " & !is.na(dados$Bloco_Reg)"
        sub_bloco = "Bloco_Reg = droplevels(dados$Bloco_Reg[validos]),"
        termo_bloco = "Bloco_Reg + "

    preparo_grupo = []
    filtro_grupo = ""
    sub_grupo = ""
    if agrupador:
        preparo_grupo = [
            f'col_agrup <- resolver_coluna_easyr(dados, "{agrupador}")',
            "dados$Grupo_Reg <- as.factor(trimws(as.character(dados[[col_agrup]])))",
        ]
        filtro_grupo = " & !is.na(dados$Grupo_Reg)"
        sub_grupo = "Grupo_Reg = droplevels(dados$Grupo_Reg[validos]),"

    #========= 4. CABEÇALHO R E CONFIGURAÇÃO DO LOOP ==============
    linhas = [
        *montar_cabecalho_pacotes(pacotes),
        "",
        *montar_leitura_dados(caminho, aba),
        f'col_dose <- resolver_coluna_easyr(dados, "{dose}")',
        'dados$Dose_Num <- suppressWarnings(as.numeric(gsub(",", ".", as.character(dados[[col_dose]]))))',
        *preparo_bloco,
        *preparo_grupo,
        "",
        *montar_helpers_grafico_r(config),
        "",
        *montar_bloco_salvar_grafico(config, "Regressao"),
        "",
        f"variaveis <- c({vetor_vars})",
        f"alfa <- {alfa}",
        f'grau_forcar <- "{grau_forcar}"',
        f"paleta_base <- {paleta_r}",
        "resultados_regressao <- list()",
        "equacoes_regressao <- list()",
        "graficos_regressao <- list()",
        "",
        "for (v in variaveis) {",
        "  col_y <- resolver_coluna_easyr(dados, v)",
        '  y_num <- suppressWarnings(as.numeric(gsub(",", ".", as.character(dados[[col_y]]))))',
        f"  validos <- !is.na(y_num) & !is.na(dados$Dose_Num){filtro_bloco}{filtro_grupo}",
        "  subdados <- data.frame(",
        "    dose_num = dados$Dose_Num[validos],",
        f"    {sub_bloco}",
        f"    {sub_grupo}",
        "    Valor_Y = y_num[validos]",
        "  )",
        "  subdados$dose_fac <- as.factor(subdados$dose_num)",
        "  k_doses <- nlevels(subdados$dose_fac)",
        '  if (k_doses < 2) stop("Sao necessarios pelo menos 2 niveis quantitativos distintos para regressao.")',
        "",
        "  grau_teto <- min(3, k_doses - 1)",
        '  if (grau_forcar == "1") grau_max <- 1',
        '  else if (grau_forcar == "2") grau_max <- min(2, k_doses - 1)',
        "  else grau_max <- grau_teto",
        "",
    ]

    #========= 5. REGRESSÃO POLINOMIAL GERAL (SEM AGRUPADOR) ==============
    if not agrupador:
        camada_ic_simples = (
            ["    geom_ribbon(data = df_curva, aes(x = dose_num, ymin = y_lwr, ymax = y_upr), fill = cor_linha, alpha = 0.16, inherit.aes = FALSE) +"]
            if cfg_graf["reg_ic"]
            else []
        )
        camada_erro_simples = (
            ["    geom_errorbar(aes(ymin = Media - Erro_Plot, ymax = Media + Erro_Plot), width = (max(df_pts$dose_num) - min(df_pts$dose_num)) * 0.03, color = cor_ponto, linewidth = 0.55) +"]
            if barra_erro != "none"
            else []
        )
        camada_pontos_simples = (
            ["    geom_jitter(data = subdados, aes(x = dose_num, y = Valor_Y), width = (max(df_pts$dose_num) - min(df_pts$dose_num)) * 0.015, size = 1.8, alpha = 0.45, color = cor_ponto, inherit.aes = FALSE) +"]
            if cfg_graf["mostrar_pontos"]
            else []
        )
        expr_subtitulo_simples = "eq_txt" if cfg_graf["reg_equacao"] else "NULL"

        linhas += [
            f"  mod_trat <- aov(Valor_Y ~ {termo_bloco}dose_fac, data = subdados)",
            "  gl_res <- df.residual(mod_trat)",
            '  if (gl_res == 0) stop("Sem repeticoes suficientes para estimar o erro experimental.")',
            "  tab_anova_trat <- anova(mod_trat)",
            '  sq_trat <- tab_anova_trat["dose_fac", "Sum Sq"]',
            '  sq_res <- tab_anova_trat["Residuals", "Sum Sq"]',
            '  qm_res <- tab_anova_trat["Residuals", "Mean Sq"]',
            "  if (is.na(qm_res) || qm_res <= 1e-12 || is.na(sq_trat) || sq_trat <= 1e-12) {",
            '    warning(paste("Variavel sem variancia suficiente para regressao:", v))',
            "    next",
            "  }",
            "",
            "  linhas_reg <- list()",
            "  sq_acum <- 0",
            "  for (g in seq_len(grau_max)) {",
            "    if (g == 1) form_g <- Valor_Y ~ dose_num",
            "    if (g == 2) form_g <- Valor_Y ~ dose_num + I(dose_num^2)",
            "    if (g == 3) form_g <- Valor_Y ~ dose_num + I(dose_num^2) + I(dose_num^3)",
            "    mod_g <- lm(form_g, data = subdados)",
            "    sq_modelo_g <- sum(anova(mod_g)[seq_len(g), 'Sum Sq'])",
            "    sq_ef <- sq_modelo_g - sq_acum",
            "    sq_acum <- sq_modelo_g",
            "    f_calc <- sq_ef / qm_res",
            "    p_val <- pf(f_calc, 1, gl_res, lower.tail = FALSE)",
            "    r2_val <- (sq_modelo_g / sq_trat) * 100",
            "    linhas_reg[[g]] <- data.frame(",
            "      Variavel = v, Efeito = paste0('Regressao ', g, 'o Grau'), GL = 1,",
            "      SQ = round(sq_ef, 4), QM = round(sq_ef, 4), F_calc = round(f_calc, 4),",
            "      p_valor = round(p_val, 6), R2_pct = round(r2_val, 2), row.names = NULL",
            "    )",
            "  }",
            "",
            "  gl_desvio <- (k_doses - 1) - grau_max",
            "  if (gl_desvio > 0) {",
            "    sq_desv <- max(0, sq_trat - sq_acum)",
            "    qm_desv <- sq_desv / gl_desvio",
            "    f_desv <- qm_desv / qm_res",
            "    p_desv <- pf(f_desv, gl_desvio, gl_res, lower.tail = FALSE)",
            "    linhas_reg[[length(linhas_reg) + 1]] <- data.frame(",
            "      Variavel = v, Efeito = 'Desvio da Regressao', GL = gl_desvio,",
            "      SQ = round(sq_desv, 4), QM = round(qm_desv, 4), F_calc = round(f_desv, 4),",
            "      p_valor = round(p_desv, 6), R2_pct = NA, row.names = NULL",
            "    )",
            "  }",
            "",
            "  linhas_reg[[length(linhas_reg) + 1]] <- data.frame(",
            "    Variavel = v, Efeito = 'Residuo', GL = gl_res,",
            "    SQ = round(sq_res, 4), QM = round(qm_res, 4), F_calc = NA, p_valor = NA, R2_pct = NA, row.names = NULL",
            "  )",
            "",
            "  tabela_reg <- do.call(rbind, linhas_reg)",
            "  resultados_regressao[[v]] <- tabela_reg",
            "  sig_graus <- which(!is.na(tabela_reg$p_valor[seq_len(grau_max)]) & tabela_reg$p_valor[seq_len(grau_max)] <= alfa)",
            "  grau_escolhido <- ifelse(length(sig_graus) > 0, max(sig_graus), 1)",
            "  if (grau_escolhido == 1) form_final <- Valor_Y ~ dose_num",
            "  if (grau_escolhido == 2) form_final <- Valor_Y ~ dose_num + I(dose_num^2)",
            "  if (grau_escolhido == 3) form_final <- Valor_Y ~ dose_num + I(dose_num^2) + I(dose_num^3)",
            "",
            "  mod_final <- lm(form_final, data = subdados)",
            "  coefs <- coef(mod_final)",
            "  if (any(is.na(coefs))) {",
            "    grau_escolhido <- 1",
            "    mod_final <- lm(Valor_Y ~ dose_num, data = subdados)",
            "    coefs <- coef(mod_final)",
            "  }",
            "  r2_final <- round((sum(anova(mod_final)[seq_len(grau_escolhido), 'Sum Sq']) / sq_trat) * 100, 2)",
            "  if (grau_escolhido == 1) {",
            "    eq_txt <- sprintf('y = %.4f %+.4fx  (R2 = %.2f%%)', coefs[1], coefs[2], r2_final)",
            "    ponto_critico <- 'Nao aplicavel (modelo linear)'",
            "  } else if (grau_escolhido == 2 && length(coefs) >= 3 && !is.na(coefs[3]) && abs(coefs[3]) > 1e-12) {",
            "    eq_txt <- sprintf('y = %.4f %+.4fx %+.4fx2  (R2 = %.2f%%)', coefs[1], coefs[2], coefs[3], r2_final)",
            "    x_crit <- -coefs[2] / (2 * coefs[3])",
            "    y_crit <- coefs[1] + coefs[2] * x_crit + coefs[3] * (x_crit^2)",
            "    tipo_crit <- ifelse(coefs[3] < 0, 'Maximo', 'Minimo')",
            "    ponto_critico <- sprintf('%s em x = %.4f (y = %.4f)', tipo_crit, x_crit, y_crit)",
            "  } else {",
            "    eq_txt <- sprintf('y = %.4f %+.4fx %+.4fx2 %+.4fx3  (R2 = %.2f%%)', coefs[1], coefs[2], coefs[3], coefs[4], r2_final)",
            "    ponto_critico <- 'Modelo cubico (avaliar inflexao na curva)'",
            "  }",
            "",
            '  cat("\\n==============================================\\n")',
            '  cat("REGRESSAO POLINOMIAL - Variavel:", v, "| alfa =", alfa, "\\n")',
            '  cat("==============================================\\n")',
            "  print(tabela_reg, row.names = FALSE)",
            '  cat("\\nModelo Selecionado:", eq_txt, "\\n")',
            '  cat("Ponto Critico:", ponto_critico, "\\n")',
            "",
            "  grade_x <- seq(min(subdados$dose_num), max(subdados$dose_num), length.out = 200)",
            "  df_curva <- data.frame(dose_num = grade_x)",
            "  pred_ci <- as.data.frame(suppressWarnings(predict(mod_final, newdata = df_curva, interval = 'confidence', level = 1 - alfa)))",
            "  df_curva$y_pred <- pred_ci$fit",
            "  df_curva$y_lwr <- pred_ci$lwr",
            "  df_curva$y_upr <- pred_ci$upr",
            f"  resumo_pts <- aggregate(subdados$Valor_Y, by = list(dose_num = subdados$dose_num), FUN = function(x) c(media = mean(x), erro = {expr_erro_agg}))",
            "  df_pts <- data.frame(dose_num = resumo_pts$dose_num, Media = resumo_pts$x[, 'media'], Erro_Plot = resumo_pts$x[, 'erro'])",
            "  cor_linha <- paleta_base[1]",
            "  cor_ponto <- ifelse(length(paleta_base) >= 2, paleta_base[2], paleta_base[1])",
            "  p <- ggplot(df_pts, aes(x = dose_num, y = Media)) +",
            *camada_ic_simples,
            *camada_pontos_simples,
            "    geom_line(data = df_curva, aes(x = dose_num, y = y_pred), color = cor_linha, linewidth = 1.1) +",
            *camada_erro_simples,
            "    geom_point(color = cor_ponto, size = 3) +",
            *camada_zero,
            f'    labs(title = paste("Regressao -", v), subtitle = {expr_subtitulo_simples}, x = {expr_x}, y = {expr_y})',
            "  p <- aplicar_tema_easyr(p, tem_legenda = FALSE, girar_eixo_x = TRUE)",
            "  graficos_regressao[[v]] <- p",
            "  print(p)",
            "  salvar_grafico_easyr(p, v)",
            "}",
        ]

    #========= 6. REGRESSÃO POLINOMIAL POR GRUPO (COM AGRUPADOR) ==============
    else:
        camada_ic_gp = (
            [
                "    geom_ribbon(data = df_curvas, aes(x = dose_num, ymin = y_lwr, ymax = y_upr, fill = Grupo_Reg), alpha = 0.14, inherit.aes = FALSE) +",
                '    scale_fill_manual(values = cores_gp, guide = "none") +',
            ]
            if cfg_graf["reg_ic"]
            else []
        )
        camada_erro_gp = (
            ["    geom_errorbar(aes(ymin = Media - Erro_Plot, ymax = Media + Erro_Plot), width = (max(df_pts$dose_num) - min(df_pts$dose_num)) * 0.03, linewidth = 0.5) +"]
            if barra_erro != "none"
            else []
        )
        camada_pontos_gp = (
            ["    geom_jitter(data = subdados, aes(x = dose_num, y = Valor_Y, color = Grupo_Reg), width = (max(df_pts$dose_num) - min(df_pts$dose_num)) * 0.015, size = 1.8, alpha = 0.45, inherit.aes = FALSE) +"]
            if cfg_graf["mostrar_pontos"]
            else []
        )

        if cfg_graf["reg_linetype"]:
            linha_curva_gp = "    geom_line(data = df_curvas, aes(x = dose_num, y = y_pred, color = Grupo_Reg, linetype = Grupo_Reg), linewidth = 1.05) +"
            labs_gp = f'    labs(title = paste("Regressao por", col_agrup, "-", v), subtitle = sub_eq_gp, x = {expr_x}, y = {expr_y}, color = col_agrup, linetype = col_agrup)'
        else:
            linha_curva_gp = "    geom_line(data = df_curvas, aes(x = dose_num, y = y_pred, color = Grupo_Reg), linewidth = 1.05) +"
            labs_gp = f'    labs(title = paste("Regressao por", col_agrup, "-", v), subtitle = sub_eq_gp, x = {expr_x}, y = {expr_y}, color = col_agrup)'

        linha_sub_eq = (
            '  sub_eq_gp <- paste(paste0(tab_eq$Grupo, ": ", tab_eq$Equacao), collapse = "\\n")'
            if cfg_graf["reg_equacao"]
            else "  sub_eq_gp <- NULL"
        )

        linhas += [
            "  niveis_gp <- levels(subdados$Grupo_Reg)",
            "  lista_eq <- list()",
            "  lista_curvas <- list()",
            "  for (gp in niveis_gp) {",
            "    fatia <- subdados[subdados$Grupo_Reg == gp, ]",
            "    g_gp <- min(grau_max, length(unique(fatia$dose_num)) - 1)",
            "    if (g_gp < 1) next",
            "    if (g_gp == 1) form_gp <- Valor_Y ~ dose_num",
            "    if (g_gp == 2) form_gp <- Valor_Y ~ dose_num + I(dose_num^2)",
            "    if (g_gp == 3) form_gp <- Valor_Y ~ dose_num + I(dose_num^2) + I(dose_num^3)",
            "    mod_gp <- lm(form_gp, data = fatia)",
            "    cf <- coef(mod_gp)",
            "    if (any(is.na(cf))) {",
            "      g_gp <- 1",
            "      mod_gp <- lm(Valor_Y ~ dose_num, data = fatia)",
            "      cf <- coef(mod_gp)",
            "    }",
            "    r2_gp <- round(suppressWarnings(summary(mod_gp)$r.squared) * 100, 2)",
            "    if (is.na(r2_gp)) r2_gp <- 0",
            "    if (g_gp == 1) eq_gp <- sprintf('y = %.4f %+.4fx (R2 = %.1f%%)', cf[1], cf[2], r2_gp)",
            "    else if (g_gp == 2) eq_gp <- sprintf('y = %.4f %+.4fx %+.4fx2 (R2 = %.1f%%)', cf[1], cf[2], cf[3], r2_gp)",
            "    else eq_gp <- sprintf('y = %.4f %+.4fx %+.4fx2 %+.4fx3 (R2 = %.1f%%)', cf[1], cf[2], cf[3], cf[4], r2_gp)",
            "    lista_eq[[gp]] <- data.frame(Variavel = v, Grupo = gp, Grau = g_gp, Equacao = eq_gp, row.names = NULL)",
            "    gx <- seq(min(fatia$dose_num), max(fatia$dose_num), length.out = 150)",
            "    dfc <- data.frame(dose_num = gx, Grupo_Reg = factor(gp, levels = niveis_gp))",
            "    pred_ci <- as.data.frame(suppressWarnings(predict(mod_gp, newdata = dfc, interval = 'confidence', level = 1 - alfa)))",
            "    dfc$y_pred <- pred_ci$fit",
            "    dfc$y_lwr <- pred_ci$lwr",
            "    dfc$y_upr <- pred_ci$upr",
            "    lista_curvas[[gp]] <- dfc",
            "  }",
            "  if (length(lista_eq) == 0) next",
            "  tab_eq <- do.call(rbind, lista_eq)",
            "  df_curvas <- do.call(rbind, lista_curvas)",
            "  equacoes_regressao[[v]] <- tab_eq",
            linha_sub_eq,
            '  cat("\\n==============================================\\n")',
            '  cat("REGRESSAO POR GRUPO (", col_agrup, ") - Variavel:", v, "\\n")',
            '  cat("==============================================\\n")',
            "  print(tab_eq, row.names = FALSE)",
            f"  resumo_pts <- aggregate(subdados$Valor_Y, by = list(dose_num = subdados$dose_num, Grupo_Reg = subdados$Grupo_Reg), FUN = function(x) c(media = mean(x), erro = {expr_erro_agg}))",
            "  df_pts <- data.frame(dose_num = resumo_pts$dose_num, Grupo_Reg = resumo_pts$Grupo_Reg, Media = resumo_pts$x[, 'media'], Erro_Plot = resumo_pts$x[, 'erro'])",
            "  cores_gp <- colorRampPalette(paleta_base)(length(niveis_gp))",
            "  p <- ggplot(df_pts, aes(x = dose_num, y = Media, color = Grupo_Reg)) +",
            *camada_ic_gp,
            *camada_pontos_gp,
            linha_curva_gp,
            *camada_erro_gp,
            "    geom_point(size = 2.8) +",
            *camada_zero,
            "    scale_color_manual(values = cores_gp) +",
            labs_gp,
            "  p <- aplicar_tema_easyr(p, tem_legenda = TRUE, girar_eixo_x = TRUE)",
            "  graficos_regressao[[v]] <- p",
            "  print(p)",
            "  salvar_grafico_easyr(p, v)",
            "}",
        ]

    return "\n".join(linhas) + "\n"