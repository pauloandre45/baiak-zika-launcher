"""
Baiak-Zika Launcher v2
Auto-update system for game client - Modern UI Version
"""

import sys
import os
import json
import zipfile
import shutil
import subprocess
import urllib.request
import ssl
import base64
import webbrowser
import tempfile
import glob
import atexit
from pathlib import Path


def cleanup_mei_folders():
    """
    Limpa pastas temporárias _MEI* do PyInstaller silenciosamente.
    Isso evita o aviso 'Failed to remove temporary directory'.
    """
    try:
        temp_dir = tempfile.gettempdir()
        mei_pattern = os.path.join(temp_dir, '_MEI*')
        
        # Pega o PID atual para não deletar a pasta que estamos usando
        current_mei = getattr(sys, '_MEIPASS', None)
        
        for mei_folder in glob.glob(mei_pattern):
            # Não deleta a pasta que o processo atual está usando
            if current_mei and mei_folder == current_mei:
                continue
            
            try:
                # Tenta remover a pasta (só funciona se não estiver em uso)
                shutil.rmtree(mei_folder, ignore_errors=True)
            except:
                pass  # Ignora erros silenciosamente
    except:
        pass  # Ignora qualquer erro


# Limpa pastas MEI antigas ao iniciar
cleanup_mei_folders()

# Registra limpeza ao sair (silenciosa)
atexit.register(cleanup_mei_folders)


try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QProgressBar, QMessageBox, QFrame,
        QGraphicsDropShadowEffect, QSizePolicy, QSpacerItem
    )
    from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize, QRect
    from PyQt5.QtGui import (QFont, QIcon, QFontDatabase, QLinearGradient, QPalette, 
                             QColor, QPainter, QBrush, QPen, QPixmap, QPainterPath, QImage)
except ImportError:
    print("PyQt5 não encontrado. Instalando...")
    os.system("pip install PyQt5")
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QProgressBar, QMessageBox, QFrame,
        QGraphicsDropShadowEffect, QSizePolicy, QSpacerItem
    )
    from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize, QRect
    from PyQt5.QtGui import (QFont, QIcon, QFontDatabase, QLinearGradient, QPalette, 
                             QColor, QPainter, QBrush, QPen, QPixmap, QPainterPath, QImage)


# ============================================
# CONFIGURAÇÕES DO LAUNCHER
# ============================================
CONFIG = {
    "serverName": "Baiak-Zika",
    "clientExecutable": "Baiak-zika-15/bin/client.exe",  # Caminho do client dentro do ZIP extraído
    "clientFolder": "Baiak-zika-15",  # Pasta do client
    "localConfigFile": "local_config.json",
    "remoteConfigUrl": "https://gist.githubusercontent.com/pauloandre45/e59926d5c0c8cbc9d225e06db7e446ad/raw/SERVIDOR_launcher_config.json",
    "clientDownloadUrl": "https://github.com/pauloandre45/baiak-zika-launcher/releases/download/v1.0.0/Baiak-zika-15.zip",
    "currentVersion": "1.0.0",
    "backupFolders": ["conf", "characterdata", "minimap"],  # Pastas que NÃO são sobrescritas
}

# Estilos globais para MessageBox
MESSAGEBOX_STYLE = """
    QMessageBox {
        background-color: #1a1020;
        border: 2px solid #ffd700;
        border-radius: 10px;
    }
    QMessageBox QLabel {
        color: #fff;
        font-size: 13px;
        padding: 10px;
    }
    QMessageBox QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #884422, stop:1 #552211);
        color: #ffd700;
        border: 1px solid #ffd700;
        border-radius: 5px;
        padding: 8px 25px;
        font-weight: bold;
        min-width: 80px;
    }
    QMessageBox QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #aa5533, stop:1 #773322);
    }
"""


def get_app_path():
    """Retorna o caminho do executável ou script"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def styled_message(parent, title, text, msg_type="info"):
    """Exibe MessageBox estilizada"""
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setStyleSheet(MESSAGEBOX_STYLE)
    
    if msg_type == "error":
        msg.setIcon(QMessageBox.Critical)
    elif msg_type == "warning":
        msg.setIcon(QMessageBox.Warning)
    elif msg_type == "question":
        msg.setIcon(QMessageBox.Question)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        return msg.exec_() == QMessageBox.Yes
    else:
        msg.setIcon(QMessageBox.Information)
    
    msg.exec_()
    return True


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


class BackgroundWidget(QWidget):
    """Widget com background personalizado"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.background_pixmap = None
        self.load_background()
    
    def load_background(self):
        """Carrega imagem de background"""
        # Tenta JPG primeiro (mais leve), depois PNG
        bg_path = os.path.join(get_app_path(), "assets", "background.jpg")
        if not os.path.exists(bg_path):
            bg_path = os.path.join(get_app_path(), "assets", "background.png")
        
        if os.path.exists(bg_path):
            self.background_pixmap = QPixmap(bg_path)
        else:
            # Cria gradient como fallback
            self.background_pixmap = None
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.background_pixmap and not self.background_pixmap.isNull():
            # Desenha background escalado
            scaled = self.background_pixmap.scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            
            # Overlay escuro para melhor legibilidade
            painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        else:
            # Gradient fallback estilo Baiak-Zika (roxo/vermelho/preto)
            gradient = QLinearGradient(0, 0, 0, self.height())
            gradient.setColorAt(0.0, QColor(45, 20, 60))      # Roxo escuro topo
            gradient.setColorAt(0.3, QColor(30, 15, 45))      # Roxo mais escuro
            gradient.setColorAt(0.6, QColor(60, 20, 30))      # Vermelho escuro
            gradient.setColorAt(1.0, QColor(20, 10, 15))      # Quase preto embaixo
            painter.fillRect(self.rect(), gradient)


class StyledButton(QPushButton):
    """Botão estilizado com efeitos"""
    def __init__(self, text, color_type="primary", parent=None):
        super().__init__(text, parent)
        self.color_type = color_type
        self.setup_style()
        self.setCursor(Qt.PointingHandCursor)
        
        # Efeito de sombra
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
    
    def setup_style(self):
        if self.color_type == "primary":
            # Botão JOGAR - Vermelho/Dourado épico
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #ff4444, stop:0.5 #cc2222, stop:1 #991111);
                    color: #ffe4b5;
                    border: 2px solid #ffd700;
                    border-radius: 8px;
                    font-size: 18px;
                    font-weight: bold;
                    padding: 15px 40px;
                    text-shadow: 2px 2px 4px #000;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #ff6666, stop:0.5 #dd3333, stop:1 #bb2222);
                    border: 2px solid #ffdd44;
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #cc2222, stop:0.5 #aa1111, stop:1 #880000);
                }
                QPushButton:disabled {
                    background: #444;
                    border: 2px solid #666;
                    color: #888;
                }
            """)
        elif self.color_type == "secondary":
            # Botão ATUALIZAR - Azul/Roxo
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #6644aa, stop:0.5 #553399, stop:1 #442277);
                    color: #ddd;
                    border: 2px solid #8866cc;
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: bold;
                    padding: 12px 25px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #7755bb, stop:0.5 #6644aa, stop:1 #553388);
                    border: 2px solid #9977dd;
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #553399, stop:0.5 #442277, stop:1 #331166);
                }
                QPushButton:disabled {
                    background: #333;
                    border: 2px solid #555;
                    color: #666;
                }
            """)
        elif self.color_type == "repair":
            # Botão REPARAR - Laranja/Dourado
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #dd8800, stop:0.5 #bb6600, stop:1 #994400);
                    color: #fff;
                    border: 2px solid #ffaa00;
                    border-radius: 8px;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 10px 20px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #ee9900, stop:0.5 #cc7700, stop:1 #aa5500);
                    border: 2px solid #ffbb22;
                }
                QPushButton:disabled {
                    background: #333;
                    border: 2px solid #555;
                    color: #666;
                }
            """)


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
        """Inicializa interface moderna"""
        self.setWindowTitle(f"{CONFIG['serverName']} Launcher")
        self.setFixedSize(700, 450)
        self.setWindowFlags(Qt.FramelessWindowHint)  # Remove borda padrão
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Widget central com background
        self.central = BackgroundWidget()
        self.setCentralWidget(self.central)
        
        # Layout principal
        main_layout = QVBoxLayout(self.central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # ========== BARRA DE TÍTULO CUSTOMIZADA ==========
        title_bar = QWidget()
        title_bar.setFixedHeight(35)
        title_bar.setStyleSheet("background-color: rgba(0, 0, 0, 0.7);")
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(10, 0, 10, 0)
        
        # Título na barra
        window_title = QLabel(f"⚔️ {CONFIG['serverName']} Launcher")
        window_title.setStyleSheet("color: #ffd700; font-size: 12px; font-weight: bold;")
        title_bar_layout.addWidget(window_title)
        
        title_bar_layout.addStretch()
        
        # Botão minimizar
        min_btn = QPushButton("─")
        min_btn.setFixedSize(30, 25)
        min_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #aaa;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.1);
                color: #fff;
            }
        """)
        min_btn.clicked.connect(self.showMinimized)
        title_bar_layout.addWidget(min_btn)
        
        # Botão fechar
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 25)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #aaa;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #cc2222;
                color: #fff;
            }
        """)
        close_btn.clicked.connect(self.close)
        title_bar_layout.addWidget(close_btn)
        
        main_layout.addWidget(title_bar)
        
        # ========== CONTEÚDO PRINCIPAL ==========
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(0)
        content_layout.setContentsMargins(40, 20, 40, 15)
        
        # ========== ÁREA SUPERIOR - Espaço para o logo do background ==========
        content_layout.addStretch(4)
        
        # ========== ÁREA CENTRAL - Botões e Status ==========
        central_area = QWidget()
        central_layout = QVBoxLayout(central_area)
        central_layout.setSpacing(15)
        central_layout.setContentsMargins(0, 0, 0, 0)
        
        # ========== BOTÕES PRINCIPAIS ==========
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setSpacing(20)
        btn_layout.setAlignment(Qt.AlignCenter)
        
        # Botão JOGAR (principal)
        self.play_btn = StyledButton("⚔️  JOGAR", "primary")
        self.play_btn.setFixedSize(160, 50)
        self.play_btn.clicked.connect(self.start_game)
        self.play_btn.setEnabled(False)
        self.play_btn.setVisible(False)
        btn_layout.addWidget(self.play_btn)
        
        # Botão BAIXAR/ATUALIZAR (muda texto conforme situação)
        self.update_btn = StyledButton("⬇️  BAIXAR CLIENTE", "secondary")
        self.update_btn.setFixedSize(200, 50)
        self.update_btn.clicked.connect(self.start_update)
        self.update_btn.setVisible(False)
        btn_layout.addWidget(self.update_btn)
        
        # Botão REPARAR
        self.repair_btn = StyledButton("🔧 REPARAR", "repair")
        self.repair_btn.setFixedSize(130, 45)
        self.repair_btn.clicked.connect(self.start_repair)
        self.repair_btn.setVisible(False)
        btn_layout.addWidget(self.repair_btn)
        
        central_layout.addWidget(btn_container)
        
        # ========== STATUS (ABAIXO DOS BOTÕES) ==========
        status_frame = QFrame()
        status_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0.7);
                border: 1px solid rgba(255, 100, 0, 0.4);
                border-radius: 6px;
            }
        """)
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(20, 8, 20, 8)
        status_layout.setSpacing(6)
        
        # Status label
        self.status_label = QLabel("Verificando...")
        self.status_label.setStyleSheet("""
            color: #ffd700;
            font-size: 12px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        self.status_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.status_label)
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(16)
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ff6600;
                border-radius: 7px;
                background-color: rgba(0, 0, 0, 0.6);
                color: #fff;
                text-align: center;
                font-weight: bold;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ff4400, stop:0.5 #ff6600, stop:1 #ffaa00);
                border-radius: 6px;
            }
        """)
        status_layout.addWidget(self.progress_bar)
        
        central_layout.addWidget(status_frame)
        
        content_layout.addWidget(central_area)
        
        # ========== FOOTER PROFISSIONAL (SEM ESPAÇO) ==========
        footer = QWidget()
        footer.setFixedHeight(65)
        footer.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 0.6);
                border-top: 1px solid rgba(255, 100, 0, 0.4);
            }
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 8, 20, 8)
        
        # Versão (esquerda)
        version_container = QWidget()
        version_container.setStyleSheet("background: transparent; border: none;")
        version_layout = QVBoxLayout(version_container)
        version_layout.setContentsMargins(0, 0, 0, 0)
        version_layout.setSpacing(2)
        
        self.version_label = QLabel(f"Versão {self.local_config.get('version', '1.0.0')}")
        self.version_label.setStyleSheet("color: rgba(255, 215, 0, 0.8); font-size: 11px; font-weight: bold; background: transparent; border: none;")
        version_layout.addWidget(self.version_label)
        
        copyright_label = QLabel("© 2025 Baiak-Zika")
        copyright_label.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 9px; background: transparent; border: none;")
        version_layout.addWidget(copyright_label)
        
        footer_layout.addWidget(version_container)
        
        footer_layout.addStretch()
        
        # Redes Sociais (centro)
        social_container = QWidget()
        social_container.setStyleSheet("background: transparent; border: none;")
        social_layout = QHBoxLayout(social_container)
        social_layout.setContentsMargins(0, 0, 0, 0)
        social_layout.setSpacing(10)
        
        # Label "Comunidade"
        community_label = QLabel("Comunidade:")
        community_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 11px; background: transparent; border: none;")
        social_layout.addWidget(community_label)
        
        # Botão Discord
        discord_btn = QPushButton()
        discord_path = os.path.join(self.app_path, "assets", "discord.png")
        if os.path.exists(discord_path):
            pixmap = QPixmap(discord_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            discord_btn.setIcon(QIcon(pixmap))
            discord_btn.setIconSize(QSize(24, 24))
        else:
            discord_btn.setText("DC")
        discord_btn.setFixedSize(40, 40)
        discord_btn.setCursor(Qt.PointingHandCursor)
        discord_btn.setToolTip("Entrar no Discord")
        discord_btn.setStyleSheet("""
            QPushButton {
                background-color: #5865F2;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #4752C4;
            }
            QPushButton:pressed {
                background-color: #3C45A5;
            }
        """)
        discord_btn.clicked.connect(lambda: self.open_link("https://discord.gg/aRR3GtFS"))
        social_layout.addWidget(discord_btn)
        
        # Botão WhatsApp
        whatsapp_btn = QPushButton()
        whatsapp_path = os.path.join(self.app_path, "assets", "whatsapp.png")
        if os.path.exists(whatsapp_path):
            pixmap = QPixmap(whatsapp_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            whatsapp_btn.setIcon(QIcon(pixmap))
            whatsapp_btn.setIconSize(QSize(24, 24))
        else:
            whatsapp_btn.setText("ZAP")
        whatsapp_btn.setFixedSize(40, 40)
        whatsapp_btn.setCursor(Qt.PointingHandCursor)
        whatsapp_btn.setToolTip("Entrar no WhatsApp")
        whatsapp_btn.setStyleSheet("""
            QPushButton {
                background-color: #25D366;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #1DA851;
            }
            QPushButton:pressed {
                background-color: #128C7E;
            }
        """)
        whatsapp_btn.clicked.connect(lambda: self.open_link("https://chat.whatsapp.com/LCNjzMRyejH4GtVotwpZvF"))
        social_layout.addWidget(whatsapp_btn)
        
        footer_layout.addWidget(social_container)
        
        footer_layout.addStretch()
        
        # Website (direita)
        website_label = QLabel("🌐 www.baiak-zika.com")
        website_label.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 10px; background: transparent; border: none;")
        footer_layout.addWidget(website_label)
        
        content_layout.addWidget(footer)
        
        main_layout.addWidget(content)
        
        # Permitir arrastar a janela
        self.oldPos = None
    
    def mousePressEvent(self, event):
        """Para arrastar a janela"""
        if event.button() == Qt.LeftButton:
            self.oldPos = event.globalPos()
    
    def mouseMoveEvent(self, event):
        """Move a janela ao arrastar"""
        if self.oldPos:
            delta = event.globalPos() - self.oldPos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPos()
    
    def mouseReleaseEvent(self, event):
        """Solta a janela"""
        self.oldPos = None
    
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
            
            # Versões remotas
            remote_client_version = self.remote_config.get("clientVersion", "0.0.0")
            remote_assets_version = self.remote_config.get("assetsVersion", "0.0.0")
            
            # Versões locais
            local_client_version = self.local_config.get("version", "0.0.0")
            local_assets_version = self.local_config.get("assetsVersion", "0.0.0")
            
            # Verificar se o client existe
            client_path = os.path.join(self.app_path, CONFIG["clientExecutable"])
            client_exists = os.path.exists(client_path)
            
            # Flags de atualização
            needs_client_update = self.compare_versions(remote_client_version, local_client_version) > 0
            needs_assets_update = self.compare_versions(remote_assets_version, local_assets_version) > 0
            
            # Guardar tipo de atualização necessária
            self.update_type = None
            
            if not client_exists:
                # Não tem client - mostra BAIXAR CLIENTE
                self.status_label.setText("Cliente não instalado - Clique em BAIXAR")
                self.update_btn.setText("⬇️  BAIXAR CLIENTE")
                self.update_btn.setFixedSize(200, 50)
                self.update_btn.setVisible(True)
                self.update_btn.setEnabled(True)
                self.play_btn.setVisible(False)
                self.repair_btn.setVisible(False)
                self.update_type = "full"
            elif needs_client_update:
                # Cliente precisa atualização completa
                self.status_label.setText(f"Nova versão do cliente: v{remote_client_version}")
                self.update_btn.setText("⬇️  ATUALIZAR")
                self.update_btn.setFixedSize(160, 50)
                self.update_btn.setVisible(True)
                self.update_btn.setEnabled(True)
                self.play_btn.setVisible(True)
                self.play_btn.setEnabled(True)
                self.repair_btn.setVisible(True)
                self.repair_btn.setEnabled(True)
                self.update_type = "full"
            elif needs_assets_update:
                # Só assets precisam atualização (download menor!)
                self.status_label.setText(f"📦 Atualização de assets: v{remote_assets_version}")
                self.update_btn.setText("⬇️  ATUALIZAR ASSETS")
                self.update_btn.setFixedSize(200, 50)
                self.update_btn.setVisible(True)
                self.update_btn.setEnabled(True)
                self.play_btn.setVisible(False)
                self.repair_btn.setVisible(True)
                self.repair_btn.setEnabled(True)
                self.update_type = "assets"
            else:
                # Tudo atualizado - mostra JOGAR e REPARAR
                self.status_label.setText("✅ Cliente atualizado!")
                self.play_btn.setVisible(True)
                self.play_btn.setEnabled(True)
                self.update_btn.setVisible(False)
                self.repair_btn.setVisible(True)
                self.repair_btn.setEnabled(True)
                self.update_type = None
                
        except Exception as e:
            self.status_label.setText(f"Erro ao verificar: {str(e)[:50]}")
            # Verificar se client existe mesmo com erro de conexão
            client_path = os.path.join(self.app_path, CONFIG["clientExecutable"])
            if os.path.exists(client_path):
                self.play_btn.setVisible(True)
                self.play_btn.setEnabled(True)
                self.update_btn.setText("⬇️  ATUALIZAR")
                self.update_btn.setVisible(True)
                self.update_btn.setEnabled(True)
                self.repair_btn.setVisible(True)
                self.repair_btn.setEnabled(True)
                self.update_type = "full"
            else:
                self.play_btn.setVisible(False)
                self.update_btn.setText("⬇️  BAIXAR CLIENTE")
                self.update_btn.setVisible(True)
                self.update_btn.setEnabled(True)
                self.repair_btn.setVisible(False)
                self.update_type = "full"
    
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
        """Inicia download da atualização (completa ou só assets)"""
        self.update_btn.setEnabled(False)
        self.play_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Verificar tipo de atualização
        if self.update_type == "assets":
            # Atualização só dos assets (menor!)
            download_url = self.remote_config.get("assetsDownloadUrl", "")
            if not download_url:
                styled_message(self, "❌ Erro", "URL de assets não configurada no servidor.", "error")
                self.update_btn.setEnabled(True)
                self.progress_bar.setVisible(False)
                return
            self.is_assets_update = True
            self.status_label.setText("Baixando assets...")
        else:
            # Atualização completa do client
            download_url = self.remote_config.get("newClientUrl") or \
                           self.remote_config.get("clientDownloadUrl") or \
                           CONFIG["clientDownloadUrl"]
            self.is_assets_update = False
            self.status_label.setText("Baixando cliente...")
        
        # Caminho para salvar
        zip_path = os.path.join(self.app_path, "update.zip")
        
        # Criar thread de download
        self.download_thread = DownloadWorker(download_url, zip_path)
        self.download_thread.progress.connect(self.on_download_progress)
        self.download_thread.finished.connect(self.on_download_complete)
        self.download_thread.start()
    
    def start_repair(self):
        """Força o download do client (reparar arquivos)"""
        if styled_message(
            self, 
            "🔧 Reparar Cliente",
            "Isso vai baixar novamente todos os arquivos do cliente.\n"
            "Suas configurações serão mantidas.\n\n"
            "Deseja continuar?",
            "question"
        ):
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
            styled_message(self, "❌ Erro no Download", message, "error")
    
    def extract_update(self):
        """Extrai arquivos do update"""
        try:
            zip_path = os.path.join(self.app_path, "update.zip")
            client_folder = os.path.join(self.app_path, CONFIG.get("clientFolder", "Baiak-zika-15"))
            
            if getattr(self, 'is_assets_update', False):
                # ========== ATUALIZAÇÃO SÓ DOS ASSETS ==========
                self.status_label.setText("Extraindo assets...")
                
                # Extrai direto - assets não têm configurações do player
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # Verificar estrutura do ZIP
                    first_entry = zip_ref.namelist()[0] if zip_ref.namelist() else ""
                    
                    # Se o ZIP contém pasta assets/ na raiz
                    if first_entry.startswith("assets/") or first_entry == "assets":
                        # Extrai para a pasta do client
                        zip_ref.extractall(client_folder)
                    else:
                        # ZIP contém só os arquivos - extrai para assets/
                        assets_path = os.path.join(client_folder, "assets")
                        zip_ref.extractall(assets_path)
                
                # Remove o ZIP
                os.remove(zip_path)
                
                # Atualiza versão dos assets local com a versão CORRETA do servidor
                if self.remote_config:
                    self.local_config["assetsVersion"] = self.remote_config.get("assetsVersion", "1.0.0")
                    self.save_local_config()
                
                self.status_label.setText("✅ Assets atualizados!")
                self.progress_bar.setVisible(False)
                self.play_btn.setVisible(True)
                self.play_btn.setEnabled(True)
                self.update_btn.setVisible(False)
                
                styled_message(self, "✅ Sucesso", "Assets atualizados com sucesso!\n\nNenhuma configuração foi alterada.", "info")
                
            else:
                # ========== ATUALIZAÇÃO COMPLETA DO CLIENT ==========
                # Backup das pastas importantes (conf, characterdata, minimap)
                self.status_label.setText("Fazendo backup...")
                backup_list = []
                for folder in CONFIG["backupFolders"]:
                    folder_path = os.path.join(client_folder, folder)
                    backup_path = os.path.join(self.app_path, f"{folder}_backup")
                    if os.path.exists(folder_path):
                        if os.path.exists(backup_path):
                            shutil.rmtree(backup_path)
                        shutil.copytree(folder_path, backup_path)
                        backup_list.append(folder)
                
                # Extrai o ZIP
                self.status_label.setText("Extraindo arquivos...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(self.app_path)
                
                # Restaura backups
                self.status_label.setText("Restaurando configurações...")
                for folder in backup_list:
                    backup_path = os.path.join(self.app_path, f"{folder}_backup")
                    folder_path = os.path.join(client_folder, folder)
                    if os.path.exists(backup_path):
                        if os.path.exists(folder_path):
                            shutil.rmtree(folder_path)
                        shutil.move(backup_path, folder_path)
                
                # Remove o ZIP
                os.remove(zip_path)
                
                # Atualiza versões locais
                if self.remote_config:
                    self.local_config["version"] = self.remote_config.get("clientVersion", "1.0.0")
                    # Assets do ZIP são versão 1.0.0 (base) - verificação automática logo abaixo
                    self.local_config["assetsVersion"] = "1.0.0"
                    self.save_local_config()
                    self.version_label.setText(f"Versão {self.local_config['version']}")
                
                # Verificar se precisa baixar assets atualizados
                remote_assets = self.remote_config.get("assetsVersion", "1.0.0") if self.remote_config else "1.0.0"
                if self.compare_versions(remote_assets, "1.0.0") > 0:
                    # Assets do servidor são mais novos que o ZIP - baixar automaticamente
                    self.status_label.setText("📦 Baixando assets atualizados...")
                    styled_message(self, "✅ Cliente instalado!", "Cliente instalado!\n\nAgora vamos baixar os assets atualizados...", "info")
                    self.update_type = "assets"
                    QTimer.singleShot(500, self.start_update)
                else:
                    self.status_label.setText("✅ Atualização concluída!")
                    self.progress_bar.setVisible(False)
                    self.play_btn.setVisible(True)
                    self.play_btn.setEnabled(True)
                    self.update_btn.setVisible(False)
                    styled_message(self, "✅ Sucesso", "Cliente atualizado com sucesso!\n\nSuas configurações foram preservadas.", "info")
            
        except Exception as e:
            self.status_label.setText(f"Erro na extração: {str(e)}")
            styled_message(self, "❌ Erro na Extração", f"Erro ao extrair arquivos:\n\n{str(e)}", "error")
            self.update_btn.setEnabled(True)
            self.play_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
    
    def start_game(self):
        """Inicia o cliente do jogo"""
        client_path = os.path.join(self.app_path, CONFIG["clientExecutable"])
        
        if os.path.exists(client_path):
            try:
                self.status_label.setText("Iniciando jogo...")
                
                # Usa ShellExecute no Windows para evitar WinError 740
                # Isso permite executar o programa sem exigir elevação do launcher
                if sys.platform == 'win32':
                    import ctypes
                    # Obtém o diretório do client.exe para usar como working directory
                    client_dir = os.path.dirname(client_path)
                    if not client_dir:
                        client_dir = self.app_path
                    
                    # ShellExecuteW com 'open' não força elevação
                    # Retorna > 32 em caso de sucesso
                    result = ctypes.windll.shell32.ShellExecuteW(
                        None,           # hwnd - handle da janela pai
                        "open",         # lpOperation - 'open' executa sem forçar admin
                        client_path,    # lpFile - arquivo a executar
                        None,           # lpParameters - argumentos
                        client_dir,     # lpDirectory - working directory
                        1               # nShowCmd - SW_SHOWNORMAL
                    )
                    
                    if result > 32:
                        # Sucesso - fecha o launcher
                        QTimer.singleShot(1000, QApplication.quit)
                    else:
                        # Falhou - mostra erro específico
                        error_codes = {
                            0: "Sistema sem memória",
                            2: "Arquivo não encontrado",
                            3: "Caminho não encontrado", 
                            5: "Acesso negado",
                            8: "Memória insuficiente",
                            11: "Formato EXE inválido",
                            26: "Erro de compartilhamento",
                            27: "Associação de arquivo incompleta",
                            28: "Timeout na operação",
                            29: "Falha na DDE",
                            30: "Transação DDE cancelada",
                            31: "Sem associação de arquivo",
                            32: "DLL não encontrada"
                        }
                        error_msg = error_codes.get(result, f"Código de erro: {result}")
                        raise Exception(f"ShellExecute falhou: {error_msg}")
                else:
                    # Linux/Mac - usa subprocess normal
                    subprocess.Popen([client_path], cwd=self.app_path)
                    QTimer.singleShot(1000, QApplication.quit)
                    
            except Exception as e:
                styled_message(self, "❌ Erro", f"Erro ao iniciar o jogo:\n\n{str(e)}", "error")
        else:
            styled_message(
                self, 
                "⚠️ Cliente não encontrado",
                f"O arquivo do jogo não foi encontrado.\n\n"
                "Clique em ATUALIZAR para baixar o cliente.",
                "warning"
            )
            self.update_btn.setVisible(True)
            self.update_btn.setEnabled(True)
    
    def open_link(self, url):
        """Abre um link no navegador padrão"""
        try:
            webbrowser.open(url)
        except Exception as e:
            styled_message(self, "❌ Erro", f"Erro ao abrir link:\n\n{str(e)}", "error")
    
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
