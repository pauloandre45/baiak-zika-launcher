"""
Baiak-Zika Launcher v2
Auto-update system for game client - Robust Version
"""

import sys
import os
import json
import zipfile
import shutil
import subprocess
import urllib.request
import ssl
from pathlib import Path

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QProgressBar, QMessageBox, QFrame
    )
    from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
    from PyQt5.QtGui import QFont, QIcon
except ImportError:
    print("PyQt5 não encontrado. Instalando...")
    os.system("pip install PyQt5")
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QProgressBar, QMessageBox, QFrame
    )
    from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
    from PyQt5.QtGui import QFont, QIcon


# ============================================
# CONFIGURAÇÕES DO LAUNCHER
# ============================================
CONFIG = {
    "serverName": "Baiak-Zika",
    "clientExecutable": "Baiak-zika-15/bin/client.exe",  # Caminho do client dentro do ZIP extraído
    "localConfigFile": "local_config.json",
    "remoteConfigUrl": "https://gist.githubusercontent.com/pauloandre45/e59926d5c0c8cbc9d225e06db7e446ad/raw/SERVIDOR_launcher_config.json",
    "clientDownloadUrl": "https://github.com/pauloandre45/baiak-zika-launcher/releases/download/v1.0.0/Baiak-zika-15.zip",
    "currentVersion": "1.0.0",
    "backupFolders": ["conf", "characterdata"],
}


def get_app_path():
    """Retorna o caminho do executável ou script"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


class DownloadWorker(QThread):
    """Worker thread para download com urllib (mais estável)"""
    progress = pyqtSignal(int, str)  # percent, status
    finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self._running = True
    
    def stop(self):
        self._running = False
    
    def run(self):
        try:
            self.progress.emit(0, "Conectando ao servidor...")
            
            # Criar contexto SSL que aceita certificados
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            # Criar request com headers
            req = urllib.request.Request(
                self.url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            
            # Abrir conexão
            response = urllib.request.urlopen(req, timeout=60, context=ctx)
            
            # Pegar tamanho total
            total_size = response.headers.get('Content-Length')
            if total_size:
                total_size = int(total_size)
            
            self.progress.emit(0, f"Baixando... (0 MB)")
            
            # Baixar em chunks
            downloaded = 0
            chunk_size = 65536  # 64KB chunks
            
            with open(self.save_path, 'wb') as f:
                while self._running:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Calcular progresso
                    mb_downloaded = downloaded / (1024 * 1024)
                    
                    if total_size:
                        percent = int((downloaded / total_size) * 100)
                        mb_total = total_size / (1024 * 1024)
                        self.progress.emit(percent, f"Baixando... {mb_downloaded:.1f} / {mb_total:.1f} MB")
                    else:
                        self.progress.emit(0, f"Baixando... {mb_downloaded:.1f} MB")
            
            if not self._running:
                # Download foi cancelado
                if os.path.exists(self.save_path):
                    os.remove(self.save_path)
                self.finished.emit(False, "Download cancelado")
                return
            
            # Verificar se o arquivo é válido
            if os.path.getsize(self.save_path) < 10000:
                with open(self.save_path, 'r', errors='ignore') as f:
                    content = f.read(1000)
                    if '<html' in content.lower() or 'error' in content.lower():
                        os.remove(self.save_path)
                        self.finished.emit(False, "Erro: Servidor retornou página de erro")
                        return
            
            self.finished.emit(True, "Download concluído!")
            
        except urllib.error.URLError as e:
            self.finished.emit(False, f"Erro de conexão: {str(e.reason)}")
        except Exception as e:
            self.finished.emit(False, f"Erro: {str(e)}")


class BaiakZikaLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app_path = get_app_path()
        self.download_thread = None
        self.remote_config = {}
        self.load_local_config()
        self.init_ui()
        # Verificar atualizações após a janela abrir
        QTimer.singleShot(500, self.check_for_updates)
    
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
        try:
            with open(config_path, 'w') as f:
                json.dump(self.local_config, f, indent=2)
        except Exception as e:
            print(f"Erro ao salvar config: {e}")
    
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
                color: white;
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
        self.status_label = QLabel("Iniciando...")
        self.status_label.setFont(QFont('Arial', 10))
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(25)
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
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
        self.play_btn.setFixedSize(150, 50)
        self.play_btn.clicked.connect(self.start_game)
        self.play_btn.setEnabled(False)
        btn_layout.addWidget(self.play_btn)
        
        self.update_btn = QPushButton("⟳  ATUALIZAR")
        self.update_btn.setFixedSize(130, 50)
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
        
        self.repair_btn = QPushButton("🔧 REPARAR")
        self.repair_btn.setFixedSize(110, 50)
        self.repair_btn.setStyleSheet("""
            QPushButton {
                background-color: #6b4c9a;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #8b6cba;
            }
            QPushButton:disabled {
                background-color: #333;
            }
        """)
        self.repair_btn.clicked.connect(self.start_repair)
        self.repair_btn.setVisible(False)
        btn_layout.addWidget(self.repair_btn)
        
        layout.addLayout(btn_layout)
    
    def check_for_updates(self):
        """Verifica se há atualizações"""
        self.status_label.setText("Verificando atualizações...")
        
        try:
            # Criar contexto SSL
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            req = urllib.request.Request(
                CONFIG["remoteConfigUrl"],
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            
            response = urllib.request.urlopen(req, timeout=10, context=ctx)
            data = response.read().decode('utf-8')
            self.remote_config = json.loads(data)
            
            remote_version = self.remote_config.get("clientVersion", "0.0.0")
            local_version = self.local_config.get("version", "0.0.0")
            
            # Verificar se o client existe
            client_path = os.path.join(self.app_path, CONFIG["clientExecutable"])
            client_exists = os.path.exists(client_path)
            
            if not client_exists:
                # Não tem client - só mostra ATUALIZAR
                self.status_label.setText("Cliente não instalado - Clique em ATUALIZAR")
                self.update_btn.setVisible(True)
                self.update_btn.setEnabled(True)
                self.play_btn.setVisible(False)
                self.repair_btn.setVisible(False)
            elif self.compare_versions(remote_version, local_version) > 0:
                # Tem client mas versão antiga - mostra JOGAR e ATUALIZAR
                self.status_label.setText(f"Nova versão disponível: {remote_version}")
                self.update_btn.setVisible(True)
                self.update_btn.setEnabled(True)
                self.play_btn.setVisible(True)
                self.play_btn.setEnabled(True)
                self.repair_btn.setVisible(True)
                self.repair_btn.setEnabled(True)
            else:
                # Client atualizado - mostra JOGAR e REPARAR
                self.status_label.setText("Cliente atualizado!")
                self.play_btn.setVisible(True)
                self.play_btn.setEnabled(True)
                self.update_btn.setVisible(False)
                self.repair_btn.setVisible(True)
                self.repair_btn.setEnabled(True)
                
        except Exception as e:
            self.status_label.setText(f"Erro ao verificar: {str(e)[:50]}")
            # Verificar se client existe mesmo com erro de conexão
            client_path = os.path.join(self.app_path, CONFIG["clientExecutable"])
            if os.path.exists(client_path):
                self.play_btn.setVisible(True)
                self.play_btn.setEnabled(True)
                self.update_btn.setVisible(True)
                self.update_btn.setEnabled(True)
            else:
                self.play_btn.setVisible(False)
                self.update_btn.setVisible(True)
                self.update_btn.setEnabled(True)
    
    def compare_versions(self, v1, v2):
        """Compara versões (1.0.0 vs 1.0.1)"""
        try:
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
        except:
            return 0
    
    def start_update(self):
        """Inicia download da atualização"""
        self.update_btn.setEnabled(False)
        self.play_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # URL de download
        download_url = self.remote_config.get("newClientUrl") or \
                       self.remote_config.get("clientDownloadUrl") or \
                       CONFIG["clientDownloadUrl"]
        
        # Caminho para salvar
        zip_path = os.path.join(self.app_path, "update.zip")
        
        # Criar thread de download
        self.download_thread = DownloadWorker(download_url, zip_path)
        self.download_thread.progress.connect(self.on_download_progress)
        self.download_thread.finished.connect(self.on_download_complete)
        self.download_thread.start()
    
    def start_repair(self):
        """Força o download do client (reparar arquivos)"""
        reply = QMessageBox.question(
            self, 
            "Reparar Cliente",
            "Isso vai baixar novamente todos os arquivos do cliente.\n"
            "Suas configurações serão mantidas.\n\n"
            "Deseja continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.start_update()
    
    def on_download_progress(self, percent, status):
        """Atualiza progresso do download"""
        self.progress_bar.setValue(percent)
        self.status_label.setText(status)
    
    def on_download_complete(self, success, message):
        """Callback quando download termina"""
        if success:
            self.status_label.setText("Extraindo arquivos...")
            # Usar QTimer para não bloquear a UI
            QTimer.singleShot(100, self.extract_update)
        else:
            self.status_label.setText(message)
            self.update_btn.setEnabled(True)
            self.play_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
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
            if self.remote_config:
                self.local_config["version"] = self.remote_config.get("clientVersion", "1.0.0")
                self.save_local_config()
                self.version_label.setText(f"Versão: {self.local_config['version']}")
            
            self.status_label.setText("✓ Atualização concluída!")
            self.progress_bar.setVisible(False)
            self.play_btn.setVisible(True)  # Mostrar botão JOGAR
            self.play_btn.setEnabled(True)
            self.update_btn.setVisible(False)
            
            QMessageBox.information(self, "Sucesso", "Cliente atualizado com sucesso!")
            
        except Exception as e:
            self.status_label.setText(f"Erro na extração: {str(e)}")
            QMessageBox.critical(self, "Erro", f"Erro ao extrair: {str(e)}")
            self.update_btn.setEnabled(True)
            self.play_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
    
    def start_game(self):
        """Inicia o cliente do jogo"""
        client_path = os.path.join(self.app_path, CONFIG["clientExecutable"])
        
        if os.path.exists(client_path):
            try:
                self.status_label.setText("Iniciando jogo...")
                # Usar subprocess.Popen com flags corretas
                if sys.platform == 'win32':
                    subprocess.Popen([client_path], cwd=self.app_path, 
                                   creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
                else:
                    subprocess.Popen([client_path], cwd=self.app_path)
                # Fecha o launcher após iniciar o jogo
                QTimer.singleShot(1000, QApplication.quit)
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
    
    def closeEvent(self, event):
        """Ao fechar a janela"""
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.stop()
            self.download_thread.wait(2000)
        event.accept()


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
