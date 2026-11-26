CATALOGO_ANALISES = [
    #========= 1. DELINEAMENTOS EXPERIMENTAIS BÁSICOS (DIC E DBC) ==============
    {
        "id": "DIC",
        "tag": "DIC",
        "nome": "Delineamento Inteiramente Casualizado",
        "descricao": "ANOVA, pressupostos e teste de Tukey para experimentos sem blocos.",
        "ajuda": "Ideal para experimentos conduzidos em condições homogêneas (como casa de vegetação ou laboratório), onde os tratamentos são sorteados totalmente ao acaso sem necessidade de blocos.",
        "usa_pvalor": True,
        "usa_grafico": True,
        "min_respostas": 1,
        "campos": [
            {
                "chave": "tratamento",
                "rotulo": "Coluna de Tratamento *",
                "obrigatorio": True,
                "ajuda": "Selecione a coluna da planilha que contém os nomes ou códigos dos tratamentos avaliados.",
            },
        ],
    },
    {
        "id": "DBC",
        "tag": "DBC",
        "nome": "Delineamento em Blocos ao Acaso",
        "descricao": "ANOVA, pressupostos e teste de Tukey com controle local por blocos.",
        "ajuda": "Indicado quando existe alguma fonte de variação conhecida na área experimental (declividade, luminosidade, bancadas ou épocas), isolando esse efeito em blocos.",
        "usa_pvalor": True,
        "usa_grafico": True,
        "min_respostas": 1,
        "campos": [
            {
                "chave": "tratamento",
                "rotulo": "Coluna de Tratamento *",
                "obrigatorio": True,
                "ajuda": "Selecione a coluna que identifica os tratamentos aplicados dentro de cada bloco.",
            },
            {
                "chave": "bloco",
                "rotulo": "Coluna de Bloco *",
                "obrigatorio": True,
                "ajuda": "Selecione a coluna que identifica as repetições/blocos do experimento.",
            },
        ],
    },

    #========= 2. DELINEAMENTOS FATORIAIS E PARCELAS SUBDIVIDIDAS ==============
    {
        "id": "FATORIAL",
        "tag": "FATORIAL",
        "nome": "Esquema Fatorial (Duplo / Triplo)",
        "descricao": "Avalia efeitos principais e interações entre dois ou três fatores (DIC ou DBC).",
        "ajuda": "Use quando você combina dois ou três fatores simultaneamente (ex.: doses de adubo × cultivares) e quer saber se há interação significativa entre eles.",
        "usa_pvalor": True,
        "usa_grafico": True,
        "min_respostas": 1,
        "opcoes_modelo": [
            {
                "chave": "delineamento_base",
                "rotulo": "Delineamento Base",
                "padrao": "DIC",
                "ajuda": "Escolha DIC se o sorteio foi inteiramente ao acaso, ou DBC se houve controle local por blocos.",
                "opcoes": [
                    {"valor": "DIC", "texto": "Inteiramente Casualizado (DIC)"},
                    {"valor": "DBC", "texto": "Blocos ao Acaso (DBC)"},
                ],
            }
        ],
        "campos": [
            {
                "chave": "fator_a",
                "rotulo": "Fator A *",
                "obrigatorio": True,
                "ajuda": "Primeiro fator experimental (ex.: fontes de corretivo ou cultivares).",
            },
            {
                "chave": "fator_b",
                "rotulo": "Fator B *",
                "obrigatorio": True,
                "ajuda": "Segundo fator experimental combinado com o Fator A (ex.: doses ou épocas).",
            },
            {
                "chave": "fator_c",
                "rotulo": "Fator C (Opcional — Fatorial Triplo)",
                "obrigatorio": False,
                "ajuda": "Preencha apenas se o experimento tiver um terceiro fator cruzado (A × B × C).",
            },
            {
                "chave": "bloco",
                "rotulo": "Coluna de Bloco *",
                "obrigatorio": True,
                "depende_de": {"delineamento_base": "DBC"},
                "ajuda": "Coluna que identifica os blocos do delineamento DBC.",
            },
        ],
    },
    {
        "id": "SUBDIVIDIDA",
        "tag": "SUBPARCELA",
        "nome": "Parcelas Subdivididas",
        "descricao": "Fator primário na parcela e secundário (ex.: tempo ou época) na subparcela.",
        "ajuda": "Indicado quando um fator exige unidades experimentais maiores ou é fixo no espaço (parcela) e outro fator é avaliado dentro dela (subparcela, como tempos de coleta).",
        "usa_pvalor": True,
        "usa_grafico": True,
        "min_respostas": 1,
        "campos": [
            {
                "chave": "parcela",
                "rotulo": "Parcela (Tratamento Principal) *",
                "obrigatorio": True,
                "ajuda": "Fator aplicado na parcela inteira (ex.: manejo de solo ou sistema de irrigação).",
            },
            {
                "chave": "subparcela",
                "rotulo": "Subparcela (Tempo / Época / Fator B) *",
                "obrigatorio": True,
                "ajuda": "Fator secundário subdividido dentro de cada parcela (ex.: dias após a semeadura).",
            },
            {
                "chave": "bloco",
                "rotulo": "Coluna de Bloco *",
                "obrigatorio": True,
                "ajuda": "Coluna que identifica os blocos experimentais.",
            },
        ],
    },

    #========= 3. ANÁLISE QUANTITATIVA (REGRESSÃO) ==============
    {
        "id": "REGRESSAO",
        "tag": "REGRESSÃO",
        "nome": "Regressão Polinomial (Doses)",
        "descricao": "Ajuste de curvas lineares, quadráticas e cúbicas para fatores quantitativos.",
        "ajuda": "Use quando os tratamentos são níveis numéricos crescentes (doses, concentrações, temperaturas ou tempos) para ajustar uma equação e estimar pontos de máximo ou mínimo.",
        "usa_pvalor": True,
        "usa_grafico": True,
        "min_respostas": 1,
        "opcoes_modelo": [
            {
                "chave": "delineamento_base",
                "rotulo": "Delineamento Base",
                "padrao": "DIC",
                "ajuda": "Define se os resíduos da ANOVA da regressão serão calculados em DIC ou DBC.",
                "opcoes": [
                    {"valor": "DIC", "texto": "Inteiramente Casualizado (DIC)"},
                    {"valor": "DBC", "texto": "Blocos ao Acaso (DBC)"},
                ],
            },
            {
                "chave": "grau_forcar",
                "rotulo": "Grau do Polinômio",
                "padrao": "AUTO",
                "ajuda": "No modo Automático, o R testa até o 3º grau e escolhe a curva de maior grau significativo.",
                "opcoes": [
                    {"valor": "AUTO", "texto": "Automático (até 3º grau, pela significância)"},
                    {"valor": "1", "texto": "Linear (1º grau)"},
                    {"valor": "2", "texto": "Quadrático (2º grau)"},
                    {"valor": "3", "texto": "Cúbico (3º grau)"},
                ],
            },
        ],
        "campos": [
            {
                "chave": "dose",
                "rotulo": "Fator Quantitativo (Doses) *",
                "obrigatorio": True,
                "ajuda": "Coluna numérica contendo os valores das doses ou níveis quantitativos avaliados.",
            },
            {
                "chave": "bloco",
                "rotulo": "Coluna de Bloco *",
                "obrigatorio": True,
                "depende_de": {"delineamento_base": "DBC"},
                "ajuda": "Coluna que identifica os blocos do experimento.",
            },
            {
                "chave": "agrupador",
                "rotulo": "Fator Qualitativo / Grupo (Opcional — múltiplas curvas)",
                "obrigatorio": False,
                "ajuda": "Opcional: selecione uma coluna categórica para traçar uma curva de regressão separada para cada grupo.",
            },
        ],
    },

    #========= 4. TESTES DE COMPARAÇÃO DE MÉDIAS (PÓS-HOC E CONTROLE) ==============
    {
        "id": "TUKEY",
        "tag": "PÓS-HOC",
        "nome": "Teste de Tukey (HSD)",
        "descricao": "Comparação múltipla par a par entre médias de tratamentos (DIC ou DBC).",
        "ajuda": "A análise de Tukey se ajusta melhor quando há necessidade de comparar todos os tratamentos entre si e verificar se existe diferença estatística aceitável entre cada par.",
        "usa_pvalor": True,
        "usa_grafico": True,
        "min_respostas": 1,
        "campos": [
            {
                "chave": "tratamento",
                "rotulo": "Coluna de Tratamento *",
                "obrigatorio": True,
                "ajuda": "Selecione a coluna que contém os tratamentos a serem comparados.",
            },
            {
                "chave": "bloco",
                "rotulo": "Coluna de Bloco (Opcional — para DBC)",
                "obrigatorio": False,
                "ajuda": "Preencha apenas se o experimento tiver blocos (DBC). Deixe vazio para analisar como DIC.",
            },
        ],
    },
    {
        "id": "SCOTT_KNOTT",
        "tag": "PÓS-HOC",
        "nome": "Agrupamento de Scott-Knott",
        "descricao": "Agrupamento hierárquico de médias sem ambiguidade de letras (DIC ou DBC).",
        "ajuda": "Separa os tratamentos em grupos distintos sem sobreposição de letras (ex.: 'a', 'b', 'c' puros), muito útil quando há grande número de tratamentos.",
        "usa_pvalor": True,
        "usa_grafico": True,
        "min_respostas": 1,
        "campos": [
            {
                "chave": "tratamento",
                "rotulo": "Coluna de Tratamento *",
                "obrigatorio": True,
                "ajuda": "Selecione a coluna que identifica os tratamentos.",
            },
            {
                "chave": "bloco",
                "rotulo": "Coluna de Bloco (Opcional — para DBC)",
                "obrigatorio": False,
                "ajuda": "Preencha apenas se o experimento foi conduzido em blocos (DBC).",
            },
        ],
    },
    {
        "id": "DUNNETT",
        "tag": "CONTROLE",
        "nome": "Teste de Dunnett (vs. Controle)",
        "descricao": "Compara cada tratamento diretamente contra a testemunha/controle (DIC ou DBC).",
        "ajuda": "Mais sensível que o Tukey quando o único objetivo é saber quais tratamentos diferem da testemunha (controle), sem comparar os demais tratamentos entre si.",
        "usa_pvalor": True,
        "usa_grafico": True,
        "min_respostas": 1,
        "campos": [
            {
                "chave": "tratamento",
                "rotulo": "Coluna de Tratamento *",
                "obrigatorio": True,
                "ajuda": "Selecione a coluna de tratamentos; em seguida, escolha qual nível é o controle.",
            },
            {
                "chave": "bloco",
                "rotulo": "Coluna de Bloco (Opcional — para DBC)",
                "obrigatorio": False,
                "ajuda": "Preencha apenas se houver blocos no delineamento experimental.",
            },
        ],
    },
    {
        "id": "SCHEFFE",
        "tag": "PÓS-HOC",
        "nome": "Teste de Scheffé",
        "descricao": "Comparação múltipla conservadora para médias e contrastes (DIC ou DBC).",
        "ajuda": "Teste rigoroso e conservador que controla o erro global em qualquer comparação ou contraste entre grupos de médias, mesmo com repetições desiguais.",
        "usa_pvalor": True,
        "usa_grafico": True,
        "min_respostas": 1,
        "campos": [
            {
                "chave": "tratamento",
                "rotulo": "Coluna de Tratamento *",
                "obrigatorio": True,
                "ajuda": "Selecione a coluna que identifica os tratamentos.",
            },
            {
                "chave": "bloco",
                "rotulo": "Coluna de Bloco (Opcional — para DBC)",
                "obrigatorio": False,
                "ajuda": "Preencha apenas se o experimento tiver blocos (DBC).",
            },
        ],
    },

    #========= 5. ANÁLISES MULTIVARIADAS E BIVARIADAS ==============
    {
        "id": "PCA",
        "tag": "MULTIVARIADA",
        "nome": "Componentes Principais (PCA)",
        "descricao": "Autovalores, variância explicada e biplot multivariado (sem teste de hipóteses).",
        "ajuda": "Condensa várias variáveis simultaneamente em eixos principais (CP1 e CP2), mostrando no biplot como tratamentos e variáveis se associam.",
        "usa_pvalor": False,
        "usa_grafico": True,
        "min_respostas": 2,
        "campos": [
            {
                "chave": "grupo",
                "rotulo": "Coluna de Agrupamento / Tratamento (Opcional)",
                "obrigatorio": False,
                "ajuda": "Opcional: colore os pontos e desenha elipses de confiança por tratamento ou grupo no biplot.",
            },
        ],
    },
    {
        "id": "CORRELACAO",
        "tag": "BIVARIADA",
        "nome": "Correlação Linear (Pearson / Spearman)",
        "descricao": "Matriz de correlação, p-valores par a par e correlograma visual.",
        "ajuda": "Mede a força e a direção (positiva ou negativa, de -1 a +1) da associação entre pares de variáveis numéricas.",
        "usa_pvalor": True,
        "usa_grafico": True,
        "min_respostas": 2,
        "opcoes_modelo": [
            {
                "chave": "metodo_correlacao",
                "rotulo": "Coeficiente de Correlação",
                "padrao": "pearson",
                "ajuda": "Use Pearson para relações lineares com distribuição normal, ou Spearman para dados não normais ou baseados em postos.",
                "opcoes": [
                    {"valor": "pearson", "texto": "Correlação Linear de Pearson (r)"},
                    {"valor": "spearman", "texto": "Correlação de Postos de Spearman (ρ)"},
                ],
            }
        ],
        "campos": [],
    },
    {
        "id": "AGRUPAMENTO",
        "tag": "MULTIVARIADA",
        "nome": "Agrupamento Hierárquico (Cluster)",
        "descricao": "Distância euclidiana padronizada, correlação cofenética e dendrograma (sem α).",
        "ajuda": "Agrupa amostras ou tratamentos por similaridade multivariada, gerando um dendrograma (árvore) e calculando a correlação cofenética.",
        "usa_pvalor": False,
        "usa_grafico": True,
        "min_respostas": 2,
        "opcoes_modelo": [
            {
                "chave": "metodo_linkage",
                "rotulo": "Método de Ligação",
                "padrao": "ward.D2",
                "ajuda": "Ward forma grupos mais compactos e homogêneos; UPGMA (average) usa a distância média entre grupos.",
                "opcoes": [
                    {"valor": "ward.D2", "texto": "Ward (ward.D2)"},
                    {"valor": "average", "texto": "Ligação Média (UPGMA / average)"},
                    {"valor": "complete", "texto": "Ligação Completa (Vizinho mais distante)"},
                ],
            }
        ],
        "campos": [
            {
                "chave": "grupo",
                "rotulo": "Coluna de Agrupamento / Tratamento (Opcional)",
                "obrigatorio": False,
                "ajuda": "Opcional: identifica cada ramo do dendrograma pelo nome do tratamento ou amostra.",
            },
        ],
    },

    #========= 6. ANÁLISE EXPLORATÓRIA E VISUALIZAÇÃO ==============
    {
        "id": "DESCRITIVA",
        "tag": "EXPLORATÓRIA",
        "nome": "Estatística Descritiva",
        "descricao": "Tabela com n, média, desvio padrão, erro padrão, mediana, mín, máx e CV% (sem α).",
        "ajuda": "Gera um resumo numérico completo dos seus dados (média, dispersão, extremos e coeficiente de variação) antes de partir para testes de hipóteses.",
        "usa_pvalor": False,
        "usa_grafico": False,
        "min_respostas": 1,
        "campos": [
            {
                "chave": "grupo",
                "rotulo": "Coluna de Agrupamento / Tratamento (Opcional)",
                "obrigatorio": False,
                "ajuda": "Se selecionada, calcula as estatísticas descritivas separadamente para cada tratamento.",
            },
        ],
    },
    {
        "id": "BOXPLOT",
        "tag": "GRÁFICO",
        "nome": "Gráfico Boxplot (Dispersão)",
        "descricao": "Distribuição por quartis, mediana, média e observações individuais (sem α).",
        "ajuda": "Excelente para visualizar a distribuição dos dados, identificar valores discrepantes (outliers) e comparar a variação entre tratamentos.",
        "usa_pvalor": False,
        "usa_grafico": True,
        "min_respostas": 1,
        "campos": [
            {
                "chave": "grupo",
                "rotulo": "Coluna de Agrupamento / Tratamento (Opcional)",
                "obrigatorio": False,
                "ajuda": "Define os grupos do eixo X para comparar a distribuição lado a lado.",
            },
        ],
    },
]