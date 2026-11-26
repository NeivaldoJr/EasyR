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
def gerar_script_pca(config: dict) -> str:
    caminho = config.get("caminho_arquivo", "")
    aba = config.get("aba", "")
    fatores = config.get("fatores", {})
    grupo = (
        fatores.get("tratamento")
        or fatores.get("grupo")
        or fatores.get("identificador")
        or ""
    )
    respostas = config.get("respostas", [])
    cores = config.get("cores_graficos", [])
    cfg_graf = obter_config_grafico(config)

    if len(respostas) < 2:
        raise ValueError("Selecione pelo menos 2 variáveis numéricas para a PCA.")

    pacotes = ["ggplot2"]
    if aba:
        pacotes.append("readxl")

    vetor_vars = ", ".join(f'"{v}"' for v in respostas)
    paleta_r = montar_paleta_r(cores)
    cor_txt = cfg_graf["cor_texto"]
    expr_x_biplot, expr_y_biplot = montar_rotulos_eixos_r(
        cfg_graf,
        'paste0("PC1 (", round(var_explicada[1], 2), "%)")',
        'paste0("PC2 (", round(var_explicada[2], 2), "%)")',
    )

    camada_rot_scree = (
        [f'  geom_text(aes(label = paste0(Variancia_pct, "%")), vjust = -0.5, fontface = "bold", size = 3.6, color = "{cor_txt}") +']
        if cfg_graf["multi_rotulos"]
        else []
    )
    camada_rot_vetores = (
        [
            "  geom_text(",
            "    data = df_vetores,",
            "    aes(x = x_fim * 1.08, y = y_fim * 1.08, label = Variavel),",
            "    inherit.aes = FALSE,",
            "    color = cor_seta,",
            '    fontface = "bold",',
            "    size = 3.7",
            "  ) +",
        ]
        if cfg_graf["multi_rotulos"]
        else []
    )
    camada_rot_obs = (
        [f'  geom_text(aes(label = Rotulo), vjust = -0.75, size = 3.0, color = "{cor_txt}", show.legend = FALSE) +']
        if (cfg_graf["multi_rotulos"] and not grupo)
        else []
    )

    #========= 3. DEFINIÇÃO DE AGRUPAMENTO E LIMPEZA DE VARIÁVEIS ==============
    if grupo:
        bloco_grupo = [
            f'col_grupo <- resolver_coluna_easyr(dados, "{grupo}")',
            "dados$Grupo_PCA <- as.factor(trimws(as.character(dados[[col_grupo]])))",
            "linhas_validas <- complete.cases(dados[, variaveis_cols, drop = FALSE]) & !is.na(dados$Grupo_PCA)",
            "dados_pca <- dados[linhas_validas, , drop = FALSE]",
            "grupos_pca <- droplevels(dados_pca$Grupo_PCA)",
            "rotulos_obs <- as.character(dados_pca$Grupo_PCA)",
            "nome_grupo <- col_grupo",
        ]
    else:
        bloco_grupo = [
            "linhas_validas <- complete.cases(dados[, variaveis_cols, drop = FALSE])",
            "dados_pca <- dados[linhas_validas, , drop = FALSE]",
            'grupos_pca <- factor(rep("Amostras", nrow(dados_pca)))',
            "rotulos_obs <- as.character(seq_len(nrow(dados_pca)))",
            'nome_grupo <- "Grupo"',
        ]

    linhas = [
        *montar_cabecalho_pacotes(pacotes),
        "",
        *montar_leitura_dados(caminho, aba),
        *montar_helpers_grafico_r(config),
        "",
        *montar_bloco_salvar_grafico(config, "PCA"),
        "",
        f"variaveis_req <- c({vetor_vars})",
        "variaveis_cols <- sapply(variaveis_req, function(v) resolver_coluna_easyr(dados, v))",
        f"paleta_base <- {paleta_r}",
        "",
        "for (col_y in variaveis_cols) {",
        '  dados[[col_y]] <- suppressWarnings(as.numeric(gsub(",", ".", as.character(dados[[col_y]]))))',
        "}",
        "",
        *bloco_grupo,
        'if (nrow(dados_pca) < 3) stop("Sao necessarias pelo menos 3 observacoes completas para executar a PCA.")',
        "",
        "matriz_x <- as.matrix(dados_pca[, variaveis_cols, drop = FALSE])",
        "colnames(matriz_x) <- variaveis_req",
        "variancia_zero <- apply(matriz_x, 2, sd, na.rm = TRUE) == 0",
        "if (any(variancia_zero)) {",
        '  stop(paste("Variaveis com variancia zero removem a escala da PCA:", paste(variaveis_req[variancia_zero], collapse = ", ")))',
        "}",
        "",

        #========= 4. CÁLCULO DA PCA, AUTOVALORES E CARGAS ==============
        "modelo_pca <- prcomp(matriz_x, center = TRUE, scale. = TRUE)",
        "autovalores <- modelo_pca$sdev^2",
        "var_explicada <- (autovalores / sum(autovalores)) * 100",
        "var_acumulada <- cumsum(var_explicada)",
        "",
        "tabela_autovalores_pca <- data.frame(",
        '  Componente = paste0("PC", seq_along(autovalores)),',
        "  Autovalor = round(autovalores, 4),",
        "  Variancia_pct = round(var_explicada, 2),",
        "  Variancia_Acumulada_pct = round(var_acumulada, 2),",
        "  row.names = NULL",
        ")",
        "",
        "cargas_mat <- modelo_pca$rotation",
        'cor_vars_pcs <- sweep(cargas_mat, 2, modelo_pca$sdev, FUN = "*")',
        "tabela_cargas_pca <- data.frame(",
        "  Variavel = rownames(cargas_mat),",
        "  round(cargas_mat, 4),",
        "  check.names = FALSE,",
        "  row.names = NULL",
        ")",
        "tabela_correlacao_pcs <- data.frame(",
        "  Variavel = rownames(cor_vars_pcs),",
        "  round(cor_vars_pcs, 4),",
        "  check.names = FALSE,",
        "  row.names = NULL",
        ")",
        "",
        "scores_pca <- as.data.frame(modelo_pca$x)",
        "scores_pca$Grupo <- grupos_pca",
        "scores_pca$Rotulo <- rotulos_obs",
        "",
        'cat("\\n==============================================\\n")',
        'cat("ANALISE DE COMPONENTES PRINCIPAIS (PCA)\\n")',
        'cat("Observacoes:", nrow(dados_pca), "| Variaveis:", length(variaveis_req), "\\n")',
        'cat("==============================================\\n")',
        'cat("\\nAutovalores e Variancia Explicada:\\n")',
        "print(tabela_autovalores_pca, row.names = FALSE)",
        'cat("\\nAutovetores (Cargas / Loadings):\\n")',
        "print(tabela_cargas_pca, row.names = FALSE)",
        'cat("\\nCorrelacao entre Variaveis e Componentes Principais:\\n")',
        "print(tabela_correlacao_pcs, row.names = FALSE)",
        "",

        #========= 5. GRÁFICO SCREE PLOT (GGPLOT2) ==============
        "cores_grupos <- colorRampPalette(paleta_base)(nlevels(scores_pca$Grupo))",
        "",
        "grafico_scree_pca <- ggplot(tabela_autovalores_pca, aes(x = factor(Componente, levels = Componente), y = Variancia_pct)) +",
        f'  geom_col(fill = paleta_base[1], color = "{cor_txt}", width = 0.6, linewidth = 0.4) +',
        "  geom_line(aes(group = 1), color = paleta_base[length(paleta_base)], linewidth = 0.8) +",
        "  geom_point(color = paleta_base[length(paleta_base)], size = 2.6) +",
        *camada_rot_scree,
        "  scale_y_continuous(limits = c(0, max(tabela_autovalores_pca$Variancia_pct) * 1.18), expand = c(0, 0)) +",
        '  labs(title = "PCA - Variancia Explicada por Componente (Scree Plot)", x = "Componente Principal", y = "Variancia Explicada (%)")',
        "grafico_scree_pca <- aplicar_tema_easyr(grafico_scree_pca, tem_legenda = FALSE, girar_eixo_x = FALSE, mostrar_eixo_x = TRUE)",
        "",
        "print(grafico_scree_pca)",
        'salvar_grafico_easyr(grafico_scree_pca, "ScreePlot")',
        "",

        #========= 6. GRÁFICO BIPLOT (GGPLOT2) ==============
        "escala_x <- max(abs(scores_pca$PC1), na.rm = TRUE)",
        "escala_y <- max(abs(scores_pca$PC2), na.rm = TRUE)",
        "max_carga_x <- max(abs(cargas_mat[, 1]), na.rm = TRUE)",
        "max_carga_y <- max(abs(cargas_mat[, 2]), na.rm = TRUE)",
        "fator_seta <- 0.82 * min(ifelse(max_carga_x > 0, escala_x / max_carga_x, 1), ifelse(max_carga_y > 0, escala_y / max_carga_y, 1))",
        "",
        "df_vetores <- data.frame(",
        "  Variavel = rownames(cargas_mat),",
        "  x_fim = cargas_mat[, 1] * fator_seta,",
        "  y_fim = cargas_mat[, 2] * fator_seta",
        ")",
        "",
        f'cor_seta <- ifelse(length(paleta_base) >= 2, paleta_base[2], "{cor_txt}")',
        "grafico_biplot_pca <- ggplot(scores_pca, aes(x = PC1, y = PC2, color = Grupo)) +",
        '  geom_hline(yintercept = 0, linetype = "dashed", color = "grey65", linewidth = 0.45) +',
        '  geom_vline(xintercept = 0, linetype = "dashed", color = "grey65", linewidth = 0.45) +',
        "  geom_point(size = 3.2, alpha = 0.9) +",
        *camada_rot_obs,
        "  geom_segment(",
        "    data = df_vetores,",
        "    aes(x = 0, y = 0, xend = x_fim, yend = y_fim),",
        "    inherit.aes = FALSE,",
        '    arrow = arrow(length = unit(0.22, "cm"), type = "closed"),',
        "    color = cor_seta,",
        "    linewidth = 0.75",
        "  ) +",
        *camada_rot_vetores,
        "  scale_color_manual(values = cores_grupos) +",
        "  labs(",
        '    title = "PCA - Biplot (Componentes Principais 1 e 2)",',
        '    subtitle = paste0("Variancia acumulada (PC1 + PC2): ", round(var_acumulada[2], 2), "%"),',
        f"    x = {expr_x_biplot},",
        f"    y = {expr_y_biplot},",
        "    color = nome_grupo",
        "  )",
    ]

    if grupo and cfg_graf["pca_elipse"]:
        linhas.extend([
            "if (any(table(scores_pca$Grupo) >= 3)) {",
            '  grafico_biplot_pca <- grafico_biplot_pca + stat_ellipse(level = 0.95, linewidth = 0.65, linetype = "dashed", show.legend = FALSE)',
            "}",
        ])

    linhas.extend([
        f"grafico_biplot_pca <- aplicar_tema_easyr(grafico_biplot_pca, tem_legenda = {'TRUE' if grupo else 'FALSE'}, girar_eixo_x = FALSE, mostrar_eixo_x = TRUE)",
        "",
        "print(grafico_biplot_pca)",
        'salvar_grafico_easyr(grafico_biplot_pca, "Biplot")',
    ])
    return "\n".join(linhas) + "\n"