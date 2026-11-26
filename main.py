#========= 1. IMPORTAÇÕES (FERRAMENTAS) ==============
import base64
import csv
import os
import re
import tempfile
from pathlib import Path
import pandas as pd
import webview
import sys
RAIZ_PROJETO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ_PROJETO not in sys.path:
    sys.path.insert(0, RAIZ_PROJETO)

from GUI.catalogo_analises import CATALOGO_ANALISES
from RSTS import gerar_script_r


#========= 2. CONSTANTES DE CAMINHO ==============
BASE_DIR = Path(__file__).resolve().parent
HTML_PATH = BASE_DIR / "GUI" / "interface.html"


#========= 3. FUNÇÕES AUXILIARES DE DADOS ==============
def _ordenar_natural(texto: str):
    partes = re.split(r"(\d+(?:[.,]\d+)?)", texto)
    chave = []
    for p in partes:
        if not p:
            continue
        num_str = p.replace(",", ".")
        try:
            chave.append((0, float(num_str)))
        except ValueError:
            chave.append((1, p.lower()))
    return chave


def _eh_numero(valor: str) -> bool:
    limpo = valor.strip().replace(",", ".")
    if not limpo or limpo.lower() in {"na", "nan", "null", "none", "-"}:
        return False
    try:
        float(limpo)
        return True
    except ValueError:
        return False


def _ler_csv_inteligente(caminho: str) -> pd.DataFrame:
    encodings = ["utf-8-sig", "utf-8", "latin1", "cp1252"]
    for enc in encodings:
        try:
            with open(caminho, "r", encoding=enc, newline="") as f:
                amostra = f.read(4096)
            dialeto = csv.Sniffer().sniff(amostra, delimiters=";\t,")
            sep = dialeto.delimiter
            return pd.read_csv(caminho, sep=sep, encoding=enc, dtype=str, keep_default_na=False)
        except Exception:
            continue
    return pd.read_csv(caminho, sep=None, engine="python", encoding="latin1", dtype=str, keep_default_na=False)


#========= 4. PONTE DE COMUNICAÇÃO (CLASSE API) ==============
class Api:
    #--- 4.1 Memória da Ponte ---
    def __init__(self):
        self._janela = None
        self._caminho_atual = ""
        self._abas_atuais = []

    #--- 4.2 Catálogo ---
    def obter_catalogo(self):
        return CATALOGO_ANALISES

    #--- 4.3 Abertura e Troca de Abas ---
    def selecionar_arquivo(self):
        if not self._janela:
            return {"ok": False, "erro": "Janela principal ainda não inicializada."}

        try:
            if hasattr(webview, "FileDialog"):
                dialog_open = webview.FileDialog.OPEN
            else:
                dialog_open = getattr(webview, "OPEN_DIALOG", 10)

            caminhos = self._janela.create_file_dialog(
                dialog_open,
                allow_multiple=False,
                file_types=("Planilhas (*.xlsx;*.xls;*.csv)", "Todos os arquivos (*.*)"),
            )
            if not caminhos:
                return {"ok": False}

            if isinstance(caminhos, str):
                caminho = caminhos
            else:
                lista = list(caminhos)
                if not lista:
                    return {"ok": False}
                caminho = str(lista[0])

            return self._carregar_planilha(caminho)
        except Exception as exc:
            return {"ok": False, "erro": f"Falha ao abrir seletor de arquivos: {exc}"}

    def carregar_planilha_base64(self, nome_arquivo: str, conteudo_b64: str):
        try:
            if "," in conteudo_b64:
                conteudo_b64 = conteudo_b64.split(",", 1)[1]
            dados_bytes = base64.b64decode(conteudo_b64)
            pasta_temp = Path(tempfile.gettempdir()) / "EasyR_uploads"
            pasta_temp.mkdir(parents=True, exist_ok=True)
            destino = pasta_temp / os.path.basename(nome_arquivo)
            destino.write_bytes(dados_bytes)
            return self._carregar_planilha(str(destino))
        except Exception as exc:
            return {"ok": False, "erro": f"Falha ao importar planilha: {exc}"}

    def trocar_aba(self, nome_aba: str):
        if not self._caminho_atual:
            return {"ok": False, "erro": "Nenhuma planilha carregada."}
        return self._carregar_planilha(self._caminho_atual, aba=nome_aba)

    #--- 4.4 Motor de Leitura e Raio-X ---
    def _carregar_planilha(self, caminho: str, aba: str = ""):
        try:
            ext = os.path.splitext(caminho)[1].lower()
            abas = []
            aba_atual = ""

            if ext in {".xlsx", ".xls"}:
                with pd.ExcelFile(caminho) as excel:
                    abas = [str(s) for s in excel.sheet_names]
                    aba_atual = aba if aba in abas else (abas[0] if abas else "")
                    df = pd.read_excel(excel, sheet_name=aba_atual, dtype=str, keep_default_na=False)
            elif ext == ".csv":
                df = _ler_csv_inteligente(caminho)
            else:
                return {"ok": False, "erro": f"Formato não suportado: {ext}"}

            df = df.fillna("")
            df.columns = [str(c).strip() for c in df.columns]
            colunas_validas = [c for c in df.columns if c and not c.startswith("Unnamed:")]
            df = df.loc[:, colunas_validas]

            for col in df.columns:
                df[col] = df[col].apply(
                    lambda x: "" if x is None or str(x).strip().lower() in {"nan", "none"} else str(x).strip()
                )

            self._caminho_atual = str(caminho)
            self._abas_atuais = abas

            cabecalhos = [str(c) for c in df.columns]
            colunas_info = []

            for col in cabecalhos:
                valores_brutos = df[col].tolist()
                nulos = sum(1 for v in valores_brutos if v == "" or v.lower() in {"na", "null"})
                validos = [v for v in valores_brutos if v != "" and v.lower() not in {"na", "null"}]
                qtd_num = sum(1 for v in validos if _eh_numero(v))
                numerica = bool(len(validos) > 0 and qtd_num == len(validos))
                alerta_texto = bool(not numerica and qtd_num > 0)
                unicos = sorted(set(validos), key=_ordenar_natural)

                colunas_info.append(
                    {
                        "nome": col,
                        "numerica": numerica,
                        "alerta_texto": alerta_texto,
                        "nulos": int(nulos),
                        "n_unicos": int(len(unicos)),
                        "valores_unicos": [str(u) for u in unicos],
                    }
                )

            preview_linhas = [
                [str(cel) if cel is not None else "" for cel in row]
                for row in df.head(100).itertuples(index=False, name=None)
            ]

            return {
                "ok": True,
                "caminho_arquivo": str(caminho),
                "nome_arquivo": os.path.basename(str(caminho)),
                "abas": abas,
                "aba_atual": str(aba_atual),
                "total_linhas": int(len(df)),
                "total_colunas": int(len(cabecalhos)),
                "cabecalhos": cabecalhos,
                "colunas": colunas_info,
                "linhas": preview_linhas,
            }
        except Exception as exc:
            return {"ok": False, "erro": f"Falha ao ler planilha: {exc}"}

    #--- 4.5 Geração e Salvamento do Script R ---
    def registrar_mapeamento(self, payload: dict):
        try:
            script = gerar_script_r(payload)
            return {"ok": True, "script": str(script)}
        except Exception as exc:
            return {"ok": False, "erro": str(exc)}

    def salvar_script_r(self, conteudo_script: str, nome_sugerido: str = "script_easyr.R"):
        if not self._janela:
            return {"ok": False, "erro": "Janela principal ainda não inicializada."}

        try:
            if hasattr(webview, "FileDialog"):
                dialog_save = webview.FileDialog.SAVE
            else:
                dialog_save = getattr(webview, "SAVE_DIALOG", 30)

            caminho = self._janela.create_file_dialog(
                dialog_save,
                save_filename=nome_sugerido,
                file_types=("Script R (*.R)", "Todos os arquivos (*.*)"),
            )
            if not caminho:
                return {"ok": False}

            destino = caminho if isinstance(caminho, str) else str(list(caminho)[0])
            if not destino.lower().endswith(".r"):
                destino += ".R"

            with open(destino, "w", encoding="utf-8") as f:
                f.write(conteudo_script)
            return {"ok": True, "caminho": destino}
        except Exception as exc:
            return {"ok": False, "erro": f"Erro ao salvar arquivo: {exc}"}


#========= 5. BLOCO DE IGNIÇÃO ==============
if __name__ == "__main__":
    api = Api()
    janela = webview.create_window(
        title="EasyR",
        url=str(HTML_PATH),
        js_api=api,
        width=1220,
        height=780,
        min_size=(980, 640),
    )
    api._janela = janela
    webview.start()