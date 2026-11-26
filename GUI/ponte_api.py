#========= 1. IMPORTAÇÕES (FERRAMENTAS) ==============
import webview
from GUI.catalogo_analises import CATALOGO_ANALISES
from GUI.leitor_dados import LeitorPlanilha
from RSTS import gerar_script_r


#========= 2. CLASSE PONTE GUI (MEMÓRIA E INICIALIZAÇÃO) ==============
class PonteGUI:
    def __init__(self):
        self.leitor = LeitorPlanilha()
        self.janela = None
        self.ultima_configuracao: dict = {}

    #========= 3. CATÁLOGO E LEITURA DE PLANILHAS ==============
    #--- 3.1 Entrega do Catálogo ---
    def obter_catalogo(self) -> list[dict]:
        return CATALOGO_ANALISES

    #--- 3.2 Seleção de Arquivo ---
    def selecionar_arquivo(self) -> dict:
        try:
            tipo_dialogo = (
                webview.FileDialog.OPEN if hasattr(webview, "FileDialog") else webview.OPEN_DIALOG
            )
            filtros = ("Planilhas Excel e CSV (*.xlsx;*.xls;*.csv)", "Todos os arquivos (*.*)")
            resultado = self.janela.create_file_dialog(
                tipo_dialogo, allow_multiple=False, file_types=filtros
            )
            if not resultado:
                return {"ok": False}

            self.leitor.carregar_arquivo(resultado[0])
            return self.leitor.exportar_para_interface()
        except Exception as erro:
            return {"ok": False, "erro": str(erro)}

    #--- 3.3 Troca de Aba ---
    def trocar_aba(self, nome_aba: str) -> dict:
        try:
            if not self.leitor.caminho_arquivo:
                return {"ok": False}
            self.leitor.carregar_aba(nome_aba)
            return self.leitor.exportar_para_interface()
        except Exception as erro:
            return {"ok": False, "erro": str(erro)}

    #========= 4. GERAÇÃO E SALVAMENTO DO SCRIPT R ==============
    #--- 4.1 Geração do Código ---
    def registrar_mapeamento(self, configuracao: dict) -> dict:
        try:
            self.ultima_configuracao = configuracao
            script_r = gerar_script_r(configuracao)
            return {
                "ok": True,
                "configuracao": configuracao,
                "script": script_r,
            }
        except Exception as erro:
            return {"ok": False, "erro": str(erro)}

    #--- 4.2 Exportação em Arquivo .R ---
    def salvar_script_r(self, conteudo_script: str, nome_sugerido: str = "analise_easyr.R") -> dict:
        try:
            tipo_dialogo = (
                webview.FileDialog.SAVE if hasattr(webview, "FileDialog") else webview.SAVE_DIALOG
            )
            filtros = ("Script R (*.R)", "Todos os arquivos (*.*)")
            caminho_destino = self.janela.create_file_dialog(
                tipo_dialogo,
                save_filename=nome_sugerido,
                file_types=filtros,
            )
            if not caminho_destino:
                return {"ok": False}

            if isinstance(caminho_destino, (list, tuple)):
                caminho_destino = caminho_destino[0]

            if not str(caminho_destino).lower().endswith(".r"):
                caminho_destino = f"{caminho_destino}.R"

            with open(caminho_destino, "w", encoding="utf-8") as arq:
                arq.write(conteudo_script)

            return {"ok": True, "caminho": caminho_destino}
        except Exception as erro:
            return {"ok": False, "erro": str(erro)}