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
def gerar_script_agrupamento(config: dict) -> str:
    caminho = config.get("caminho_arquivo", "")
    aba = config.get("aba", "")
    fatores = config.get("fatores", {})
    grupo = (
        fatores.get("grupo")
        or fatores.get("tratamento")
        or fatores.get("identificador")
        or ""
    )
    metodo_linkage = str(config.get("metodo_linkage", "ward.D2")).strip()
    if metodo_linkage not in ("ward.D2", "average", "complete", "single"):
        metodo_linkage = "ward.D2"

    respostas = config.get("respostas", [])
    cores = config.get("cores_graficos", [])
    cfg_graf = obter_config_grafico(config)

    if len(respostas) < 2:
        raise ValueError("Selecione pelo menos 2 variáveis numéricas para o agrupamento hierárquico.")

    pacotes = ["ggplot2"]
    if aba:
        pacotes.append("readxl")

    vetor_vars = ", ".join(f'"{v}"' for v in respostas)
    paleta_r = montar_paleta_r(cores)
    cor_txt = cfg_graf["cor_texto"]
    expr_x, expr_y = montar_rotulos_eixos_r(cfg_graf, "NULL", '"Distancia de Dissimilaridade"')

    camada_rotulos = (
        ['  geom_text(data = df_folhas, aes(x = x, y = -y_offset_lbl, label = rotulo, color = cluster), angle = 45, hjust = 1, fontface = "bold", size = 3.5, show.legend = FALSE) +']
        if cfg_graf["multi_rotulos"]
        else []
    )
    limite_inf_y = "-altura_max * 0.30" if cfg_graf["multi_rotulos"] else "-altura_max * 0.05"

    #========= 3. DEFINIÇÃO DA UNIDADE DE AGRUPAMENTO ==============
    if grupo:
        bloco_preparo = [
            f'col_grupo <- resolver_coluna_easyr(dados, "{grupo}")',
            "dados$Grupo_Cluster <- as.factor(trimws(as.character(dados[[col_grupo]])))",
            "dados_validos <- dados[complete.cases(dados[, variaveis_cols, drop = FALSE]) & !is.na(dados$Grupo_Cluster), , drop = FALSE]",
            "medias_grupo <- aggregate(dados_validos[, variaveis_cols, drop = FALSE], by = list(Unidade = dados_validos$Grupo_Cluster), FUN = mean, na.rm = TRUE)",
            "rownames(medias_grupo) <- as.character(medias_grupo$Unidade)",
            "matriz_bruta <- as.matrix(medias_grupo[, variaveis_cols, drop = FALSE])",
            "colnames(matriz_bruta) <- variaveis_req",
            'titulo_dendro <- paste("Agrupamento Hierarquico -", col_grupo)',
        ]
    else:
        bloco_preparo = [
            "dados_validos <- dados[complete.cases(dados[, variaveis_cols, drop = FALSE]), , drop = FALSE]",
            "matriz_bruta <- as.matrix(dados_validos[, variaveis_cols, drop = FALSE])",
            "colnames(matriz_bruta) <- variaveis_req",
            'rownames(matriz_bruta) <- paste0("Obs_", seq_len(nrow(matriz_bruta)))',
            'titulo_dendro <- "Agrupamento Hierarquico das Observacoes"',
        ]

    #========= 4. CABEÇALHO R E LIMPEZA DE VARIÁVEIS CONSTANTES ==============
    linhas = [
        *montar_cabecalho_pacotes(pacotes),
        "",
        *montar_leitura_dados(caminho, aba),
        *montar_helpers_grafico_r(config),
        "",
        *montar_bloco_salvar_grafico(config, "Agrupamento"),
        "",
        f"variaveis_req <- c({vetor_vars})",
        "variaveis_cols <- sapply(variaveis_req, function(v) resolver_coluna_easyr(dados, v))",
        f"paleta_base <- {paleta_r}",
        "",
        "for (col_y in variaveis_cols) {",
        '  dados[[col_y]] <- suppressWarnings(as.numeric(gsub(",", ".", as.character(dados[[col_y]]))))',
        "}",
        "",
        *bloco_preparo,
        'if (nrow(matriz_bruta) < 3) stop("Sao necessarios pelo menos 3 grupos ou observacoes distintas para formar um dendrograma.")',
        "",
        "sds <- apply(matriz_bruta, 2, sd, na.rm = TRUE)",
        "if (any(is.na(sds) | sds == 0)) {",
        "  vars_const <- colnames(matriz_bruta)[is.na(sds) | sds == 0]",
        '  warning(paste("Variaveis constantes removidas da padronizacao:", paste(vars_const, collapse = ", ")))',
        "  matriz_bruta <- matriz_bruta[, !(is.na(sds) | sds == 0), drop = FALSE]",
        "}",
        'if (ncol(matriz_bruta) < 1) stop("Nenhuma variavel com variacao suficiente para o agrupamento.")',
        "",

        #========= 5. MATRIZ DE DISTÂNCIA, HCLUST E CLUSTERS ==============
        "matriz_padronizada <- scale(matriz_bruta)",
        'dist_mat <- dist(matriz_padronizada, method = "euclidean")',
        f'hc <- hclust(dist_mat, method = "{metodo_linkage}")',
        "cor_cofen <- round(cor(dist_mat, cophenetic(hc)), 4)",
        "",
        "k_grupos <- min(3, nrow(matriz_padronizada) - 1)",
        "clusters_cut <- cutree(hc, k = k_grupos)",
        "tabela_agrupamento <- data.frame(",
        "  Unidade = names(clusters_cut),",
        "  Cluster = as.integer(clusters_cut),",
        "  row.names = NULL",
        ")",
        "",
        'cat("\\n==============================================\\n")',
        f'cat("AGRUPAMENTO HIERARQUICO | Ligacao: {metodo_linkage} | Distancia: Euclidiana\\n")',
        'cat("Correlacao Cofenetica (CCC):", cor_cofen, "\\n")',
        'cat("==============================================\\n")',
        'cat("\\nClassificacao por Clusters (k =", k_grupos, "grupos):\\n")',
        "print(tabela_agrupamento, row.names = FALSE)",
        "",

        #========= 6. CÁLCULO DAS COORDENADAS E DENDROGRAMA (GGPLOT2) ==============
        "n_itens <- length(hc$order)",
        "pos_x <- numeric(n_itens)",
        "pos_x[hc$order] <- seq_len(n_itens)",
        "alturas_nos <- numeric(nrow(hc$merge))",
        "coord_x_nos <- numeric(nrow(hc$merge))",
        "seg_list <- list()",
        "",
        "for (m in seq_len(nrow(hc$merge))) {",
        "  esq <- hc$merge[m, 1]",
        "  dir <- hc$merge[m, 2]",
        "  x1 <- ifelse(esq < 0, pos_x[-esq], coord_x_nos[esq])",
        "  y1 <- ifelse(esq < 0, 0, alturas_nos[esq])",
        "  x2 <- ifelse(dir < 0, pos_x[-dir], coord_x_nos[dir])",
        "  y2 <- ifelse(dir < 0, 0, alturas_nos[dir])",
        "  ym <- hc$height[m]",
        "  alturas_nos[m] <- ym",
        "  coord_x_nos[m] <- (x1 + x2) / 2",
        "  seg_list[[m]] <- data.frame(",
        "    x = c(x1, x2, x1),",
        "    y = c(y1, y2, ym),",
        "    xend = c(x1, x2, x2),",
        "    yend = c(ym, ym, ym)",
        "  )",
        "}",
        "",
        "df_seg <- do.call(rbind, seg_list)",
        "df_folhas <- data.frame(",
        "  x = seq_len(n_itens),",
        "  rotulo = hc$labels[hc$order],",
        "  cluster = factor(clusters_cut[hc$order])",
        ")",
        "cores_clust <- colorRampPalette(paleta_base)(nlevels(df_folhas$cluster))",
        "altura_max <- max(max(hc$height), 0.001)",
        "y_max_dendro <- altura_max * 1.15",
        "y_offset_lbl <- altura_max * 0.04",
        "",
        "grafico_dendrograma <- ggplot() +",
        f'  geom_segment(data = df_seg, aes(x = x, y = y, xend = xend, yend = yend), color = "{cor_txt}", linewidth = 0.75) +',
        "  geom_point(data = df_folhas, aes(x = x, y = 0, color = cluster), size = 3.2) +",
        *camada_rotulos,
        '  scale_color_manual(values = cores_clust, name = "Cluster") +',
        f"  scale_y_continuous(limits = c({limite_inf_y}, y_max_dendro)) +",
        "  labs(",
        "    title = titulo_dendro,",
        f'    subtitle = paste0("Metodo: {metodo_linkage} | Distancia Euclidiana | CCC = ", cor_cofen),',
        f"    x = {expr_x},",
        f"    y = {expr_y}",
        "  )",
        "grafico_dendrograma <- aplicar_tema_easyr(grafico_dendrograma, tem_legenda = TRUE, girar_eixo_x = FALSE, mostrar_eixo_x = FALSE)",
        "",
        "print(grafico_dendrograma)",
        'salvar_grafico_easyr(grafico_dendrograma, "Dendrograma")',
    ]
    return "\n".join(linhas) + "\n"