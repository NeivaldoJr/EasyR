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
def gerar_script_scheffe(config: dict) -> str:
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
        raise ValueError("Coluna de tratamento não informada para o Scheffé.")
    if not respostas:
        raise ValueError("Nenhuma variável resposta selecionada.")

    pacotes = ["agricolae", "ggplot2"]
    if aba:
        pacotes.append("readxl")

    vetor_vars = ", ".join(f'"{v}"' for v in respostas)
    paleta_r = montar_paleta_r(cores)
    cor_txt = cfg_graf["cor_texto"]
    barra_erro = cfg_graf["barra_erro"]
    expr_x, expr_y = montar_rotulos_eixos_r(cfg_graf, "col_trat", "v")

    if barra_erro == "sd":
        expr_erro_r = 'medias_info[trats, "std"]'
    elif barra_erro == "ci":
        expr_erro_r = 'ifelse(medias_info[trats, "r"] > 1, qt(0.975, df = medias_info[trats, "r"] - 1) * (medias_info[trats, "std"] / sqrt(medias_info[trats, "r"])), 0)'
    elif barra_erro == "none":
        expr_erro_r = "rep(0, length(trats))"
    else:
        expr_erro_r = 'medias_info[trats, "std"] / sqrt(medias_info[trats, "r"])'

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
        *montar_bloco_salvar_grafico(config, "Scheffe"),
        "",
        f"variaveis <- c({vetor_vars})",
        f"alfa <- {alfa}",
        f"paleta_base <- {paleta_r}",
        "resultados_anova_scheffe <- list()",
        "resultados_scheffe <- list()",
        "graficos_scheffe <- list()",
        "",

        #========= 5. LOOP POR VARIÁVEL: ANOVA E TESTE DE SCHEFFÉ ==============
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
        "  resultados_anova_scheffe[[v]] <- tab_anova",
        "",
        '  teste <- scheffe.test(modelo, "Tratamento", alpha = alfa, group = TRUE, console = FALSE)',
        "  grupos <- teste$groups",
        "  medias_info <- teste$means",
        "  trats <- rownames(grupos)",
        '  ep <- medias_info[trats, "std"] / sqrt(medias_info[trats, "r"])',
        f"  erro_calc <- {expr_erro_r}",
        "",
        "  tabela <- data.frame(",
        "    Variavel = v,",
        "    Tratamento = factor(trats, levels = levels(subdados$Tratamento)),",
        "    Media = round(grupos[[1]], 4),",
        "    EP = round(ep, 4),",
        "    Erro_Plot = erro_calc,",
        '    Grupo = grupos[["groups"]],',
        "    Dif_Critica = round(teste$statistics$CriticalDifference, 4),",
        "    CV_pct = round(teste$statistics$CV, 2),",
        "    row.names = NULL",
        "  )",
        "  tabela <- tabela[order(tabela$Tratamento), ]",
        '  resultados_scheffe[[v]] <- tabela[, c("Variavel", "Tratamento", "Media", "EP", "Grupo", "Dif_Critica", "CV_pct")]',
        "",
        '  cat("\\n==============================================\\n")',
        '  cat("SCHEFFE - Variavel:", v, "| alfa =", alfa, "\\n")',
        '  cat("==============================================\\n")',
        "  print(tab_anova)",
        '  cat("\\nComparacao de Medias (Scheffe):\\n")',
        "  print(resultados_scheffe[[v]], row.names = FALSE)",
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
        f'    labs(title = paste("Scheffe -", v), x = {expr_x}, y = {expr_y})',
        "  p <- aplicar_tema_easyr(p, tem_legenda = FALSE, girar_eixo_x = TRUE)",
        "",
        "  graficos_scheffe[[v]] <- p",
        "  print(p)",
        "  salvar_grafico_easyr(p, v)",
        "}",
        "",
        "tabela_final_scheffe <- do.call(rbind, resultados_scheffe)",
        "rownames(tabela_final_scheffe) <- NULL",
    ]
    return "\n".join(linhas) + "\n"