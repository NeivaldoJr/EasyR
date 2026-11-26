#========= 1. IMPORTAÇÃO DOS GERADORES ==============
from RSTS.agrupamento import gerar_script_agrupamento
from RSTS.boxplot import gerar_script_boxplot
from RSTS.correlacao import gerar_script_correlacao
from RSTS.dbc import gerar_script_dbc
from RSTS.descritiva import gerar_script_descritiva
from RSTS.dic import gerar_script_dic
from RSTS.dunnett import gerar_script_dunnett
from RSTS.fatorial import gerar_script_fatorial
from RSTS.pca import gerar_script_pca
from RSTS.regressao import gerar_script_regressao
from RSTS.scheffe import gerar_script_scheffe
from RSTS.scott_knott import gerar_script_scott_knott
from RSTS.subdividida import gerar_script_subdividida
from RSTS.tukey import gerar_script_tukey


#========= 2. DICIONÁRIO ROTEADOR DE ANÁLISES ==============
GERADORES = {
    "DIC": gerar_script_dic,
    "DBC": gerar_script_dbc,
    "FATORIAL": gerar_script_fatorial,
    "SUBDIVIDIDA": gerar_script_subdividida,
    "REGRESSAO": gerar_script_regressao,
    "PCA": gerar_script_pca,
    "CORRELACAO": gerar_script_correlacao,
    "AGRUPAMENTO": gerar_script_agrupamento,
    "TUKEY": gerar_script_tukey,
    "SCOTT_KNOTT": gerar_script_scott_knott,
    "DUNNETT": gerar_script_dunnett,
    "SCHEFFE": gerar_script_scheffe,
    "DESCRITIVA": gerar_script_descritiva,
    "BOXPLOT": gerar_script_boxplot,
}


#========= 3. FUNÇÃO PRINCIPAL DE DISPARO ==============
def gerar_script_r(config: dict) -> str:
    analise_id = config.get("analise_id", "")
    gerador = GERADORES.get(analise_id)
    if gerador is None:
        raise ValueError(f"Gerador não encontrado para a análise: {analise_id}")
    return gerador(config)