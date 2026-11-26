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
def gerar_script_boxplot(config: dict) -> str:
    caminho = config.get("caminho_arquivo", "")
    aba = config.get("aba", "")
    fatores = config.get("fatores", {})
    grupo = fatores.get("grupo", "")
    respostas = config.get("respostas", [])
    cores = config.get("cores_graficos", [])
    cfg_graf = obter_config_grafico(config)

    if not respostas:
        raise ValueError("Nenhuma variável resposta selecionada.")

    pacotes = ["ggplot2"]
    if aba:
        pacotes.append("readxl")

    vetor_vars = ", ".join(f'"{v}"' for v in respostas)
    paleta_r = montar_paleta_r(cores)
    cor_txt = cfg_graf["cor_texto"]
    mostrar_pontos = cfg_graf["mostrar_pontos"]
    outlier_cfg = "NA" if mostrar_pontos else "16"

    #========= 3. CABEÇALHO R E CONFIGURAÇÕES INICIAIS ==============
    linhas = [
        *montar_cabecalho_pacotes(pacotes),
        "",
        *montar_leitura_dados(caminho, aba),
        *montar_helpers_grafico_r(config),
        "",
        *montar_bloco_salvar_grafico(config, "Boxplot"),
        "",
        f"variaveis <- c({vetor_vars})",
        f"paleta_base <- {paleta_r}",
        "graficos_boxplot <- list()",
        "",
    ]

    #========= 4. GERAÇÃO DO BOXPLOT (COM OU SEM AGRUPAMENTO) ==============
    if grupo:
        expr_x, expr_y = montar_rotulos_eixos_r(cfg_graf, "col_grupo_alvo", "v")
        camada_jitter = (
            [f'    geom_jitter(width = 0.14, size = 2.1, alpha = 0.78, color = "{cor_txt}") +']
            if mostrar_pontos
            else []
        )
        subtitulo_box = (
            "Linha: mediana | Losango branco: media | Pontos: observacoes"
            if mostrar_pontos
            else "Linha: mediana | Losango branco: media | Pontos isolados: outliers"
        )

        linhas.extend([
            f'col_grupo_alvo <- resolver_coluna_easyr(dados, "{grupo}")',
            "",
            "for (v in variaveis) {",
            "  col_y <- resolver_coluna_easyr(dados, v)",
            '  y_num <- suppressWarnings(as.numeric(gsub(",", ".", as.character(dados[[col_y]]))))',
            "  g_chr <- trimws(as.character(dados[[col_grupo_alvo]]))",
            '  validos <- !is.na(y_num) & !is.na(g_chr) & g_chr != "" & tolower(g_chr) != "na"',
            "",
            "  subdados <- data.frame(",
            "    Grupo_Plot = factor(g_chr[validos], levels = unique(g_chr[validos])),",
            "    Valor_Y = y_num[validos],",
            "    stringsAsFactors = FALSE",
            "  )",
            "",
            "  if (nrow(subdados) == 0) {",
            '    warning(paste("Sem dados numericos validos para:", v))',
            "    next",
            "  }",
            "",
            "  cores_grupo <- colorRampPalette(paleta_base)(nlevels(subdados$Grupo_Plot))",
            "  p <- ggplot(subdados, aes(x = Grupo_Plot, y = Valor_Y, fill = Grupo_Plot)) +",
            f'    geom_boxplot(width = 0.55, alpha = 0.85, color = "{cor_txt}", outlier.shape = {outlier_cfg}, outlier.color = "{cor_txt}") +',
            *camada_jitter,
            f'    stat_summary(fun = mean, geom = "point", shape = 18, size = 3.6, color = "#FFFFFF") +',
            "    scale_fill_manual(values = cores_grupo) +",
            f'    labs(title = paste("Boxplot -", v), subtitle = "{subtitulo_box}", x = {expr_x}, y = {expr_y})',
            "  p <- aplicar_tema_easyr(p, tem_legenda = FALSE, girar_eixo_x = TRUE)",
            "",
            "  graficos_boxplot[[v]] <- p",
            "  print(p)",
            "  salvar_grafico_easyr(p, v)",
            "}",
        ])
    else:
        expr_x, expr_y = montar_rotulos_eixos_r(cfg_graf, '""', "v")
        camada_jitter = (
            [f'    geom_jitter(width = 0.10, size = 2.2, alpha = 0.78, color = "{cor_txt}") +']
            if mostrar_pontos
            else []
        )
        subtitulo_box = (
            "Linha: mediana | Losango branco: media | Pontos: observacoes"
            if mostrar_pontos
            else "Linha: mediana | Losango branco: media | Pontos isolados: outliers"
        )

        linhas.extend([
            "for (v in variaveis) {",
            "  col_y <- resolver_coluna_easyr(dados, v)",
            '  y_num <- suppressWarnings(as.numeric(gsub(",", ".", as.character(dados[[col_y]]))))',
            "  y_valid <- y_num[!is.na(y_num)]",
            "  if (length(y_valid) == 0) next",
            "",
            "  subdados <- data.frame(Eixo_X = factor(v), Valor_Y = y_valid)",
            "  p <- ggplot(subdados, aes(x = Eixo_X, y = Valor_Y)) +",
            f'    geom_boxplot(width = 0.42, fill = paleta_base[1], alpha = 0.85, color = "{cor_txt}", outlier.shape = {outlier_cfg}, outlier.color = "{cor_txt}") +',
            *camada_jitter,
            f'    stat_summary(fun = mean, geom = "point", shape = 18, size = 3.6, color = "#FFFFFF") +',
            f'    labs(title = paste("Boxplot -", v), subtitle = "{subtitulo_box}", x = {expr_x}, y = {expr_y})',
            "  p <- aplicar_tema_easyr(p, tem_legenda = FALSE, girar_eixo_x = TRUE)",
            "",
            "  graficos_boxplot[[v]] <- p",
            "  print(p)",
            "  salvar_grafico_easyr(p, v)",
            "}",
        ])

    return "\n".join(linhas) + "\n"