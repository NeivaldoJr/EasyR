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
def gerar_script_rca(config: dict) -> str:
    caminho = config.get("caminho_arquivo", "")
    aba = config.get("aba", "")
    fatores = config.get("fatores", {})
    grupo = (
        fatores.get("tratamento")
        or fatores.get("grupo")
        or fatores.get("identificador")
        or ""
    )
    metodo_cor = str(config.get("metodo_correlacao", "pearson")).lower().strip()
    if metodo_cor not in ("pearson", "spearman"):
        metodo_cor = "pearson"
    nome_metodo = "Pearson" if metodo_cor == "pearson" else "Spearman"

    respostas = config.get("respostas", [])
    alfa = config.get("alfa", 0.05)
    cores = config.get("cores_graficos", [])
    cfg_graf = obter_config_grafico(config)

    if len(respostas) < 2:
        raise ValueError("Selecione pelo menos 2 variáveis numéricas para correlação e agrupamento.")

    pacotes = ["ggplot2"]
    if aba:
        pacotes.append("readxl")

    vetor_vars = ", ".join(f'"{v}"' for v in respostas)
    paleta_r = montar_paleta_r(cores)
    cor_txt = cfg_graf["cor_texto"]
    expr_x_cor, expr_y_cor = montar_rotulos_eixos_r(cfg_graf, "NULL", "NULL")
    expr_x_den, expr_y_den = montar_rotulos_eixos_r(cfg_graf, "NULL", '"Distancia Euclidiana (Ward.D2)"')

    camada_rot_cor = (
        [f'  geom_text(aes(label = rotulo), fontface = "bold", size = 3.8, color = "{cor_txt}") +']
        if cfg_graf["multi_rotulos"]
        else []
    )
    camada_rot_den = (
        ['    geom_text(data = df_folhas, aes(x = x, y = -y_offset_lbl, label = rotulo, color = cluster), angle = 45, hjust = 1, fontface = "bold", size = 3.5, show.legend = FALSE) +']
        if cfg_graf["multi_rotulos"]
        else []
    )
    limite_inf_den = "-max(hc$height) * 0.28" if cfg_graf["multi_rotulos"] else "-max(hc$height) * 0.05"

    #========= 3. PREPARAÇÃO DOS DADOS PARA CORRELAÇÃO E AGRUPAMENTO ==============
    if grupo:
        bloco_agrupamento = [
            f'col_grupo <- resolver_coluna_easyr(dados, "{grupo}")',
            "dados$Grupo_RCA <- as.factor(trimws(as.character(dados[[col_grupo]])))",
            "dados_validos <- dados[complete.cases(dados[, variaveis_cols, drop = FALSE]) & !is.na(dados$Grupo_RCA), , drop = FALSE]",
            "medias_grupo <- aggregate(dados_validos[, variaveis_cols, drop = FALSE], by = list(Grupo = dados_validos$Grupo_RCA), FUN = mean, na.rm = TRUE)",
            "rownames(medias_grupo) <- as.character(medias_grupo$Grupo)",
            "matriz_cluster <- scale(as.matrix(medias_grupo[, variaveis_cols, drop = FALSE]))",
            'titulo_dendro <- paste("Agrupamento Hierarquico (Ward / Distancia Euclidiana) -", col_grupo)',
        ]
    else:
        bloco_agrupamento = [
            "dados_validos <- dados[complete.cases(dados[, variaveis_cols, drop = FALSE]), , drop = FALSE]",
            'rownames(dados_validos) <- paste0("Obs_", seq_len(nrow(dados_validos)))',
            "matriz_cluster <- scale(as.matrix(dados_validos[, variaveis_cols, drop = FALSE]))",
            'titulo_dendro <- "Agrupamento Hierarquico (Ward / Distancia Euclidiana)"',
        ]

    linhas = [
        *montar_cabecalho_pacotes(pacotes),
        "",
        *montar_leitura_dados(caminho, aba),
        *montar_helpers_grafico_r(config),
        "",
        *montar_bloco_salvar_grafico(config, "RCA"),
        "",
        f"variaveis_req <- c({vetor_vars})",
        "variaveis_cols <- sapply(variaveis_req, function(v) resolver_coluna_easyr(dados, v))",
        f"alfa <- {alfa}",
        f"paleta_base <- {paleta_r}",
        "",
        "for (col_y in variaveis_cols) {",
        '  dados[[col_y]] <- suppressWarnings(as.numeric(gsub(",", ".", as.character(dados[[col_y]]))))',
        "}",
        "",
        *bloco_agrupamento,
        'if (nrow(dados_validos) < 3) stop("Sao necessarias pelo menos 3 observacoes completas para correlacao e agrupamento.")',
        "",

        #========= 4. MATRIZ DE CORRELAÇÃO E P-VALORES ==============
        "mat_num <- as.matrix(dados_validos[, variaveis_cols, drop = FALSE])",
        "colnames(mat_num) <- variaveis_req",
        f'mat_cor <- cor(mat_num, method = "{metodo_cor}")',
        "n_vars <- length(variaveis_req)",
        "mat_p <- matrix(NA_real_, nrow = n_vars, ncol = n_vars, dimnames = list(variaveis_req, variaveis_req))",
        "pares_cor <- list()",
        "idx_par <- 1",
        "",
        "for (i in seq_len(n_vars)) {",
        "  mat_p[i, i] <- 0",
        "  if (i < n_vars) {",
        "    for (j in (i + 1):n_vars) {",
        f'      teste_c <- suppressWarnings(cor.test(mat_num[, i], mat_num[, j], method = "{metodo_cor}"))',
        "      mat_p[i, j] <- teste_c$p.value",
        "      mat_p[j, i] <- teste_c$p.value",
        '      sig_txt <- ifelse(teste_c$p.value <= 0.001, "***", ifelse(teste_c$p.value <= 0.01, "**", ifelse(teste_c$p.value <= alfa, "*", "ns")))',
        "      pares_cor[[idx_par]] <- data.frame(",
        "        Var_1 = variaveis_req[i],",
        "        Var_2 = variaveis_req[j],",
        "        Coef_r = round(unname(teste_c$estimate), 4),",
        "        p_valor = round(teste_c$p.value, 6),",
        "        Significancia = sig_txt,",
        "        row.names = NULL",
        "      )",
        "      idx_par <- idx_par + 1",
        "    }",
        "  }",
        "}",
        "",
        "matriz_correlacao_rca <- round(mat_cor, 4)",
        "matriz_pvalor_rca <- round(mat_p, 6)",
        "tabela_pares_correlacao <- do.call(rbind, pares_cor)",
        "",
        'cat("\\n==============================================\\n")',
        f'cat("CORRELACAO ({nome_metodo.upper()}) E AGRUPAMENTO (RCA) | alfa =", alfa, "\\n")',
        'cat("==============================================\\n")',
        f'cat("\\nMatriz de Correlacao ({nome_metodo}):\\n")',
        "print(matriz_correlacao_rca)",
        'cat("\\nPares de Correlacao e Significancia:\\n")',
        "print(tabela_pares_correlacao, row.names = FALSE)",
        "",

        #========= 5. GRÁFICO CORRELOGRAMA (GGPLOT2) ==============
        "grid_cor <- expand.grid(Var1 = factor(variaveis_req, levels = variaveis_req), Var2 = factor(variaveis_req, levels = rev(variaveis_req)))",
        "grid_cor$r <- mapply(function(a, b) mat_cor[as.character(a), as.character(b)], grid_cor$Var1, grid_cor$Var2)",
        "grid_cor$p <- mapply(function(a, b) mat_p[as.character(a), as.character(b)], grid_cor$Var1, grid_cor$Var2)",
        "grid_cor$rotulo <- ifelse(",
        "  as.character(grid_cor$Var1) == as.character(grid_cor$Var2),",
        '  "1.00",',
        '  paste0(sprintf("%.2f", grid_cor$r), ifelse(grid_cor$p <= alfa, "*", ""))',
        ")",
        "",
        "cor_alta <- paleta_base[1]",
        'cor_baixa <- ifelse(length(paleta_base) >= 3, paleta_base[3], "#3B6998")',
        "grafico_correlacao_rca <- ggplot(grid_cor, aes(x = Var1, y = Var2, fill = r)) +",
        '  geom_tile(color = "#FFFFFF", linewidth = 0.8) +',
        *camada_rot_cor,
        '  scale_fill_gradient2(low = cor_baixa, mid = "#F7F3EB", high = cor_alta, midpoint = 0, limits = c(-1, 1), name = "r") +',
        f'  labs(title = "Matriz de Correlacao de {nome_metodo} (* p <= {alfa})", x = {expr_x_cor}, y = {expr_y_cor})',
        "grafico_correlacao_rca <- aplicar_tema_easyr(grafico_correlacao_rca, tem_legenda = TRUE, girar_eixo_x = TRUE) +",
        '  theme(axis.text.x = element_text(face = "bold"), axis.text.y = element_text(face = "bold"))',
        "",
        "print(grafico_correlacao_rca)",
        'salvar_grafico_easyr(grafico_correlacao_rca, "Correlacao")',
        "",

        #========= 6. AGRUPAMENTO HIERÁRQUICO E DENDROGRAMA (GGPLOT2) ==============
        "if (nrow(matriz_cluster) >= 3) {",
        '  dist_mat <- dist(matriz_cluster, method = "euclidean")',
        '  hc <- hclust(dist_mat, method = "ward.D2")',
        "  k_grupos <- min(3, nrow(matriz_cluster) - 1)",
        "  clusters_cut <- cutree(hc, k = k_grupos)",
        "  tabela_agrupamento_rca <- data.frame(",
        "    Unidade = names(clusters_cut),",
        "    Cluster = as.integer(clusters_cut),",
        "    row.names = NULL",
        "  )",
        '  cat("\\nClassificacao por Agrupamento Hierarquico (k =", k_grupos, "grupos):\\n")',
        "  print(tabela_agrupamento_rca, row.names = FALSE)",
        "",
        "  n_itens <- length(hc$order)",
        "  pos_x <- numeric(n_itens)",
        "  pos_x[hc$order] <- seq_len(n_itens)",
        "  alturas_nos <- numeric(nrow(hc$merge))",
        "  coord_x_nos <- numeric(nrow(hc$merge))",
        "  seg_list <- list()",
        "",
        "  for (m in seq_len(nrow(hc$merge))) {",
        "    esq <- hc$merge[m, 1]",
        "    dir <- hc$merge[m, 2]",
        "    x1 <- ifelse(esq < 0, pos_x[-esq], coord_x_nos[esq])",
        "    y1 <- ifelse(esq < 0, 0, alturas_nos[esq])",
        "    x2 <- ifelse(dir < 0, pos_x[-dir], coord_x_nos[dir])",
        "    y2 <- ifelse(dir < 0, 0, alturas_nos[dir])",
        "    ym <- hc$height[m]",
        "    alturas_nos[m] <- ym",
        "    coord_x_nos[m] <- (x1 + x2) / 2",
        "    seg_list[[m]] <- data.frame(",
        "      x = c(x1, x2, x1),",
        "      y = c(y1, y2, ym),",
        "      xend = c(x1, x2, x2),",
        "      yend = c(ym, ym, ym)",
        "    )",
        "  }",
        "",
        "  df_seg <- do.call(rbind, seg_list)",
        "  df_folhas <- data.frame(",
        "    x = seq_len(n_itens),",
        "    rotulo = hc$labels[hc$order],",
        "    cluster = factor(clusters_cut[hc$order])",
        "  )",
        "  cores_clust <- colorRampPalette(paleta_base)(nlevels(df_folhas$cluster))",
        "  y_max_dendro <- max(hc$height) * 1.15",
        "  y_offset_lbl <- max(hc$height) * 0.04",
        "",
        "  grafico_dendrograma_rca <- ggplot() +",
        f'    geom_segment(data = df_seg, aes(x = x, y = y, xend = xend, yend = yend), color = "{cor_txt}", linewidth = 0.75) +',
        "    geom_point(data = df_folhas, aes(x = x, y = 0, color = cluster), size = 3.2) +",
        *camada_rot_den,
        '    scale_color_manual(values = cores_clust, name = "Grupo") +',
        f"    scale_y_continuous(limits = c({limite_inf_den}, y_max_dendro)) +",
        f'    labs(title = titulo_dendro, x = {expr_x_den}, y = {expr_y_den})',
        "  grafico_dendrograma_rca <- aplicar_tema_easyr(grafico_dendrograma_rca, tem_legenda = TRUE, girar_eixo_x = FALSE, mostrar_eixo_x = FALSE)",
        "",
        "  print(grafico_dendrograma_rca)",
        '  salvar_grafico_easyr(grafico_dendrograma_rca, "Dendrograma")',
        "}",
    ]
    return "\n".join(linhas) + "\n"