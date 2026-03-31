import sys
import os
import shutil
import time
import re
import json
import urllib.request
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QComboBox, 
                             QTextEdit, QFrame, QGridLayout, QSizePolicy, QFileDialog,
                             QStackedWidget, QScrollArea, QListWidget, QListWidgetItem, QListView,
                             QProgressBar, QMessageBox, QLineEdit, QDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon, QColor, QPalette, QCursor
import qtawesome as qta

from core.image_manager import ImageManager
from core.utils import ensure_dir
from core.updater import UpdateCheckerThread, UpdateDownloaderThread, apply_update, CURRENT_VERSION
from core.analytics import AnalyticsManager, log_ga_event

# --- STYLING CONSTANTS ---
BG_COLOR = "#0b0c10"
SIDEBAR_COLOR = "#0b0c10"
CARD_BG = "#131418"
CARD_BORDER = "#1f2024"
TEXT_PRIMARY = "#f3f4f6"
TEXT_SECONDARY = "#9ca3af"

# REPLACE THIS WITH YOUR ACTUAL GITHUB RAW URL LATER
HELP_DOC_URL = "https://raw.githubusercontent.com/username/repo/main/bootly_help.json"

class SidebarBtn(QPushButton):
    def __init__(self, icon_name, text, active=False):
        super().__init__(text)
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.icon_name = icon_name
        self.active = active
        self._update_style()

    def set_active(self, active):
        self.active = active
        self._update_style()

    def _update_style(self):
        icon_color = '#60a5fa' if self.active else TEXT_SECONDARY
        self.setIcon(qta.icon(self.icon_name, color=icon_color))
        self.setIconSize(QSize(20, 20))
        
        if self.active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: #0b1f3b;
                    color: #60a5fa;
                    text-align: left;
                    padding-left: 15px;
                    border: none;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 10pt;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {TEXT_SECONDARY};
                    text-align: left;
                    padding-left: 15px;
                    border: none;
                    border-radius: 8px;
                    font-weight: 500;
                    font-size: 10pt;
                }}
                QPushButton:hover {{
                    background-color: #1f2024;
                    color: {TEXT_PRIMARY};
                }}
            """)

class ActionBtn(QPushButton):
    def __init__(self, icon_name, title, subtitle, style_type="blue"):
        super().__init__()
        self.setFixedSize(130, 90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.style_type = style_type
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(4)
        
        self.icon_lbl = QLabel()
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setStyleSheet("background: transparent;")
        
        icon_color = "white" if style_type != "outline" else TEXT_SECONDARY
        pm = qta.icon(icon_name, color=icon_color).pixmap(QSize(32, 32))
        self.icon_lbl.setPixmap(pm)
        
        self.t = QLabel(title)
        self.t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if style_type != "outline":
            self.t.setStyleSheet("font-size: 11pt; font-weight: bold; background: transparent; color: white;")
        else:
            self.t.setStyleSheet(f"font-size: 11pt; font-weight: bold; background: transparent; color: {TEXT_SECONDARY};")
        
        self.sub = QLabel(subtitle)
        self.sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if style_type != "outline":
            self.sub.setStyleSheet("font-size: 8pt; background: transparent; color: rgba(255,255,255,0.7);")
        else:
            self.sub.setStyleSheet(f"font-size: 8pt; background: transparent; color: {TEXT_SECONDARY};")
            
        layout.addWidget(self.icon_lbl)
        layout.addWidget(self.t)
        layout.addWidget(self.sub)

        self._update_state_style()

    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        self._update_state_style()

    def _update_state_style(self):
        if not self.isEnabled():
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: #1f2937;
                    border: none;
                    border-radius: 8px;
                    color: #4b5563;
                }}
            """)
            self.t.setStyleSheet("font-size: 11pt; font-weight: bold; background: transparent; color: #6b7280;")
            self.sub.setStyleSheet("font-size: 8pt; background: transparent; color: #4b5563;")
            return

        if self.style_type == "blue":
            self.setStyleSheet("""
                QPushButton {
                    background-color: #1e88e5;
                    border: none;
                    border-radius: 8px;
                    color: white;
                }
                QPushButton:hover { background-color: #2196f3; }
            """)
            self.t.setStyleSheet("font-size: 11pt; font-weight: bold; background: transparent; color: white;")
            self.sub.setStyleSheet("font-size: 8pt; background: transparent; color: rgba(255,255,255,0.7);")
        elif self.style_type == "light_blue":
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #42a5f5, stop:1 #1e88e5);
                    border: none;
                    border-radius: 8px;
                    color: white;
                }
                QPushButton:hover { background: #64b5f6; }
            """)
            self.t.setStyleSheet("font-size: 11pt; font-weight: bold; background: transparent; color: white;")
            self.sub.setStyleSheet("font-size: 8pt; background: transparent; color: rgba(255,255,255,0.7);")
        elif self.style_type == "outline":
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: 1px solid {CARD_BORDER};
                    border-radius: 8px;
                    color: {TEXT_SECONDARY};
                }}
                QPushButton:hover {{ background-color: {CARD_BORDER}; color: {TEXT_PRIMARY}; }}
            """)
            self.t.setStyleSheet(f"font-size: 11pt; font-weight: bold; background: transparent; color: {TEXT_SECONDARY};")
            self.sub.setStyleSheet(f"font-size: 8pt; background: transparent; color: {TEXT_SECONDARY};")

class ConsoleWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #10151c;
                border: 1px solid {CARD_BORDER};
                border-radius: 12px;
            }}
        """)
        self.setFixedHeight(180)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top bar
        top_bar = QFrame()
        top_bar.setFixedHeight(30)
        top_bar.setStyleSheet("background: transparent; border-bottom: none;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(15, 0, 15, 0)
        
        # Mac OS dots
        dots_layout = QHBoxLayout()
        dots_layout.setSpacing(6)
        for color in ["#ff5f56", "#ffbd2e", "#27c93f"]:
            dot = QFrame()
            dot.setFixedSize(12, 12)
            dot.setStyleSheet(f"background-color: {color}; border-radius: 6px; border: none;")
            dots_layout.addWidget(dot)
        top_layout.addLayout(dots_layout)
        top_layout.addStretch()
        
        close_btn = QLabel("✕")
        close_btn.setStyleSheet("color: #666; font-size: 10pt; border: none; background: transparent;")
        top_layout.addWidget(close_btn)
        
        layout.addWidget(top_bar)

        self.progress = QProgressBar()
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar { background: #131418; border: none; }
            QProgressBar::chunk { background-color: #60a5fa; }
        """)
        self.progress.hide()
        layout.addWidget(self.progress)

        # Log Text Area
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background: transparent;
                border: none;
                color: #e5e7eb;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
                padding: 10px 15px;
            }
        """)
        layout.addWidget(self.text_edit)

    def log(self, text, tag="INFO"):
        color = "#60a5fa"
        if tag == "SUCCESS": color = "#4ade80"
        elif tag == "WARN": color = "#fbbf24"
        elif tag == "UNPACKING" or tag == "REPACKING": color = "#818cf8"
        elif tag == "ERROR": color = "#f87171"

        html = f"<span style='color: {color}; font-weight: bold;'>[{tag}]</span> <span style='color: #e5e7eb;'>{text}</span>"
        self.text_edit.append(html)
        self.text_edit.verticalScrollBar().setValue(self.text_edit.verticalScrollBar().maximum())

    def start_progress(self):
        self.progress.show()
        self.progress.setRange(0, 0)

    def stop_progress(self):
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.progress.hide()

class WorkerThread(QThread):
    finished = pyqtSignal(bool, str)
    log_signal = pyqtSignal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.kwargs['callback'] = self.emit_log

    def emit_log(self, msg):
        self.log_signal.emit(msg)

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(True, str(result))
        except Exception as e:
            self.finished.emit(False, str(e))

class KBFetcherThread(QThread):
    finished = pyqtSignal(bool, object)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            req = urllib.request.Request(self.url, headers={'User-Agent': 'BootlyApp/1.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                self.finished.emit(True, data)
        except Exception as e:
            self.finished.emit(False, str(e))

class ThumbnailCard(QFrame):
    clicked = pyqtSignal(str, str)

    def __init__(self, name, type_):
        super().__init__()
        self.name = name
        self.type_ = type_
        self.setFixedSize(160, 160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {CARD_BG};
                border: 1px solid {CARD_BORDER};
                border-radius: 8px;
            }}
            QFrame:hover {{
                border: 1px solid #3b82f6;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon = QLabel()
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pm = qta.icon("fa5s.folder-open" if type_ == "PROJECT" else "fa5s.file-image", 
                      color="#4ade80" if type_ == "PROJECT" else "#60a5fa").pixmap(QSize(48, 48))
        icon.setPixmap(pm)
        icon.setStyleSheet("background: transparent; border: none;")
        
        lbl_name = QLabel(name)
        lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_name.setWordWrap(True)
        lbl_name.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: bold; background: transparent; border: none;")
        
        lbl_type = QLabel("Project Folder" if type_ == "PROJECT" else "Raw Image")
        lbl_type.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_type.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 8pt; background: transparent; border: none;")
        
        layout.addStretch()
        layout.addWidget(icon)
        layout.addWidget(lbl_name)
        layout.addWidget(lbl_type)
        layout.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.name, self.type_)

class ArticleCard(QFrame):
    def __init__(self, question, answer, tags, highlight_term=""):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {CARD_BG};
                border: 1px solid {CARD_BORDER};
                border-radius: 12px;
                margin-top: 10px;
                margin-bottom: 5px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(12)
        
        def highlight(text, term):
            if not term: return text
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            return pattern.sub(lambda m: f"<span style='background-color: #3b82f6; color: white; padding: 2px 4px; border-radius: 4px;'>{m.group(0)}</span>", text)

        # Header Area
        header_lay = QHBoxLayout()
        header_lay.setSpacing(10)
        
        q_ico = QLabel()
        q_ico.setPixmap(qta.icon('fa5s.question-circle', color='#3b82f6').pixmap(QSize(24, 24)))
        q_ico.setStyleSheet("background: transparent; border: none;")
        header_lay.addWidget(q_ico)
        
        lbl_q = QLabel(highlight(question, highlight_term))
        lbl_q.setTextFormat(Qt.TextFormat.RichText)
        lbl_q.setWordWrap(True)
        lbl_q.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14pt; font-weight: bold; border: none; background: transparent;")
        header_lay.addWidget(lbl_q, stretch=1)
        layout.addLayout(header_lay)
        
        # Tags Area
        if tags:
            tags_lay = QHBoxLayout()
            tags_lay.setContentsMargins(34, 0, 0, 0) # align under text
            tags_lay.setSpacing(8)
            for t in tags:
                lbl_t = QLabel(t)
                lbl_t.setStyleSheet("background-color: #1f2937; color: #9ca3af; padding: 4px 10px; border-radius: 6px; font-size: 8pt; border: none;")
                tags_lay.addWidget(lbl_t)
            tags_lay.addStretch()
            layout.addLayout(tags_lay)
            
        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background-color: {CARD_BORDER}; border: none; margin-top: 8px; margin-bottom: 8px;")
        layout.addWidget(div)
        
        # Answer Area
        answer_formatted = answer.replace('\n', '<br>')
        lbl_a = QLabel(highlight(answer_formatted, highlight_term))
        lbl_a.setTextFormat(Qt.TextFormat.RichText)
        lbl_a.setWordWrap(True)
        lbl_a.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        lbl_a.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl_a.setStyleSheet(f"color: #d1d5db; font-size: 11pt; border: none; background: transparent; line-height: 180%; margin-top: 5px;")
        layout.addWidget(lbl_a)

import urllib.parse
class SubscribeWorker(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, email, name):
        super().__init__()
        self.email = email
        self.name = name

    def run(self):
        try:
            url = "https://mailer.harislab.tech/api/subscribe/submit?token=92e12fff7101"
            attribs_json = json.dumps({"name": self.name})
            
            data = urllib.parse.urlencode({
                "email": self.email,
                "attribs": attribs_json
            }).encode('utf-8')
            
            req = urllib.request.Request(url, data=data, method="POST")
            with urllib.request.urlopen(req, timeout=10) as response:
                self.finished.emit(True, "Success")
        except Exception as e:
            self.finished.emit(False, str(e))

class SubscribeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Subscribe to Updates")
        self.setFixedSize(450, 320)
        self.setStyleSheet(f"background-color: {BG_COLOR};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        lbl_title = QLabel("Subscribe via Email 📬")
        lbl_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16pt; font-weight: bold;")
        layout.addWidget(lbl_title)
        
        lbl_sub = QLabel("Get notified instantly about fresh Bootly software updates over email!")
        lbl_sub.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10pt; margin-bottom: 5px;")
        layout.addWidget(lbl_sub)
        
        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("Please enter your name")
        self.inp_name.setStyleSheet(f"QLineEdit {{ background-color: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: 6px; padding: 12px; color: {TEXT_PRIMARY}; font-size: 11pt; }}")
        layout.addWidget(self.inp_name)
        
        self.inp_email = QLineEdit()
        self.inp_email.setPlaceholderText("Please enter your email address")
        self.inp_email.setStyleSheet(f"QLineEdit {{ background-color: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: 6px; padding: 12px; color: {TEXT_PRIMARY}; font-size: 11pt; }}")
        layout.addWidget(self.inp_email)
        
        layout.addStretch()
        
        self.btn_sub = QPushButton("Subscribe Now")
        self.btn_sub.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sub.setStyleSheet("background-color: #4ade80; color: #064e3b; padding: 14px; border-radius: 6px; font-weight: bold; font-size: 11pt; border: none;")
        self.btn_sub.clicked.connect(self.handle_submit)
        layout.addWidget(self.btn_sub)

    def handle_submit(self):
        name = self.inp_name.text().strip()
        email = self.inp_email.text().strip()
        
        if not name or not email:
            QMessageBox.warning(self, "Invalid Input", "Please provide both your name and email address.")
            return
            
        if "@" not in email or "." not in email:
            QMessageBox.warning(self, "Invalid Input", "Please provide a valid email address.")
            return
            
        self.btn_sub.setText("Subscribing...")
        self.btn_sub.setEnabled(False)
        self.inp_name.setEnabled(False)
        self.inp_email.setEnabled(False)
        
        self.worker = SubscribeWorker(email, name)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()
        
    def on_finished(self, success, result):
        if success:
            QMessageBox.information(
                self, 
                "Success!", 
                "PLEASE CHECK YOUR EMAIL TO CONFIRM SUBSCRIPTION.\nNOT RECEIVING MAIL? CHECK YOUR SPAM FOLDER."
            )
            self.accept()
        else:
            QMessageBox.critical(self, "Subscription Failed", f"Could not bind your subscription to our mailing list:\n{result}")
            self.btn_sub.setText("Subscribe Now")
            self.btn_sub.setEnabled(True)
            self.inp_name.setEnabled(True)
            self.inp_email.setEnabled(True)

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Bootly")
        self.setFixedSize(400, 260)
        self.setStyleSheet(f"background-color: {BG_COLOR};")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)
        
        logo = QLabel()
        logo.setPixmap(qta.icon('fa5s.fire', color='#3b82f6').pixmap(QSize(48, 48)))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)
        
        lbl_title = QLabel(f"Bootly v{CURRENT_VERSION}")
        lbl_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16pt; font-weight: bold;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)
        
        lbl_dev = QLabel("Developed by Haris")
        lbl_dev.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11pt;")
        lbl_dev.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_dev)
        
        lbl_os = QLabel("An open-source project. View source on GitHub:")
        lbl_os.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10pt; margin-top: 15px;")
        lbl_os.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_os)
        
        lbl_link = QLabel("<a href='https://github.com/Haris16-code/Bootly' style='color: #60a5fa; text-decoration: none;'>github.com/Haris16-code/Bootly</a>")
        lbl_link.setOpenExternalLinks(True)
        lbl_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_link.setStyleSheet("font-size: 11pt; font-weight: bold;")
        layout.addWidget(lbl_link)

        layout.addStretch()

class UpdateDialog(QDialog):
    def __init__(self, data, parent_app):
        super().__init__(parent_app)
        self.data = data
        self.app = parent_app
        self.setWindowTitle("Update Available")
        self.setFixedSize(500, 350)
        self.setStyleSheet(f"background-color: {BG_COLOR};")
        
        layout = QVBoxLayout(self)
        
        lbl_title = QLabel(f"Version {data.get('latest_version')} is available!")
        lbl_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16pt; font-weight: bold;")
        layout.addWidget(lbl_title)
        
        lbl_sub = QLabel(f"You are currently running Bootly v{CURRENT_VERSION}.")
        lbl_sub.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10pt; margin-bottom: 10px;")
        layout.addWidget(lbl_sub)
        
        lbl_feat = QLabel("✨ What's New:")
        lbl_feat.setStyleSheet(f"color: #4ade80; font-size: 11pt; font-weight: bold; margin-bottom: 2px;")
        layout.addWidget(lbl_feat)
        
        notes = QTextEdit()
        notes.setReadOnly(True)
        notes_text = data.get("release_notes", "No release notes available.")
        # Attempt to render as HTML if they used bullet points, otherwise plain text falls back cleanly
        notes.setHtml(notes_text.replace('\n', '<br>') if '<' not in notes_text else notes_text)
        notes.setStyleSheet(f"background-color: {CARD_BG}; color: {TEXT_PRIMARY}; border: 1px solid {CARD_BORDER}; border-radius: 6px; padding: 10px; font-size: 10pt;")
        layout.addWidget(notes)
        
        self.progress = QProgressBar()
        self.progress.setStyleSheet("QProgressBar { background: #131418; border: none; } QProgressBar::chunk { background-color: #3b82f6; }")
        self.progress.hide()
        layout.addWidget(self.progress)
        
        btn_lay = QHBoxLayout()
        self.btn_install = QPushButton("Download && Install")
        self.btn_install.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_install.setStyleSheet("background-color: #3b82f6; color: white; padding: 10px 20px; border-radius: 6px; font-weight: bold; border: none;")
        self.btn_install.clicked.connect(self.start_download)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet(f"background-color: transparent; border: 1px solid {CARD_BORDER}; color: {TEXT_SECONDARY}; padding: 10px 20px; border-radius: 6px; font-weight: bold;")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_lay.addStretch()
        btn_lay.addWidget(self.btn_cancel)
        btn_lay.addWidget(self.btn_install)
        layout.addLayout(btn_lay)

    def start_download(self):
        self.btn_install.setText("Downloading...")
        self.btn_install.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.progress.show()
        self.progress.setValue(0)
        
        self.thread = UpdateDownloaderThread(self.data, self.app.base_path)
        self.thread.progress.connect(self.progress.setValue)
        self.thread.finished.connect(self.on_downloaded)
        self.thread.start()

    def on_downloaded(self, success, result):
        if success:
            log_ga_event("update_downloaded")
            apply_update(result, self.app.base_path)
        else:
            log_ga_event("error_occurred", {"error_type": "update_failed"})
            QMessageBox.critical(self, "Update Failed", f"Failed to download update:\n{result}")
            self.reject()

class BootlyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        if getattr(sys, 'frozen', False):
            self.base_path = os.path.dirname(sys.executable)
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))
        
        self.image_manager = ImageManager(self.base_path)
        AnalyticsManager.init(self.base_path)
        log_ga_event("app_launch")
        
        self.current_item = None
        self.current_type = None 
        self.loaded_articles = []
        self.init_ui()
        self.refresh_state()
        self.check_for_updates()

    def show_subscribe(self):
        log_ga_event("subscribe_click")
        SubscribeDialog(self).exec()

    def show_about(self):
        log_ga_event("about_click")
        AboutDialog(self).exec()

    def check_for_updates(self, manual=False):
        log_ga_event("update_check", {"manual": manual})
        self._manual_update = manual
        self.upd_thread = UpdateCheckerThread()
        self.upd_thread.finished.connect(self.on_update_checked)
        self.upd_thread.start()

    def on_update_checked(self, success, data, msg):
        if success:
            dialog = UpdateDialog(data, self)
            dialog.exec()
        elif getattr(self, '_manual_update', False):
            QMessageBox.information(self, "Up to Date", f"You are running the latest version of Bootly (v{CURRENT_VERSION}).\n\n{msg}")

    def init_ui(self):
        self.setWindowTitle("Bootly Dashboard")
        self.resize(900, 650)
        self.setStyleSheet(f"QMainWindow {{ background-color: {BG_COLOR}; }}")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)

        # --- SIDEBAR ---
        sidebar = QFrame()
        sidebar.setFixedWidth(180)
        sidebar.setStyleSheet("background-color: transparent; border: none;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(5, 5, 5, 5)
        sidebar_layout.setSpacing(8)

        brand_layout = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(qta.icon('fa5s.fire', color='#3b82f6').pixmap(QSize(28, 28)))
        title = QLabel("Bootly")
        title.setStyleSheet(f"font-size: 16pt; font-weight: 800; color: {TEXT_PRIMARY};")
        
        brand_layout.addWidget(logo)
        brand_layout.addWidget(title)
        brand_layout.addStretch()
        sidebar_layout.addLayout(brand_layout)
        sidebar_layout.addSpacing(20)

        self.btn_dash = SidebarBtn("fa5s.home", "Dashboard", True)
        self.btn_explore = SidebarBtn("fa5s.layer-group", "Workspace")
        self.btn_help = SidebarBtn("fa5s.book", "Knowledge Base") 
        self.btn_update = SidebarBtn("fa5s.arrow-alt-circle-up", "Check Updates") 
        self.btn_subscribe = SidebarBtn("fa5s.envelope", "Email Updates") 
        self.btn_about = SidebarBtn("fa5s.info-circle", "About")
        
        self.btn_dash.clicked.connect(lambda: self.switch_view(0))
        self.btn_explore.clicked.connect(lambda: self.switch_view(1))
        self.btn_help.clicked.connect(lambda: self.switch_view(2))
        self.btn_update.clicked.connect(lambda: self.check_for_updates(manual=True))
        self.btn_subscribe.clicked.connect(self.show_subscribe)
        self.btn_about.clicked.connect(self.show_about)

        sidebar_layout.addWidget(self.btn_dash)
        sidebar_layout.addWidget(self.btn_explore)
        sidebar_layout.addWidget(self.btn_help)
        
        # Push update to bottom
        sidebar_layout.addStretch()
        
        div = QFrame(); div.setFixedHeight(1); div.setStyleSheet(f"background-color: {CARD_BORDER}; border: none; margin-bottom: 5px;")
        sidebar_layout.addWidget(div)
        
        sidebar_layout.addWidget(self.btn_update)
        sidebar_layout.addWidget(self.btn_subscribe)
        sidebar_layout.addWidget(self.btn_about)
        main_layout.addWidget(sidebar)

        # --- STACKED WIDGET ---
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # PAGE 0: DASHBOARD
        dash_page = QWidget()
        content_layout = QVBoxLayout(dash_page)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(15)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(15)

        info_card = QFrame()
        info_card.setStyleSheet(f"background-color: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: 12px;")
        info_card_layout = QVBoxLayout(info_card)
        info_card_layout.setContentsMargins(20, 20, 20, 20)
        
        card_header = QHBoxLayout()
        self.icon_box = QLabel("B")
        self.icon_box.setFixedSize(48, 48)
        self.icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_box.setStyleSheet("background-color: #374151; color: white; font-size: 20pt; font-weight: bold; border-radius: 8px;")
        card_header.addWidget(self.icon_box)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        
        self.lbl_img_name = QLabel("No Selection")
        self.lbl_img_name.setStyleSheet(f"font-size: 12pt; font-weight: bold; color: {TEXT_PRIMARY};")
        self.lbl_img_subtitle = QLabel("0.0 MB · Unknown")
        self.lbl_img_subtitle.setStyleSheet(f"font-size: 9pt; color: {TEXT_SECONDARY};")
        self.lbl_img_date = QLabel("Location: —")
        self.lbl_img_date.setStyleSheet(f"font-size: 9pt; color: {TEXT_SECONDARY};")
        
        title_layout.addWidget(self.lbl_img_name)
        title_layout.addWidget(self.lbl_img_subtitle)
        title_layout.addWidget(self.lbl_img_date)
        card_header.addLayout(title_layout)
        card_header.addStretch()
        
        self.btn_open_folder = QPushButton()
        self.btn_open_folder.setIcon(qta.icon('fa5s.folder-open', color='#4ade80'))
        self.btn_open_folder.setToolTip("Open Project Folder in Explorer")
        self.btn_open_folder.setFixedSize(32, 32)
        self.btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_folder.setStyleSheet(f"background: #1f2937; border-radius: 16px; border: 1px solid {CARD_BORDER};")
        self.btn_open_folder.clicked.connect(self.handle_open_folder)
        card_header.addWidget(self.btn_open_folder)
        info_card_layout.addLayout(card_header)

        div = QFrame(); div.setFixedHeight(1); div.setStyleSheet(f"background-color: {CARD_BORDER}; margin-top: 10px; margin-bottom: 10px;")
        info_card_layout.addWidget(div)

        lbl_meta = QLabel("Image metadata")
        lbl_meta.setStyleSheet(f"font-size: 9pt; font-weight: bold; color: {TEXT_PRIMARY};")
        info_card_layout.addWidget(lbl_meta)

        self.grid = QGridLayout()
        self.grid.setSpacing(8)
        
        self.lbls_meta = {"Size": QLabel("—"), "Header": QLabel("—"), "Format": QLabel("—"), "Version": QLabel("—"), "Status": QLabel("—")}
        meta_items = [("Size:", "Size", "Header:", "Header"), ("Format:", "Format", "OS Version:", "Version"), ("Status:", "Status", "—", "—")]
        
        for row, item in enumerate(meta_items):
            k1, v1_key, k2, v2_key = item
            def style(w, is_val=False):
                if isinstance(w, QLabel): w.setStyleSheet(f"color: {TEXT_PRIMARY if is_val else TEXT_SECONDARY}; font-size: 9pt;")
            l1 = QLabel(k1); l2 = QLabel(k2); style(l1); style(l2)
            v1_widget = self.lbls_meta.get(v1_key, QLabel("—")); v2_widget = self.lbls_meta.get(v2_key, QLabel(""))
            style(v1_widget, True); style(v2_widget, True)
            self.grid.addWidget(l1, row, 0); self.grid.addWidget(v1_widget, row, 1)
            self.grid.addWidget(l2, row, 2); self.grid.addWidget(v2_widget, row, 3)
            
        info_card_layout.addLayout(self.grid)

        info_card_layout.addSpacing(10)
        lbl_sb = QLabel("Structure bar")
        lbl_sb.setStyleSheet(f"font-size: 9pt; font-weight: bold; color: {TEXT_PRIMARY}; margin-bottom: 5px;")
        info_card_layout.addWidget(lbl_sb)
        
        self.bar_layout = QHBoxLayout()
        self.bar_layout.setSpacing(2)
        info_card_layout.addLayout(self.bar_layout)
        top_layout.addWidget(info_card, stretch=6)

        # IMAGE STRUCTURE CARD
        struct_card = QFrame()
        struct_card.setStyleSheet(f"background-color: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: 12px;")
        self.struct_layout = QVBoxLayout(struct_card)
        self.struct_layout.setContentsMargins(15, 20, 15, 15)
        
        lbl_str = QLabel("Image Structure")
        lbl_str.setStyleSheet(f"font-size: 10pt; font-weight: bold; color: {TEXT_PRIMARY}; margin-bottom: 5px;")
        self.struct_layout.addWidget(lbl_str)

        self.struct_rows = {}
        for k in ["Total Image", "Kernel", "Ramdisk", "Second", "DTB"]:
            row = QFrame(); row.setFixedHeight(32)
            row.setStyleSheet("background-color: #1a1e24; border-radius: 4px; margin-bottom: 2px;")
            r_lay = QHBoxLayout(row); r_lay.setContentsMargins(10, 0, 10, 0)
            l_k = QLabel(k); l_k.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 9pt; background: transparent;")
            l_v = QLabel("0.0 MB"); l_v.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 9pt; background: transparent;")
            r_lay.addWidget(l_k); r_lay.addStretch(); r_lay.addWidget(l_v)
            self.struct_layout.addWidget(row)
            self.struct_rows[k] = l_v
        
        self.struct_layout.addStretch()
        top_layout.addWidget(struct_card, stretch=4)
        content_layout.addLayout(top_layout)

        # ACTION BUTTONS
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)
        
        self.btn_sel = ActionBtn("fa5s.folder-open", "Browse", "Find Image", "outline")
        self.btn_unpack_file = ActionBtn("fa5s.cube", "Unpack", "Primary Action", "light_blue")
        self.btn_repack_file = ActionBtn("fa5s.sync-alt", "Repack", "Active Project", "blue")
        self.btn_info_act = ActionBtn("fa5s.info", "Details", "Load Metadata", "outline")

        self.btn_sel.clicked.connect(self.select_image_dialog)
        self.btn_unpack_file.clicked.connect(self.handle_unpack)
        self.btn_repack_file.clicked.connect(self.handle_repack)
        self.btn_info_act.clicked.connect(self.handle_info)

        actions_layout.addWidget(self.btn_sel)
        actions_layout.addWidget(self.btn_unpack_file)
        actions_layout.addWidget(self.btn_repack_file)
        actions_layout.addWidget(self.btn_info_act)
        actions_layout.addStretch()
        content_layout.addLayout(actions_layout)

        self.console = ConsoleWidget()
        content_layout.addWidget(self.console)
        self.stack.addWidget(dash_page)

        # ==========================================
        # PAGE 1: WORKSPACE EXPLORER
        # ==========================================
        explore_page = QWidget()
        exp_layout = QVBoxLayout(explore_page)
        exp_layout.setContentsMargins(10, 10, 10, 10)
        
        exp_header = QHBoxLayout()
        exp_title = QLabel("Workspace Explorer")
        exp_title.setStyleSheet(f"font-size: 18pt; font-weight: bold; color: {TEXT_PRIMARY};")
        exp_header.addWidget(exp_title)
        exp_header.addStretch()
        
        btn_refresh = QPushButton()
        btn_refresh.setIcon(qta.icon('fa5s.sync', color='white'))
        btn_refresh.setFixedSize(36, 36)
        btn_refresh.setStyleSheet("background-color: #374151; border-radius: 18px;")
        btn_refresh.clicked.connect(self.refresh_state)
        exp_header.addWidget(btn_refresh)
        exp_layout.addLayout(exp_header)
        
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListView.ViewMode.IconMode)
        self.list_widget.setResizeMode(QListView.ResizeMode.Adjust)
        self.list_widget.setSpacing(20)
        self.list_widget.setMovement(QListView.Movement.Static)
        self.list_widget.setStyleSheet("QListWidget { background: transparent; border: none; } QListWidget::item:selected { background: transparent; border: none; }")
        exp_layout.addWidget(self.list_widget)
        
        self.stack.addWidget(explore_page)

        # ==========================================
        # PAGE 2: HELP KNOWLEDGE BASE (SMART ARTICLES)
        # ==========================================
        help_page = QWidget()
        help_layout = QVBoxLayout(help_page)
        help_layout.setContentsMargins(20, 20, 20, 20)
        help_layout.setSpacing(20)

        hb_header = QHBoxLayout()
        hb_title = QLabel("Knowledge Base & Manual")
        hb_title.setStyleSheet(f"font-size: 22pt; font-weight: bold; color: {TEXT_PRIMARY};")
        hb_header.addWidget(hb_title)
        hb_header.addStretch()

        self.btn_kb_refresh = QPushButton()
        self.btn_kb_refresh.setIcon(qta.icon('fa5s.cloud-download-alt', color='white'))
        self.btn_kb_refresh.setFixedSize(40, 40)
        self.btn_kb_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_kb_refresh.setStyleSheet("background-color: #3b82f6; border-radius: 20px; border: none;")
        self.btn_kb_refresh.clicked.connect(self.fetch_kb)
        hb_header.addWidget(self.btn_kb_refresh)
        help_layout.addLayout(hb_header)

        # Smart Search Bar Box
        search_box = QFrame()
        search_box.setStyleSheet(f"background-color: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: 12px; padding: 5px;")
        search_lay = QHBoxLayout(search_box)
        
        s_ico = QLabel()
        s_ico.setPixmap(qta.icon('fa5s.search', color='#9ca3af').pixmap(QSize(20, 20)))
        s_ico.setStyleSheet("border: none; background: transparent;")
        search_lay.addWidget(s_ico)
        
        self.kb_search = QLineEdit()
        self.kb_search.setPlaceholderText("Search for a question or keyword... (e.g. 'repack')")
        self.kb_search.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                border: none;
                color: {TEXT_PRIMARY};
                font-size: 12pt;
                padding: 10px;
            }}
        """)
        self.kb_search.textChanged.connect(self.filter_kb)
        search_lay.addWidget(self.kb_search)
        help_layout.addWidget(search_box)
        
        # Results Meta Data
        self.lbl_search_meta = QLabel("")
        self.lbl_search_meta.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10pt; font-weight: bold; margin-left: 5px;")
        help_layout.addWidget(self.lbl_search_meta)

        # PROPER DOCUMENTATION SCROLL AREA
        self.kb_scroll = QScrollArea()
        self.kb_scroll.setWidgetResizable(True)
        self.kb_scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 10px; background: transparent; }
            QScrollBar::handle:vertical { background: #374151; border-radius: 5px; }
        """)
        
        self.kb_content = QWidget()
        self.kb_content.setStyleSheet("background: transparent;")
        self.kb_content_layout = QVBoxLayout(self.kb_content)
        self.kb_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.kb_content_layout.setContentsMargins(0, 0, 15, 0)
        self.kb_content_layout.setSpacing(10)
        
        self.kb_scroll.setWidget(self.kb_content)
        help_layout.addWidget(self.kb_scroll)

        self.stack.addWidget(help_page)

    def switch_view(self, idx):
        self.stack.setCurrentIndex(idx)
        self.btn_dash.set_active(idx == 0)
        self.btn_explore.set_active(idx == 1)
        self.btn_help.set_active(idx == 2)
        if idx == 2 and not self.loaded_articles:
            self.fetch_kb()

    # --- KNOWLEDGE BASE ---
    def fetch_kb(self):
        self._clear_kb_ui()
        lbl = QLabel("Fetching Knowledge Base from remote server...")
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; padding: 10px; font-style: italic; font-size: 11pt;")
        self.lbl_search_meta.setText("Connecting to database...")
        self.kb_content_layout.addWidget(lbl)
        
        self.btn_kb_refresh.setEnabled(False)
        self.kb_worker = KBFetcherThread(HELP_DOC_URL)
        self.kb_worker.finished.connect(self.on_kb_fetched)
        self.kb_worker.start()

    def on_kb_fetched(self, success, data):
        self.btn_kb_refresh.setEnabled(True)
        self._clear_kb_ui()

        if success:
            self.loaded_articles = data.get("articles", [])
            if not self.loaded_articles:
                lbl = QLabel("No articles found in JSON.")
                lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; padding: 10px; font-size: 11pt;")
                self.kb_content_layout.addWidget(lbl)
                self.lbl_search_meta.setText("0 articles loaded")
            else:
                self.filter_kb(self.kb_search.text())
        else:
            # Fallback Local Data: Full Official Bootly Guide!
            self.loaded_articles = [
                {"question": "How do I unpack an Image?", "answer": "1. Go to your Dashboard.\n2. Click the 'Browse' button to explicitly select a bare, raw `.img` file from your desktop.\n3. Click 'Unpack' to mathematically extract the kernel and ramdisk into a fresh Project Folder automatically.", "tags": ["unpack", "extract", "start"]},
                {"question": "How do I repack an Image?", "answer": "1. First, navigate to the Workspace Explorer and select an already-extracted 'Active Project' folder.\n2. In the Dashboard view, magically click 'Repack'.\n3. Wait for the binary processing task to complete. The newly constructed boot image will securely be saved inside the 'output' folder.", "tags": ["repack", "build", "save"]},
                {"question": "How do I edit ramdisk files easily?", "answer": "Simple! After Unpacking successfully, an 'Open Folder' button (it looks like a green folder icon) dynamically appears on the Image Card on your Dashboard. Clicking it instantly forces Windows File Explorer to pop open directed straight at your extracted project files. Tweak configurations inside to your heart's content.", "tags": ["edit", "ramdisk", "kernel", "folder"]},
                {"question": "Where are my exact compiled images saved?", "answer": "To prevent workspace messes, every time you successfully run the Repack sequence, the final compiled `.img` file is instantly generated and pushed strictly into the `output/` directory located underneath the main Bootly workspace root.", "tags": ["output", "files", "location", "compiled"]},
                {"question": "Why is the 'Unpack' button intentionally disabled?", "answer": "The Unpack button actively assesses context and intelligently grays itself out when you have an already-extracted Project Directory selected. Bootly operates safely—you can only unpack raw `.img` archives.", "tags": ["disabled", "button", "unpack", "gray"]}
            ]
            self.filter_kb(self.kb_search.text())

    def _clear_kb_ui(self):
        for i in reversed(range(self.kb_content_layout.count())): 
            w = self.kb_content_layout.itemAt(i).widget()
            if w: w.deleteLater()

    def filter_kb(self, query):
        q = query.lower().strip()
        self._clear_kb_ui()

        count = 0
        for art in self.loaded_articles:
            text_pool = art.get('question', '').lower() + " " + art.get('answer', '').lower() + " ".join(art.get('tags', []))
            if q in text_pool:
                count += 1
                card = ArticleCard(art.get('question', 'Q?'), art.get('answer', 'A.'), art.get('tags', []), highlight_term=q)
                self.kb_content_layout.addWidget(card)

        if count == 0 and self.loaded_articles:
            self.lbl_search_meta.setText(f"Found 0 matches for '{q}'")
            m = QLabel(f"No results found matching your search term.")
            m.setStyleSheet("color: #9ca3af; font-style: italic; font-size: 11pt; padding: 20px;")
            self.kb_content_layout.addWidget(m)
        else:
            self.lbl_search_meta.setText(f"Showing {count} Help Article{'s' if count != 1 else ''}")

    # --- DASHBOARD LOGIC ---
    def select_image_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Boot/Recovery Image", "", "Image files (*.img);;All Files (*)")
        if file_path:
            input_dir = os.path.join(self.base_path, 'input')
            ensure_dir(input_dir)
            filename = os.path.basename(file_path)
            dest_path = os.path.join(input_dir, filename)
            
            if os.path.abspath(file_path) != os.path.abspath(dest_path):
                self.console.log(f"Copying {filename} to workspace...", "INFO")
                shutil.copy2(file_path, dest_path)
            
            self.load_item(filename, "RAW")

    def refresh_state(self):
        images = self.image_manager.get_raw_images()
        projects = self.image_manager.get_projects()
        
        self.list_widget.clear()
        
        def add_header(title):
            item = QListWidgetItem(self.list_widget)
            item.setSizeHint(QSize(900, 40))
            lbl = QLabel(title)
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 14pt; font-weight: bold; margin-top: 10px; margin-bottom: 5px;")
            self.list_widget.setItemWidget(item, lbl)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            
        def fill_items(items, type_):
            for i in items:
                list_item = QListWidgetItem(self.list_widget)
                list_item.setSizeHint(QSize(160, 160))
                card = ThumbnailCard(i, type_)
                card.clicked.connect(self.load_item)
                self.list_widget.setItemWidget(list_item, card)

        if projects:
            add_header("Active Unpacked Projects")
            fill_items(projects, "PROJECT")
            
        if images:
            add_header("Raw Images")
            fill_items(images, "RAW")

        if not self.current_item and (images or projects):
            if projects: self.load_item(projects[0], "PROJECT")
            else: self.load_item(images[0], "RAW")
        
        self.console.log("Workspace refreshed.", "INFO")

    def reset_ui_metadata(self):
        self.lbls_meta["Version"].setText("—")
        self.lbls_meta["Header"].setText("—")
        self.lbls_meta["Format"].setText("—")
        for k in self.struct_rows: self.struct_rows[k].setText("0.0 MB")
        while self.bar_layout.count():
            item = self.bar_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
                
    def run_metadata_parser(self, target_img):
        info_str = self.image_manager.get_info(target_img)
        def extract(pat, txt):
            m = re.search(pat, txt, re.MULTILINE)
            return m.group(1) if m else None
            
        header = extract(r"Header version\s*:\s*(.+)", info_str)
        if header: self.lbls_meta["Header"].setText(f"v{header.strip()}")
        
        os_ver = extract(r"OS version\s*:\s*(.+)", info_str)
        if os_ver: self.lbls_meta["Version"].setText(os_ver.strip())
        
        compress = extract(r"Ramdisk compress\.\s*:\s*(.+)", info_str)
        if compress: self.lbls_meta["Format"].setText(compress.strip().upper())
        
        def set_sz(name, pat):
            sz = extract(pat, info_str)
            if sz and sz.isdigit():
                mb = float(sz) / (1024*1024)
                if name in self.struct_rows: self.struct_rows[name].setText(f"{mb:.2f} MB")
                return mb
            return 0.0
            
        k_sz = set_sz("Kernel", r"Kernel size\s*:\s*(\d+)")
        r_sz = set_sz("Ramdisk", r"Ramdisk size\s*:\s*(\d+)")
        s_sz = set_sz("Second", r"Second size\s*:\s*(\d+)")
        
        total_sz = k_sz + r_sz + s_sz
        if total_sz > 0 and self.current_type == 'RAW':
             self.struct_rows["Total Image"].setText(f"{total_sz:.2f} MB")
             self.lbls_meta["Size"].setText(f"{total_sz:.2f} MB")
             
        sizes = [k_sz, r_sz, s_sz]
        total_vis = sum(sizes) if sum(sizes) > 0 else 1
        
        for idx, c in enumerate(["#1e88e5", "#4ade80", "#fbbf24"]):
            weight = max(1, int((sizes[idx] / total_vis) * 100)) if sizes[idx] > 0 else 0
            if weight == 0: continue
            chunk = QFrame(); chunk.setStyleSheet(f"background-color: {c}; border-radius: 3px;"); chunk.setFixedHeight(12)
            sz_pol = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed); sz_pol.setHorizontalStretch(weight); chunk.setSizePolicy(sz_pol)
            self.bar_layout.addWidget(chunk)
            
        chunk = QFrame(); chunk.setStyleSheet("background-color: #374151; border-radius: 3px;"); chunk.setFixedHeight(12)
        sz_pol = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed); sz_pol.setHorizontalStretch(100); chunk.setSizePolicy(sz_pol)
        self.bar_layout.addWidget(chunk)

    def load_item(self, name, type_):
        self.current_item = name
        self.current_type = type_
        self.switch_view(0)
        self.reset_ui_metadata()
        
        self.lbl_img_name.setText(f"{name} <span style='color:#4ade80;'>({type_})</span>")
        self.setWindowTitle(f"Bootly - {name}")
        self.lbl_img_date.setText(f"Location: {os.path.join(self.base_path, 'input' if type_ == 'RAW' else name)}")
        
        if type_ == "RAW":
            path = os.path.join(self.base_path, 'input', name)
            size_mb = os.path.getsize(path)/(1024*1024) if os.path.exists(path) else 0
            self.lbl_img_subtitle.setText(f"{size_mb:.1f} MB · Archive")
            self.icon_box.setStyleSheet("background-color: #3b82f6; color: white; border-radius: 8px;")
            self.lbls_meta["Status"].setText("Raw Archive")
            self.btn_unpack_file.setEnabled(True)
            self.btn_repack_file.setEnabled(False)
            self.btn_open_folder.setVisible(False)
            self.run_metadata_parser(name)
        else:
            self.lbl_img_subtitle.setText("Extracted Project Directory")
            self.icon_box.setStyleSheet("background-color: #4ade80; color: #064e3b; border-radius: 8px;")
            self.lbls_meta["Status"].setText("Editable Directory")
            self.lbls_meta["Size"].setText("Multiple Files")
            self.btn_unpack_file.setEnabled(False)
            self.btn_repack_file.setEnabled(True)
            self.btn_open_folder.setVisible(True)
            if os.path.exists(os.path.join(self.base_path, 'input', f"{name}.img")):
                self.run_metadata_parser(f"{name}.img")

        self.console.log(f"Switched to {name} ({type_})", "SUCCESS")

    def handle_open_folder(self):
        if self.current_type == "PROJECT":
            path = os.path.join(self.base_path, self.current_item)
            if os.path.exists(path):
                os.startfile(path)

    def console_cb_signal(self, message):
        tag = "INFO"
        if "Compressing" in message or "Exec" in message: tag = "REPACKING"
        elif "Unpacking" in message or "Extracting" in message: tag = "UNPACKING"
        elif "Success" in message: tag = "SUCCESS"
        elif "Error" in message or "failed" in message: 
            tag = "ERROR"
            log_ga_event("error_occurred", {"error_type": "process_error"})
            
        self.console.log(message, tag)

    def handle_unpack(self):
        if self.current_type != "RAW": return
        self.console.start_progress()
        self.console.log("Extracting...", "UNPACKING")
        self.btn_unpack_file.setEnabled(False)
        self.worker = WorkerThread(self.image_manager.unpack, self.current_item)
        self.worker.log_signal.connect(self.console_cb_signal)
        self.worker.finished.connect(self.on_unpack_done)
        self.worker.start()

    def on_unpack_done(self, success, res):
        self.console.stop_progress()
        if success:
            self.console.log("Extracted kernel and ramdisk.", "SUCCESS")
            folder_name = os.path.splitext(self.current_item)[0]
            self.refresh_state() 
            self.load_item(folder_name, "PROJECT")
            if QMessageBox.question(self, 'Success', "Unpacked successfully! Open folder?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                self.handle_open_folder()
        else:
             self.btn_unpack_file.setEnabled(True)

    def handle_repack(self):
        if self.current_type != "PROJECT": return
        self.console.start_progress()
        self.console.log("Repacking...", "REPACKING")
        self.btn_repack_file.setEnabled(False)
        self.worker = WorkerThread(self.image_manager.repack, self.current_item)
        self.worker.log_signal.connect(self.console_cb_signal)
        self.worker.finished.connect(self.on_repack_done)
        self.worker.start()
        
    def on_repack_done(self, success, res):
        self.console.stop_progress()
        self.btn_repack_file.setEnabled(True)
        if success:
            out_img = os.path.join(self.image_manager.output_path, f"{self.current_item}-repacked.img")
            self.console.log(f"Repack complete", "SUCCESS")
            if QMessageBox.question(self, 'Success', "Repacked! Open output folder?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                os.startfile(self.image_manager.output_path)

    def handle_info(self):
        if not self.current_item: return
        self.console.start_progress()
        self.console.log("Fetching detailed info...", "INFO")
        target = self.current_item if self.current_type == "RAW" else f"{self.current_item}.img"
        info = self.image_manager.get_info(target)
        for line in str(info).split('\n'):
            if line.strip(): self.console.log(line.strip(), "INFO")
        self.console.stop_progress()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    app.setStyleSheet(f"""
        QMessageBox {{
            background-color: {BG_COLOR};
        }}
        QMessageBox QLabel {{
            color: {TEXT_PRIMARY};
            font-size: 10pt;
        }}
        QMessageBox QPushButton {{
            background-color: #3b82f6;
            color: white;
            padding: 6px 20px;
            border-radius: 4px;
            font-weight: bold;
            border: none;
        }}
        QMessageBox QPushButton:hover {{
            background-color: #2563eb;
        }}
    """)
    
    window = BootlyApp()
    window.show()
    sys.exit(app.exec())
