"""
Baiak-Zika Launcher v2
Estilo Tibia - com background, notícias, etc.
"""

import sys
import os
import json
import zipfile
import shutil
import subprocess
import threading
from pathlib import Path
from datetime import datetime

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QProgressBar, QMessageBox, QFrame,
        QTextBrowser, QGraphicsDropShadowEffect, QScrollArea
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer, QUrl
    from PyQt5.QtGui import (
        QFont, QPixmap, QPalette, QColor, QIcon, QPainter, 
        QBrush, QLinearGradient, QFontDatabase
    )
except ImportError:
    print("PyQt5 não encontrado. Instalando...")
    os.system("pip install PyQt5")
    from PyQt5.QtWidgets import *
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *

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
    "remoteConfigUrl": "https://gist.githubusercontent.com/pauloandre45/e59926d5c0c8cbc9d225e06db7e446ad/raw/SERVIDOR_launcher_config.json",
    "clientDownloadUrl": "https://drive.google.com/uc?export=download&id=1axpKG8b-gE3HRN1xwez6D_K3SKWlN-9p",
    "currentVersion": "1.0.0",
    "backupFolders": ["conf", "characterdata"],
    # Website/Discord para botões
    "website": "https://baiak-zika.com",
    "discord": "https://discord.gg/baiak-zika",
}

# Cores do tema
THEME = {
    "primary": "#c4a052",      # Dourado
    "secondary": "#1a1a1a",    # Preto
    "accent": "#8b7355",       # Marrom
    "text": "#ffffff",         # Branco
    "textDark": "#cccccc",     # Cinza claro
    "success": "#4CAF50",      # Verde
    "error": "#f44336",        # Vermelho
    "background": "#0d0d0d",   # Fundo escuro
}


def get_app_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


class DownloadThread(QThread):
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
            
            if "drive.google.com" in self.url:
                response = session.get(self.url, stream=True)
                for key, value in response.cookies.items():
                    if key.startswith('download_warning'):
                        download_url = f"{self.url}&confirm={value}"
                        break
                
                if download_url == self.url:
                    content = response.content.decode('utf-8', errors='ignore')
                    if 'confirm=' in content:
                        import re
                        match = re.search(r'confirm=([0-9A-Za-z_-]+)', content)
                        if match:
                            download_url = f"{self.url}&confirm={match.group(1)}"
            
            self.status.emit("Baixando atualização...")
            response = session.get(download_url, stream=True, timeout=30)
            
            content_type = response.headers.get('content-type', '')
            if 'text/html' in content_type:
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
                            self.status.emit(f"Baixando... {downloaded // (1024*1024)} MB")
            
            if os.path.getsize(self.save_path) < 1000:
                with open(self.save_path, 'r', errors='ignore') as f:
                    content = f.read()
                    if '<html' in content.lower():
                        os.remove(self.save_path)
                        self.finished_download.emit(False, "Erro: Download bloqueado")
                        return
            
            self.finished_download.emit(True, "Download concluído!")
            
        except Exception as e:
            self.finished_download.emit(False, f"Erro: {str(e)}")


class UpdateChecker(QThread):
    result = pyqtSignal(bool, str, dict)
    
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
                    self.result.emit(True, f"Nova versão: {remote_version}", remote_config)
                else:
                    self.result.emit(False, "Cliente atualizado!", remote_config)
            else:
                self.result.emit(False, "Servidor offline", {})
        except Exception as e:
            self.result.emit(False, f"Sem conexão", {})
    
    def compare_versions(self, v1, v2):
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


class NewsWidget(QFrame):
    """Widget de notícias estilo Tibia"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(0, 0, 0, 0.7);
                border: 2px solid {THEME['primary']};
                border-radius: 10px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Título
        title = QLabel("📜 NOTÍCIAS")
        title.setFont(QFont('Georgia', 14, QFont.Bold))
        title.setStyleSheet(f"color: {THEME['primary']}; background: transparent; border: none;")
        layout.addWidget(title)
        
        # Área de notícias
        self.news_area = QTextBrowser()
        self.news_area.setOpenExternalLinks(True)
        self.news_area.setStyleSheet(f"""
            QTextBrowser {{
                background-color: transparent;
                color: {THEME['textDark']};
                border: none;
                font-size: 12px;
            }}
            QScrollBar:vertical {{
                background: rgba(0,0,0,0.3);
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {THEME['primary']};
                border-radius: 4px;
            }}
        """)
        
        # Notícias padrão
        self.news_area.setHtml("""
            <style>
                body { font-family: Georgia, serif; }
                .date { color: #c4a052; font-size: 10px; }
                .title { color: #ffffff; font-weight: bold; font-size: 13px; }
                .content { color: #cccccc; font-size: 11px; margin-bottom: 15px; }
            </style>
            <p class="date">📅 14/01/2026</p>
            <p class="title">🎮 Bem-vindo ao Baiak-Zika!</p>
            <p class="content">Servidor online 24/7 com eventos diários e muita diversão!</p>
            
            <p class="date">📅 10/01/2026</p>
            <p class="title">⚔️ Novo Boss Semanal</p>
            <p class="content">Derrote o boss e ganhe itens exclusivos!</p>
            
            <p class="date">📅 05/01/2026</p>
            <p class="title">🎁 Evento de Boas-Vindas</p>
            <p class="content">Novos jogadores ganham kit inicial!</p>
        """)
        layout.addWidget(self.news_area)
    
    def update_news(self, news_html):
        self.news_area.setHtml(news_html)


class ServerInfoWidget(QFrame):
    """Widget com info do servidor"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(0, 0, 0, 0.7);
                border: 2px solid {THEME['primary']};
                border-radius: 10px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Status do servidor
        self.status_label = QLabel("🟢 SERVIDOR ONLINE")
        self.status_label.setFont(QFont('Arial', 11, QFont.Bold))
        self.status_label.setStyleSheet(f"color: {THEME['success']}; background: transparent; border: none;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Players online
        self.players_label = QLabel("👥 Players: ---")
        self.players_label.setFont(QFont('Arial', 10))
        self.players_label.setStyleSheet(f"color: {THEME['textDark']}; background: transparent; border: none;")
        self.players_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.players_label)


class BaiakZikaLauncherV2(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app_path = get_app_path()
        self.load_local_config()
        self.init_ui()
        self.check_for_updates()
    
    def load_local_config(self):
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
        config_path = os.path.join(self.app_path, CONFIG["localConfigFile"])
        with open(config_path, 'w') as f:
            json.dump(self.local_config, f, indent=2)
    
    def paintEvent(self, event):
        """Desenha o background"""
        painter = QPainter(self)
        
        # Gradiente de fundo
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(30, 30, 40))
        gradient.setColorAt(0.5, QColor(15, 15, 25))
        gradient.setColorAt(1, QColor(5, 5, 15))
        painter.fillRect(self.rect(), gradient)
        
        # Tenta carregar imagem de fundo
        bg_path = os.path.join(self.app_path, "background.png")
        if os.path.exists(bg_path):
            pixmap = QPixmap(bg_path)
            painter.setOpacity(0.3)
            painter.drawPixmap(self.rect(), pixmap)
    
    def init_ui(self):
        self.setWindowTitle(f"{CONFIG['serverName']} Launcher")
        self.setFixedSize(800, 550)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        
        # Widget central
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # === BARRA SUPERIOR (título + fechar) ===
        top_bar = QFrame()
        top_bar.setFixedHeight(40)
        top_bar.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(0, 0, 0, 0.8);
                border-bottom: 2px solid {THEME['primary']};
            }}
        """)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(15, 0, 10, 0)
        
        # Logo/Título
        logo = QLabel(f"⚔️ {CONFIG['serverName']}")
        logo.setFont(QFont('Georgia', 16, QFont.Bold))
        logo.setStyleSheet(f"color: {THEME['primary']};")
        top_layout.addWidget(logo)
        
        top_layout.addStretch()
        
        # Botão minimizar
        min_btn = QPushButton("─")
        min_btn.setFixedSize(30, 30)
        min_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {THEME['text']};
                border: none;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.1);
            }}
        """)
        min_btn.clicked.connect(self.showMinimized)
        top_layout.addWidget(min_btn)
        
        # Botão fechar
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {THEME['text']};
                border: none;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: {THEME['error']};
            }}
        """)
        close_btn.clicked.connect(self.close)
        top_layout.addWidget(close_btn)
        
        main_layout.addWidget(top_bar)
        
        # === CONTEÚDO PRINCIPAL ===
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 10)
        content_layout.setSpacing(20)
        
        # --- Coluna esquerda (notícias) ---
        left_col = QVBoxLayout()
        
        self.news_widget = NewsWidget()
        self.news_widget.setFixedWidth(350)
        left_col.addWidget(self.news_widget)
        
        content_layout.addLayout(left_col)
        
        # --- Coluna direita (info + botões) ---
        right_col = QVBoxLayout()
        right_col.setSpacing(15)
        
        # Título grande
        title = QLabel(CONFIG['serverName'])
        title.setFont(QFont('Georgia', 36, QFont.Bold))
        title.setStyleSheet(f"""
            color: {THEME['primary']};
            background: transparent;
        """)
        title.setAlignment(Qt.AlignCenter)
        
        # Efeito de sombra
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(196, 160, 82, 150))
        title.setGraphicsEffect(shadow)
        
        right_col.addWidget(title)
        
        # Subtítulo
        subtitle = QLabel("O Melhor Servidor OTServ")
        subtitle.setFont(QFont('Georgia', 12))
        subtitle.setStyleSheet(f"color: {THEME['textDark']}; background: transparent;")
        subtitle.setAlignment(Qt.AlignCenter)
        right_col.addWidget(subtitle)
        
        right_col.addSpacing(10)
        
        # Info do servidor
        self.server_info = ServerInfoWidget()
        self.server_info.setFixedHeight(80)
        right_col.addWidget(self.server_info)
        
        right_col.addSpacing(5)
        
        # Status de atualização
        self.status_label = QLabel("Verificando atualizações...")
        self.status_label.setFont(QFont('Arial', 10))
        self.status_label.setStyleSheet(f"color: {THEME['textDark']}; background: transparent;")
        self.status_label.setAlignment(Qt.AlignCenter)
        right_col.addWidget(self.status_label)
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid {THEME['primary']};
                border-radius: 5px;
                background-color: rgba(0,0,0,0.5);
                text-align: center;
                color: white;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {THEME['primary']}, stop:1 #d4b062);
                border-radius: 3px;
            }}
        """)
        self.progress_bar.setVisible(False)
        right_col.addWidget(self.progress_bar)
        
        right_col.addStretch()
        
        # === BOTÕES ===
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(10)
        
        # Botão JOGAR
        self.play_btn = QPushButton("▶  JOGAR")
        self.play_btn.setFixedHeight(50)
        self.play_btn.setFont(QFont('Arial', 14, QFont.Bold))
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4CAF50, stop:1 #2E7D32);
                color: white;
                border: 2px solid #66BB6A;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #66BB6A, stop:1 #4CAF50);
            }}
            QPushButton:disabled {{
                background: #555;
                border-color: #666;
            }}
        """)
        self.play_btn.clicked.connect(self.start_game)
        self.play_btn.setEnabled(False)
        btn_layout.addWidget(self.play_btn)
        
        # Botão ATUALIZAR
        self.update_btn = QPushButton("⟳  ATUALIZAR")
        self.update_btn.setFixedHeight(40)
        self.update_btn.setFont(QFont('Arial', 11, QFont.Bold))
        self.update_btn.setCursor(Qt.PointingHandCursor)
        self.update_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {THEME['primary']}, stop:1 {THEME['accent']});
                color: white;
                border: 2px solid {THEME['primary']};
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #d4b062, stop:1 {THEME['primary']});
            }}
        """)
        self.update_btn.clicked.connect(self.start_update)
        self.update_btn.setVisible(False)
        btn_layout.addWidget(self.update_btn)
        
        right_col.addLayout(btn_layout)
        
        # Links (Website, Discord)
        links_layout = QHBoxLayout()
        links_layout.setSpacing(10)
        
        web_btn = QPushButton("🌐 Website")
        web_btn.setCursor(Qt.PointingHandCursor)
        web_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {THEME['primary']};
                border: 1px solid {THEME['primary']};
                border-radius: 5px;
                padding: 8px 15px;
            }}
            QPushButton:hover {{
                background: rgba(196, 160, 82, 0.2);
            }}
        """)
        web_btn.clicked.connect(lambda: self.open_url(CONFIG['website']))
        links_layout.addWidget(web_btn)
        
        discord_btn = QPushButton("💬 Discord")
        discord_btn.setCursor(Qt.PointingHandCursor)
        discord_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: #7289DA;
                border: 1px solid #7289DA;
                border-radius: 5px;
                padding: 8px 15px;
            }}
            QPushButton:hover {{
                background: rgba(114, 137, 218, 0.2);
            }}
        """)
        discord_btn.clicked.connect(lambda: self.open_url(CONFIG['discord']))
        links_layout.addWidget(discord_btn)
        
        right_col.addLayout(links_layout)
        
        content_layout.addLayout(right_col)
        main_layout.addWidget(content)
        
        # === BARRA INFERIOR ===
        bottom_bar = QFrame()
        bottom_bar.setFixedHeight(30)
        bottom_bar.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(0, 0, 0, 0.8);
                border-top: 1px solid {THEME['primary']};
            }}
        """)
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(15, 0, 15, 0)
        
        version_label = QLabel(f"Versão: {self.local_config.get('version', '1.0.0')}")
        version_label.setStyleSheet(f"color: {THEME['textDark']}; font-size: 10px;")
        bottom_layout.addWidget(version_label)
        
        bottom_layout.addStretch()
        
        copyright_label = QLabel("© 2026 Baiak-Zika. Todos os direitos reservados.")
        copyright_label.setStyleSheet(f"color: {THEME['textDark']}; font-size: 10px;")
        bottom_layout.addWidget(copyright_label)
        
        main_layout.addWidget(bottom_bar)
        
        # Para arrastar a janela
        self.drag_pos = None
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos:
            self.move(event.globalPos() - self.drag_pos)
    
    def open_url(self, url):
        import webbrowser
        webbrowser.open(url)
    
    def check_for_updates(self):
        self.status_label.setText("Verificando atualizações...")
        
        if "SEU_USUARIO" in CONFIG["remoteConfigUrl"]:
            self.status_label.setText("⚠ Configure a URL remota")
            self.play_btn.setEnabled(True)
            return
        
        self.checker = UpdateChecker(
            CONFIG["remoteConfigUrl"],
            self.local_config.get("version", "1.0.0")
        )
        self.checker.result.connect(self.on_update_check_complete)
        self.checker.start()
    
    def on_update_check_complete(self, needs_update, message, remote_config):
        self.status_label.setText(message)
        
        # Atualiza notícias se disponível
        if remote_config.get("news"):
            self.news_widget.update_news(remote_config["news"])
        
        if needs_update:
            self.update_btn.setVisible(True)
            self.play_btn.setEnabled(False)
            self.remote_config = remote_config
            self.status_label.setStyleSheet(f"color: {THEME['primary']}; background: transparent;")
        else:
            self.play_btn.setEnabled(True)
            self.update_btn.setVisible(False)
            self.status_label.setStyleSheet(f"color: {THEME['success']}; background: transparent;")
    
    def start_update(self):
        self.update_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        download_url = self.remote_config.get("clientDownloadUrl", CONFIG["clientDownloadUrl"])
        zip_path = os.path.join(self.app_path, "update.zip")
        
        self.downloader = DownloadThread(download_url, zip_path)
        self.downloader.progress.connect(self.progress_bar.setValue)
        self.downloader.status.connect(self.status_label.setText)
        self.downloader.finished_download.connect(self.on_download_complete)
        self.downloader.start()
    
    def on_download_complete(self, success, message):
        if success:
            self.status_label.setText("Extraindo arquivos...")
            self.extract_update()
        else:
            self.status_label.setText(message)
            self.update_btn.setEnabled(True)
            QMessageBox.critical(self, "Erro", message)
    
    def extract_update(self):
        try:
            zip_path = os.path.join(self.app_path, "update.zip")
            
            self.status_label.setText("Fazendo backup...")
            for folder in CONFIG["backupFolders"]:
                folder_path = os.path.join(self.app_path, folder)
                backup_path = os.path.join(self.app_path, f"{folder}_backup")
                if os.path.exists(folder_path):
                    if os.path.exists(backup_path):
                        shutil.rmtree(backup_path)
                    shutil.copytree(folder_path, backup_path)
            
            self.status_label.setText("Extraindo arquivos...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.app_path)
            
            self.status_label.setText("Restaurando configurações...")
            for folder in CONFIG["backupFolders"]:
                backup_path = os.path.join(self.app_path, f"{folder}_backup")
                folder_path = os.path.join(self.app_path, folder)
                if os.path.exists(backup_path):
                    if os.path.exists(folder_path):
                        shutil.rmtree(folder_path)
                    shutil.move(backup_path, folder_path)
            
            os.remove(zip_path)
            
            if hasattr(self, 'remote_config') and self.remote_config:
                self.local_config["version"] = self.remote_config.get("clientVersion", "1.0.0")
                self.save_local_config()
            
            self.status_label.setText("✓ Atualização concluída!")
            self.status_label.setStyleSheet(f"color: {THEME['success']}; background: transparent;")
            self.progress_bar.setVisible(False)
            self.play_btn.setEnabled(True)
            self.update_btn.setVisible(False)
            
            QMessageBox.information(self, "Sucesso", "Cliente atualizado com sucesso!")
            
        except Exception as e:
            self.status_label.setText(f"Erro: {str(e)}")
            QMessageBox.critical(self, "Erro", f"Erro ao extrair: {str(e)}")
            self.update_btn.setEnabled(True)
    
    def start_game(self):
        client_path = os.path.join(self.app_path, CONFIG["clientExecutable"])
        
        if os.path.exists(client_path):
            try:
                self.status_label.setText("Iniciando jogo...")
                subprocess.Popen([client_path], cwd=self.app_path)
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
    
    icon_path = os.path.join(get_app_path(), "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    launcher = BaiakZikaLauncherV2()
    launcher.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
