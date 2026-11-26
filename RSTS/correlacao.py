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
def gerar_script_correlacao(config: dict) -> str:
    caminho = config.get("caminho_arquivo", "")
    aba = config.get("aba", "")
    metodo_cor = str(config.get("metodo_correlacao", "pearson")).lower().strip()
    if metodo_cor not in ("pearson", "spearman"):
        metodo_cor = "pearson"
    nome_metodo = "Pearson" if metodo_cor == "pearson" else "Spearman"

    respostas = config.get("respostas", [])
    alfa = config.get("alfa", 0.05)
    cores = config.get("cores_graficos", [])
    cfg_graf = obter_config_grafico(config)

    if len(respostas) < 2:
        raise ValueError("Selecione pelo menos 2 variáveis numéricas para a análise de correlação.")

    pacotes = ["ggplot2"]
    if aba:
        pacotes.append("readxl")

    vetor_vars = ", ".join(f'"{v}"' for v in respostas)
    paleta_r = montar_paleta_r(cores)
    cor_txt = cfg_graf["cor_texto"]
    expr_x, expr_y = montar_rotulos_eixos_r(cfg_graf, "NULL", "NULL")

    camada_rotulos = (
        [f'  geom_text(aes(label = rotulo), fontface = "bold", size = 3.8, color = "{cor_txt}") +']
        if cfg_graf["multi_rotulos"]
        else []
    )

    #========= 3. CABEÇALHO R E FILTRAGEM DE VARIÁVEIS CONSTANTES ==============
    linhas = [
        *montar_cabecalho_pacotes(pacotes),
        "",
        *montar_leitura_dados(caminho, aba),
        *montar_helpers_grafico_r(config),
        "",
        *montar_bloco_salvar_grafico(config, "Correlacao"),
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
        "dados_validos <- dados[complete.cases(dados[, variaveis_cols, drop = FALSE]), , drop = FALSE]",
        'if (nrow(dados_validos) < 3) stop("Sao necessarias pelo menos 3 observacoes completas para calcular correlacoes.")',
        "",
        "mat_num <- as.matrix(dados_validos[, variaveis_cols, drop = FALSE])",
        "colnames(mat_num) <- variaveis_req",
        "",
        "sds <- apply(mat_num, 2, sd, na.rm = TRUE)",
        "if (any(is.na(sds) | sds == 0)) {",
        "  vars_const <- variaveis_req[is.na(sds) | sds == 0]",
        '  warning(paste("Variaveis constantes removidas da correlacao:", paste(vars_const, collapse = ", ")))',
        "  keep <- !(is.na(sds) | sds == 0)",
        "  mat_num <- mat_num[, keep, drop = FALSE]",
        "  variaveis_req <- variaveis_req[keep]",
        "}",
        'if (ncol(mat_num) < 2) stop("Restaram menos de 2 variaveis com variacao para correlacionar.")',
        "",

        #========= 4. CÁLCULO DAS MATRIZES (r / ρ) E P-VALORES ==============
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
        "        Coeficiente = round(unname(teste_c$estimate), 4),",
        "        p_valor = round(teste_c$p.value, 6),",
        "        Significancia = sig_txt,",
        "        row.names = NULL",
        "      )",
        "      idx_par <- idx_par + 1",
        "    }",
        "  }",
        "}",
        "",
        "matriz_correlacao <- round(mat_cor, 4)",
        "matriz_pvalor <- round(mat_p, 6)",
        "tabela_pares_correlacao <- do.call(rbind, pares_cor)",
        "",
        'cat("\\n==============================================\\n")',
        f'cat("CORRELACAO DE {nome_metodo.upper()} | n =", nrow(mat_num), "| alfa =", alfa, "\\n")',
        'cat("==============================================\\n")',
        f'cat("\\nMatriz de Correlacao ({nome_metodo}):\\n")',
        "print(matriz_correlacao)",
        'cat("\\nMatriz de p-valores:\\n")',
        "print(matriz_pvalor)",
        'cat("\\nPares de Correlacao e Significancia:\\n")',
        "print(tabela_pares_correlacao, row.names = FALSE)",
        "",

        #========= 5. CORRELOGRAMA VISUAL PERSONALIZADO (GGPLOT2) ==============
        "grid_cor <- expand.grid(",
        "  Var1 = factor(variaveis_req, levels = variaveis_req),",
        "  Var2 = factor(variaveis_req, levels = rev(variaveis_req))",
        ")",
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
        "grafico_correlacao <- ggplot(grid_cor, aes(x = Var1, y = Var2, fill = r)) +",
        '  geom_tile(color = "#FFFFFF", linewidth = 0.8) +',
        *camada_rotulos,
        '  scale_fill_gradient2(low = cor_baixa, mid = "#F7F3EB", high = cor_alta, midpoint = 0, limits = c(-1, 1), name = "Coef.") +',
        f'  labs(title = "Correlograma de {nome_metodo} (* p <= {alfa})", x = {expr_x}, y = {expr_y})',
        "grafico_correlacao <- aplicar_tema_easyr(grafico_correlacao, tem_legenda = TRUE, girar_eixo_x = TRUE) +",
        '  theme(axis.text.x = element_text(face = "bold"), axis.text.y = element_text(face = "bold"))',
        "",
        "print(grafico_correlacao)",
        'salvar_grafico_easyr(grafico_correlacao, "Matriz")',
    ]
    return "\n".join(linhas) + "\n"