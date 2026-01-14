"""
Baiak-Zika Launcher
Auto-update system for game client
"""

import sys
import os
import json
import zipfile
import shutil
import subprocess
import threading
from pathlib import Path

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QProgressBar, QMessageBox, QFrame
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
    from PyQt5.QtGui import QFont, QPixmap, QPalette, QColor, QIcon
except ImportError:
    print("PyQt5 não encontrado. Instalando...")
    os.system("pip install PyQt5")
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QProgressBar, QMessageBox, QFrame
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
    from PyQt5.QtGui import QFont, QPixmap, QPalette, QColor, QIcon

try:
    import requests
except ImportError:
    print("requests não encontrado. Instalando...")
    os.system("pip install requests")
    import requests


# ============================================
# CONFIGURAÇÕES DO LAUNCHER
# ============================================
CONFIG = {
    "serverName": "Baiak-Zika",
    "clientExecutable": "client.exe",
    "localConfigFile": "local_config.json",
    # URL do JSON remoto com versões
    "remoteConfigUrl": "https://gist.githubusercontent.com/pauloandre45/e59926d5c0c8cbc9d225e06db7e446ad/raw/SERVIDOR_launcher_config.json",
    "clientDownloadUrl": "https://github.com/pauloandre45/baiak-zika-launcher/releases/download/v1.0.0/Baiak-zika-15.zip",
    "currentVersion": "1.0.0",
    # Pastas para fazer backup durante atualização
    "backupFolders": ["conf", "characterdata"],
}


def get_app_path():
    """Retorna o caminho do executável ou script"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_google_drive_confirm_url(url, session):
    """Lida com confirmação de download do Google Drive para arquivos grandes"""
    response = session.get(url, stream=True)
    
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            return f"{url}&confirm={value}"
    
    # Verifica se tem token de confirmação no HTML
    if b'confirm=' in response.content:
        import re
        match = re.search(b'confirm=([^&"]+)', response.content)
        if match:
            return f"{url}&confirm={match.group(1).decode()}"
    
    return url


class DownloadThread(QThread):
    """Thread para download com progresso"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished_download = pyqtSignal(bool, str)
    
    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path
    
    def run(self):
        try:
            self.status.emit("Conectando ao servidor...")
            
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            download_url = self.url
            
            # Para Google Drive, precisamos lidar com confirmação de vírus scan
            if "drive.google.com" in self.url:
                # Primeira requisição para pegar o token de confirmação
                response = session.get(self.url, stream=True)
                
                # Procura por token de confirmação em cookies ou HTML
                for key, value in response.cookies.items():
                    if key.startswith('download_warning'):
                        download_url = f"{self.url}&confirm={value}"
                        break
                
                # Se não achou em cookies, procura no HTML
                if download_url == self.url:
                    content = response.content.decode('utf-8', errors='ignore')
                    if 'confirm=' in content:
                        import re
                        match = re.search(r'confirm=([0-9A-Za-z_-]+)', content)
                        if match:
                            download_url = f"{self.url}&confirm={match.group(1)}"
                    # Tenta também o formato uuid
                    if 'uuid=' in content:
                        match = re.search(r'uuid=([0-9a-f-]+)', content)
                        if match:
                            download_url = f"{self.url}&confirm=t&uuid={match.group(1)}"
            
            self.status.emit("Baixando atualização...")
            
            # Faz o download real
            response = session.get(download_url, stream=True, timeout=30)
            
            # Verifica se é realmente um arquivo (não uma página HTML)
            content_type = response.headers.get('content-type', '')
            if 'text/html' in content_type:
                # Ainda é página de confirmação, tenta forçar
                download_url = self.url.replace('uc?export=download', 'uc?export=download&confirm=t')
                response = session.get(download_url, stream=True, timeout=30)
            
            total_size = int(response.headers.get('content-length', 0))
            
            downloaded = 0
            with open(self.save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=32768):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            self.progress.emit(progress)
                        else:
                            # Se não sabe o tamanho, mostra MB baixados
                            self.status.emit(f"Baixando... {downloaded // (1024*1024)} MB")
            
            # Verifica se o arquivo baixado é válido (não é HTML de erro)
            if os.path.getsize(self.save_path) < 1000:
                with open(self.save_path, 'r', errors='ignore') as f:
                    content = f.read()
                    if '<html' in content.lower():
                        os.remove(self.save_path)
                        self.finished_download.emit(False, "Erro: Google Drive bloqueou o download. Tente novamente.")
                        return
            
            self.finished_download.emit(True, "Download concluído!")
            
        except requests.exceptions.Timeout:
            self.finished_download.emit(False, "Erro: Timeout - servidor demorou muito para responder")
        except requests.exceptions.ConnectionError:
            self.finished_download.emit(False, "Erro: Sem conexão com a internet")
        except Exception as e:
            self.finished_download.emit(False, f"Erro no download: {str(e)}")


class UpdateChecker(QThread):
    """Thread para verificar atualizações"""
    result = pyqtSignal(bool, str, dict)  # needs_update, message, remote_config
    
    def __init__(self, remote_url, local_version):
        super().__init__()
        self.remote_url = remote_url
        self.local_version = local_version
    
    def run(self):
        try:
            response = requests.get(self.remote_url, timeout=10)
            if response.status_code == 200:
                remote_config = response.json()
                remote_version = remote_config.get("clientVersion", "0.0.0")
                
                if self.compare_versions(remote_version, self.local_version) > 0:
                    self.result.emit(True, f"Nova versão disponível: {remote_version}", remote_config)
                else:
                    self.result.emit(False, "Cliente atualizado!", remote_config)
            else:
                self.result.emit(False, "Não foi possível verificar atualizações", {})
        except Exception as e:
            self.result.emit(False, f"Erro ao verificar: {str(e)}", {})
    
    def compare_versions(self, v1, v2):
        """Compara versões (1.0.0 vs 1.0.1)"""
        v1_parts = [int(x) for x in v1.split('.')]
        v2_parts = [int(x) for x in v2.split('.')]
        
        for i in range(max(len(v1_parts), len(v2_parts))):
            v1_val = v1_parts[i] if i < len(v1_parts) else 0
            v2_val = v2_parts[i] if i < len(v2_parts) else 0
            if v1_val > v2_val:
                return 1
            elif v1_val < v2_val:
                return -1
        return 0


class BaiakZikaLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app_path = get_app_path()
        self.load_local_config()
        self.init_ui()
        self.check_for_updates()
    
    def load_local_config(self):
        """Carrega configuração local"""
        config_path = os.path.join(self.app_path, CONFIG["localConfigFile"])
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.local_config = json.load(f)
            except:
                self.local_config = {"version": CONFIG["currentVersion"]}
        else:
            self.local_config = {"version": CONFIG["currentVersion"]}
            self.save_local_config()
    
    def save_local_config(self):
        """Salva configuração local"""
        config_path = os.path.join(self.app_path, CONFIG["localConfigFile"])
        with open(config_path, 'w') as f:
            json.dump(self.local_config, f, indent=2)
    
    def init_ui(self):
        """Inicializa interface"""
        self.setWindowTitle(f"{CONFIG['serverName']} Launcher")
        self.setFixedSize(500, 350)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a2e;
            }
            QLabel {
                color: #eee;
            }
            QPushButton {
                background-color: #e94560;
                color: white;
                border: none;
                padding: 15px 30px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #ff6b6b;
            }
            QPushButton:disabled {
                background-color: #555;
            }
            QProgressBar {
                border: 2px solid #333;
                border-radius: 5px;
                text-align: center;
                background-color: #16213e;
            }
            QProgressBar::chunk {
                background-color: #e94560;
                border-radius: 3px;
            }
        """)
        
        # Widget central
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Título
        title = QLabel(CONFIG['serverName'])
        title.setFont(QFont('Arial', 28, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #e94560;")
        layout.addWidget(title)
        
        # Subtítulo
        subtitle = QLabel("Launcher Oficial")
        subtitle.setFont(QFont('Arial', 12))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #888;")
        layout.addWidget(subtitle)
        
        # Espaçador
        layout.addStretch()
        
        # Status
        self.status_label = QLabel("Verificando atualizações...")
        self.status_label.setFont(QFont('Arial', 10))
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(25)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Versão
        self.version_label = QLabel(f"Versão: {self.local_config.get('version', '1.0.0')}")
        self.version_label.setFont(QFont('Arial', 9))
        self.version_label.setAlignment(Qt.AlignCenter)
        self.version_label.setStyleSheet("color: #666;")
        layout.addWidget(self.version_label)
        
        # Botões
        btn_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("▶  JOGAR")
        self.play_btn.setFixedSize(200, 50)
        self.play_btn.clicked.connect(self.start_game)
        self.play_btn.setEnabled(False)
        btn_layout.addWidget(self.play_btn)
        
        self.update_btn = QPushButton("⟳  ATUALIZAR")
        self.update_btn.setFixedSize(150, 50)
        self.update_btn.setStyleSheet("""
            QPushButton {
                background-color: #0f3460;
            }
            QPushButton:hover {
                background-color: #16213e;
            }
            QPushButton:disabled {
                background-color: #333;
            }
        """)
        self.update_btn.clicked.connect(self.start_update)
        self.update_btn.setVisible(False)
        btn_layout.addWidget(self.update_btn)
        
        layout.addLayout(btn_layout)
    
    def check_for_updates(self):
        """Verifica se há atualizações"""
        self.status_label.setText("Verificando atualizações...")
        
        # Se não tem URL remota configurada, apenas habilita o botão jogar
        if "SEU_USUARIO" in CONFIG["remoteConfigUrl"] or "SEU_GIST_ID" in CONFIG["remoteConfigUrl"]:
            self.status_label.setText("⚠ Configure a URL remota para auto-update")
            self.play_btn.setEnabled(True)
            return
        
        self.checker = UpdateChecker(
            CONFIG["remoteConfigUrl"],
            self.local_config.get("version", "1.0.0")
        )
        self.checker.result.connect(self.on_update_check_complete)
        self.checker.start()
    
    def on_update_check_complete(self, needs_update, message, remote_config):
        """Callback quando verificação termina"""
        self.status_label.setText(message)
        
        if needs_update:
            self.update_btn.setVisible(True)
            self.play_btn.setEnabled(False)
            self.remote_config = remote_config
        else:
            self.play_btn.setEnabled(True)
            self.update_btn.setVisible(False)
    
    def start_update(self):
        """Inicia download da atualização"""
        self.update_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # URL de download
        download_url = self.remote_config.get("clientDownloadUrl", CONFIG["clientDownloadUrl"])
        
        # Caminho para salvar
        zip_path = os.path.join(self.app_path, "update.zip")
        
        self.downloader = DownloadThread(download_url, zip_path)
        self.downloader.progress.connect(self.progress_bar.setValue)
        self.downloader.status.connect(self.status_label.setText)
        self.downloader.finished_download.connect(self.on_download_complete)
        self.downloader.start()
    
    def on_download_complete(self, success, message):
        """Callback quando download termina"""
        if success:
            self.status_label.setText("Extraindo arquivos...")
            self.extract_update()
        else:
            self.status_label.setText(message)
            self.update_btn.setEnabled(True)
            QMessageBox.critical(self, "Erro", message)
    
    def extract_update(self):
        """Extrai arquivos do update"""
        try:
            zip_path = os.path.join(self.app_path, "update.zip")
            
            # Backup das pastas importantes
            self.status_label.setText("Fazendo backup...")
            for folder in CONFIG["backupFolders"]:
                folder_path = os.path.join(self.app_path, folder)
                backup_path = os.path.join(self.app_path, f"{folder}_backup")
                if os.path.exists(folder_path):
                    if os.path.exists(backup_path):
                        shutil.rmtree(backup_path)
                    shutil.copytree(folder_path, backup_path)
            
            # Extrai o ZIP
            self.status_label.setText("Extraindo arquivos...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.app_path)
            
            # Restaura backups
            self.status_label.setText("Restaurando configurações...")
            for folder in CONFIG["backupFolders"]:
                backup_path = os.path.join(self.app_path, f"{folder}_backup")
                folder_path = os.path.join(self.app_path, folder)
                if os.path.exists(backup_path):
                    if os.path.exists(folder_path):
                        shutil.rmtree(folder_path)
                    shutil.move(backup_path, folder_path)
            
            # Remove o ZIP
            os.remove(zip_path)
            
            # Atualiza versão local
            if hasattr(self, 'remote_config') and self.remote_config:
                self.local_config["version"] = self.remote_config.get("clientVersion", "1.0.0")
                self.save_local_config()
                self.version_label.setText(f"Versão: {self.local_config['version']}")
            
            self.status_label.setText("✓ Atualização concluída!")
            self.progress_bar.setVisible(False)
            self.play_btn.setEnabled(True)
            self.update_btn.setVisible(False)
            
            QMessageBox.information(self, "Sucesso", "Cliente atualizado com sucesso!")
            
        except Exception as e:
            self.status_label.setText(f"Erro na extração: {str(e)}")
            QMessageBox.critical(self, "Erro", f"Erro ao extrair: {str(e)}")
            self.update_btn.setEnabled(True)
    
    def start_game(self):
        """Inicia o cliente do jogo"""
        client_path = os.path.join(self.app_path, CONFIG["clientExecutable"])
        
        if os.path.exists(client_path):
            try:
                self.status_label.setText("Iniciando jogo...")
                subprocess.Popen([client_path], cwd=self.app_path)
                # Fecha o launcher após iniciar o jogo
                QApplication.quit()
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao iniciar: {str(e)}")
        else:
            QMessageBox.warning(
                self, 
                "Cliente não encontrado",
                f"O arquivo {CONFIG['clientExecutable']} não foi encontrado.\n\n"
                "Clique em ATUALIZAR para baixar o cliente."
            )
            self.update_btn.setVisible(True)
            self.update_btn.setEnabled(True)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Ícone (se existir)
    icon_path = os.path.join(get_app_path(), "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    launcher = BaiakZikaLauncher()
    launcher.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
