#========= 1. IMPORTAÇÕES (FERRAMENTAS) ==============
import os
from dataclasses import dataclass, field
import pandas as pd


#========= 2. ESTRUTURA DE DADOS DA CLASSE (ATRIBUTOS) ==============
@dataclass
class LeitorPlanilha:
    caminho_arquivo: str = ""
    nome_arquivo: str = ""
    extensao: str = ""
    abas_disponiveis: list[str] = field(default_factory=list)
    aba_selecionada: str = ""
    df: pd.DataFrame | None = None

    #========= 3. ABERTURA E HIGIENIZAÇÃO DA PLANILHA ==============
    #--- 3.1 Carregamento Inicial ---
    def carregar_arquivo(self, caminho: str) -> None:
        self.caminho_arquivo = caminho
        self.nome_arquivo = os.path.basename(caminho)
        self.extensao = os.path.splitext(caminho)[1].lower()
        self.abas_disponiveis = []
        self.aba_selecionada = ""

        if self.extensao in (".xlsx", ".xls"):
            with pd.ExcelFile(caminho) as excel:
                self.abas_disponiveis = list(excel.sheet_names)
            if self.abas_disponiveis:
                self.carregar_aba(self.abas_disponiveis[0])
        elif self.extensao == ".csv":
            with open(caminho, "r", encoding="utf-8-sig", errors="replace") as f:
                primeira_linha = f.readline()
            sep = ";" if ";" in primeira_linha else ","
            dec = "," if sep == ";" else "."
            self.df = pd.read_csv(caminho, sep=sep, dec=dec)
            self._higienizar_dataframe()
        else:
            raise ValueError(f"Formato não suportado: {self.extensao}")

    #--- 3.2 Troca de Aba ---
    def carregar_aba(self, nome_aba: str) -> None:
        self.aba_selecionada = nome_aba
        self.df = pd.read_excel(self.caminho_arquivo, sheet_name=nome_aba)
        self._higienizar_dataframe()

    #--- 3.3 Limpeza Interna ---
    def _higienizar_dataframe(self) -> None:
        if self.df is not None:
            self.df = self.df.dropna(how="all").reset_index(drop=True)
            self.df.columns = [str(col).strip() for col in self.df.columns]

    #========= 4. DIAGNÓSTICO E EXPORTAÇÃO PARA A INTERFACE ==============
    #--- 4.1 Filtro de Colunas Numéricas ---
    def colunas_numericas(self) -> list[str]:
        if self.df is None:
            return []
        return list(self.df.select_dtypes(include=["number"]).columns)

    #--- 4.2 Empacotamento do Raio-X ---
    def exportar_para_interface(self) -> dict:
        if self.df is None:
            return {"ok": False}

        numericas = set(self.colunas_numericas())
        colunas_info = []

        for col in self.df.columns:
            serie = self.df[col]
            is_num = col in numericas
            nulos = int(serie.isna().sum())
            nao_nulos = serie.dropna()
            alerta_texto = False

            if not is_num and len(nao_nulos) > 0:
                conv = pd.to_numeric(
                    nao_nulos.astype(str).str.strip().str.replace(",", ".", regex=False),
                    errors="coerce",
                )
                validos = int(conv.notna().sum())
                if validos > 0 and validos >= len(nao_nulos) * 0.5:
                    alerta_texto = True

            valores_limpos = [
                v.strip()
                for v in nao_nulos.astype(str).tolist()
                if v.strip() != "" and v.strip().lower() != "nan"
            ]
            unicos = list(dict.fromkeys(valores_limpos))

            colunas_info.append({
                "nome": col,
                "numerica": is_num,
                "nulos": nulos,
                "alerta_texto": alerta_texto,
                "n_unicos": len(unicos),
                "valores_unicos": unicos,
            })

        amostra = self.df.fillna("NA")
        todas_linhas = amostra.astype(str).values.tolist()

        return {
            "ok": True,
            "nome_arquivo": self.nome_arquivo,
            "caminho_arquivo": self.caminho_arquivo,
            "abas": self.abas_disponiveis,
            "aba_atual": self.aba_selecionada,
            "total_linhas": int(self.df.shape[0]),
            "total_colunas": int(self.df.shape[1]),
            "colunas": colunas_info,
            "cabecalhos": list(self.df.columns),
            "linhas": todas_linhas,
        }