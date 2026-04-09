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
                             QProgressBar, QMessageBox, QLineEdit, QDialog, QMenuBar, QMenu, QCheckBox, QInputDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QUrl
from PyQt6.QtGui import QFont, QIcon, QColor, QPalette, QCursor, QAction, QDesktopServices
import qtawesome as qta

from core.image_manager import ImageManager
from core.utils import ensure_dir, open_folder
from core.updater import UpdateCheckerThread, UpdateDownloaderThread, apply_update, CURRENT_VERSION, is_binary
from core.analytics import AnalyticsManager, log_ga_event

# --- STYLING CONSTANTS ---
BG_COLOR = "#0b0c10"
SIDEBAR_COLOR = "#0b0c10"
CARD_BG = "#131418"
CARD_BORDER = "#1f2024"
TEXT_PRIMARY = "#f3f4f6"
TEXT_SECONDARY = "#9ca3af"

HELP_DOC_URL = "https://bootly.harislab.tech/api/discussions?include=firstPost,tags"

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
        
        self.btn_clear = QPushButton("Clear Output")
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background: transparent; border: 1px solid #374151; color: #9ca3af; 
                padding: 2px 10px; border-radius: 4px; font-size: 8pt; font-weight: bold;
            }
            QPushButton:hover { background: #374151; color: white; }
        """)
        self.btn_clear.clicked.connect(self.clear_output)
        top_layout.addWidget(self.btn_clear)
        
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
        self.progress.setRange(0, 0)
        self.progress.show()

    def stop_progress(self):
        self.progress.hide()

    def clear_output(self):
        self.text_edit.clear()

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

    def __init__(self, base_url, offset=0, limit=10):
        super().__init__()
        self.base_url = base_url
        self.offset = offset
        self.limit = limit

    def run(self):
        try:
            # Build URL with pagination
            url = f"{self.base_url}&page[offset]={self.offset}&page[limit]={self.limit}"
            req = urllib.request.Request(url, headers={'User-Agent': 'BootlyApp/1.0'})
            with urllib.request.urlopen(req, timeout=12) as response:
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
    def __init__(self, question, answer, tags, url="", highlight_term=""):
        super().__init__()
        self.question = question
        self.answer = answer
        self.tags = tags
        self.url = url
        self.highlight_term = highlight_term
        self.expanded = False
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {CARD_BG};
                border: 1px solid {CARD_BORDER};
                border-radius: 12px;
                margin-top: 10px;
                margin-bottom: 5px;
            }}
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(25, 25, 25, 25)
        self.layout.setSpacing(12)
        
        # Header Area
        header_lay = QHBoxLayout()
        header_lay.setSpacing(10)
        
        q_ico = QLabel()
        q_ico.setPixmap(qta.icon('fa5s.question-circle', color='#3b82f6').pixmap(QSize(24, 24)))
        q_ico.setStyleSheet("background: transparent; border: none;")
        header_lay.addWidget(q_ico)
        
        self.lbl_q = QLabel(self._highlight(question, highlight_term))
        self.lbl_q.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_q.setWordWrap(True)
        self.lbl_q.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14pt; font-weight: bold; border: none; background: transparent;")
        header_lay.addWidget(self.lbl_q, stretch=1)
        self.layout.addLayout(header_lay)
        
        # Tags Area
        if tags:
            tags_lay = QHBoxLayout()
            tags_lay.setContentsMargins(34, 0, 0, 0)
            tags_lay.setSpacing(8)
            for t in tags:
                lbl_t = QLabel(t)
                lbl_t.setStyleSheet("background-color: #1f2937; color: #9ca3af; padding: 4px 10px; border-radius: 6px; font-size: 8pt; border: none;")
                tags_lay.addWidget(lbl_t)
            tags_lay.addStretch()
            self.layout.addLayout(tags_lay)
            
        # Divider (Initially hidden, shown when expanded)
        self.div = QFrame()
        self.div.setFixedHeight(1)
        self.div.setStyleSheet(f"background-color: {CARD_BORDER}; border: none; margin-top: 8px; margin-bottom: 8px;")
        self.div.setVisible(False)
        self.layout.addWidget(self.div)
        
        # Answer/Content Area
        self.lbl_a = QLabel()
        self.lbl_a.setWordWrap(True)
        self.lbl_a.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse)
        self.lbl_a.setOpenExternalLinks(True)
        self.lbl_a.setStyleSheet(f"color: #d1d5db; font-size: 11pt; border: none; background: transparent; line-height: 160%;")
        self.lbl_a.setVisible(False)
        self.layout.addWidget(self.lbl_a)

        # Community Footer (Initially hidden)
        self.footer = QFrame()
        self.footer.setStyleSheet("background: transparent; border: none;")
        self.footer_lay = QHBoxLayout(self.footer)
        self.footer_lay.setContentsMargins(0, 10, 0, 0)
        self.footer_lay.setSpacing(10)

        def create_footer_btn(text, icon_name):
            btn = QPushButton(text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #1f2937;
                    color: {TEXT_SECONDARY};
                    border: 1px solid {CARD_BORDER};
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 9pt;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {CARD_BORDER};
                    color: {TEXT_PRIMARY};
                    border: 1px solid #3b82f6;
                }}
            """)
            if self.url:
                btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.url)))
            return btn

        self.btn_like = create_footer_btn("👍 Like on Community", None)
        self.btn_join = create_footer_btn("💬 Join Discussion", None)
        self.btn_web = create_footer_btn("🌐 Open in Full Web View", None)

        self.footer_lay.addWidget(self.btn_like)
        self.footer_lay.addWidget(self.btn_join)
        self.footer_lay.addWidget(self.btn_web)
        self.footer_lay.addStretch()
        
        self.footer.setVisible(False)
        self.layout.addWidget(self.footer)

        # Read More Button
        self.btn_more = QPushButton("Read More")
        self.btn_more.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_more.setFixedWidth(100)
        self.btn_more.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #3b82f6;
                color: #3b82f6;
                border-radius: 6px;
                padding: 5px;
                font-weight: bold;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #3b82f6;
                color: white;
            }
        """)
        self.btn_more.clicked.connect(self.toggle_expand)
        self.layout.addWidget(self.btn_more)

    def _highlight(self, text, term):
        if not term: return text
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        return pattern.sub(lambda m: f"<span style='background-color: #3b82f6; color: white; padding: 2px 4px; border-radius: 4px;'>{m.group(0)}</span>", text)

    def toggle_expand(self):
        self.expanded = not self.expanded
        if self.expanded:
            # Show full content (using HTML from Flarum if possible)
            display_content = self.answer
            
            # Apply highlighting to content if there's a search term
            if self.highlight_term:
                display_content = self._highlight(display_content, self.highlight_term)
            
            if "<html>" in display_content.lower() or "<p>" in display_content.lower() or "</span>" in display_content.lower():
                self.lbl_a.setText(display_content)
                self.lbl_a.setTextFormat(Qt.TextFormat.RichText)
            elif hasattr(self.lbl_a, 'setMarkdown'):
                # Markdown highlighting is tricky, best to use HTML format if we highlighted
                if self.highlight_term:
                    self.lbl_a.setText(display_content)
                    self.lbl_a.setTextFormat(Qt.TextFormat.RichText)
                else:
                    self.lbl_a.setMarkdown(self.answer)
            else:
                self.lbl_a.setText(display_content.replace('\n', '<br>'))
            
            self.lbl_a.setVisible(True)
            self.footer.setVisible(True)
            self.btn_more.setText("Read Less")
            self.div.setVisible(True)
        else:
            self.lbl_a.setVisible(False)
            self.footer.setVisible(False)
            self.btn_more.setText("Read More")
            self.div.setVisible(False)

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
        
        is_compiled = is_binary()
        
        if is_compiled:
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
        else:
            # Source code mode
            lbl_source = QLabel("⚠️ Running through source code")
            lbl_source.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 9pt; font-style: italic;")
            btn_lay.addWidget(lbl_source)
            btn_lay.addStretch()
            
            self.btn_github = QPushButton("Open GitHub (Browser)")
            self.btn_github.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_github.setStyleSheet("background-color: #4ade80; color: #064e3b; padding: 10px 20px; border-radius: 6px; font-weight: bold; border: none;")
            self.btn_github.clicked.connect(self.open_github_link)
            
            self.btn_close = QPushButton("Close")
            self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_close.setStyleSheet(f"background-color: transparent; border: 1px solid {CARD_BORDER}; color: {TEXT_SECONDARY}; padding: 10px 20px; border-radius: 6px; font-weight: bold;")
            self.btn_close.clicked.connect(self.reject)
            
            btn_lay.addWidget(self.btn_close)
            btn_lay.addWidget(self.btn_github)

        layout.addLayout(btn_lay)

    def open_github_link(self):
        url = self.data.get("source_url", "https://github.com/Haris16-code/Bootly")
        QDesktopServices.openUrl(QUrl(url))
        self.accept()

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
        self.kb_offset = 0
        self.kb_limit = 10
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

        # Menu Bar Styling
        self.menuBar().setStyleSheet(f"""
            QMenuBar {{
                background-color: {BG_COLOR};
                color: {TEXT_SECONDARY};
                border-bottom: 1px solid {CARD_BORDER};
            }}
            QMenuBar::item {{
                padding: 4px 10px;
                background: transparent;
            }}
            QMenuBar::item:selected {{
                background: #1f2024;
                color: {TEXT_PRIMARY};
            }}
            QMenu {{
                background-color: {CARD_BG};
                color: {TEXT_PRIMARY};
                border: 1px solid {CARD_BORDER};
            }}
            QMenu::item:selected {{
                background-color: #3b82f6;
                color: white;
            }}
        """)

        # Community Menu
        comm_menu = self.menuBar().addMenu("Community")
        
        act_feature = QAction("Suggest a Feature", self)
        act_feature.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://bootly.harislab.tech/t/feature-requests")))
        comm_menu.addAction(act_feature)
        
        act_feedback = QAction("Send Feedback", self)
        act_feedback.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://bootly.harislab.tech/t/feedback")))
        comm_menu.addAction(act_feedback)
        
        comm_menu.addSeparator()
        
        act_join = QAction("Join Official Community", self)
        act_join.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://bootly.harislab.tech")))
        comm_menu.addAction(act_join)

        # Help Menu
        help_menu = self.menuBar().addMenu("Help")
        
        act_bug = QAction("Report a Bug", self)
        act_bug.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/Haris16-code/Bootly/issues")))
        help_menu.addAction(act_bug)
        
        help_menu.addSeparator()
        
        act_upd = QAction("Check for Updates", self)
        act_upd.triggered.connect(lambda: self.check_for_updates(manual=True))
        help_menu.addAction(act_upd)
        
        act_sub = QAction("Email Updates", self)
        act_sub.triggered.connect(self.show_subscribe)
        help_menu.addAction(act_sub)
        
        act_about = QAction("About Bootly", self)
        act_about.triggered.connect(self.show_about)
        help_menu.addAction(act_about)

        # Main Navigation Buttons
        self.btn_dash = SidebarBtn("fa5s.home", "Dashboard", True)
        self.btn_explore = SidebarBtn("fa5s.layer-group", "Workspace")
        self.btn_avb = SidebarBtn("fa5s.shield-alt", "AVB Tool")
        self.btn_help = SidebarBtn("fa5s.book", "Knowledge Base") 
        
        self.btn_dash.clicked.connect(lambda: self.switch_view(0))
        self.btn_explore.clicked.connect(lambda: self.switch_view(1))
        self.btn_help.clicked.connect(lambda: self.switch_view(2))
        self.btn_avb.clicked.connect(lambda: self.switch_view(3))
        
        sidebar_layout.addWidget(self.btn_dash)
        sidebar_layout.addWidget(self.btn_explore)
        sidebar_layout.addWidget(self.btn_avb)
        sidebar_layout.addWidget(self.btn_help)
        
        # Keep navigation at the top
        sidebar_layout.addStretch()
        
        # Finalize Sidebar layout
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

        # SECURITY OPTIONS
        security_group = QFrame()
        security_group.setStyleSheet(f"background-color: #111827; border: 1px solid {CARD_BORDER}; border-radius: 8px;")
        sec_lay = QHBoxLayout(security_group)
        sec_lay.setContentsMargins(15, 8, 15, 8)
        
        sec_lbl = QLabel("Security Bypass:")
        sec_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: bold; font-size: 9pt; margin-right: 10px;")
        sec_lay.addWidget(sec_lbl)
        
        self.cb_patch_vbmeta = QCheckBox("Patch VBMeta (AVB)")
        
        chk_style = f"""
            QCheckBox {{ color: {TEXT_SECONDARY}; font-size: 9pt; spacing: 8px; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 4px; border: 1px solid {CARD_BORDER}; background: {BG_COLOR}; }}
            QCheckBox::indicator:checked {{ background: #3b82f6; border-color: #3b82f6; }}
        """
        self.cb_patch_vbmeta.setStyleSheet(chk_style)
        
        sec_lay.addWidget(self.cb_patch_vbmeta)
        sec_lay.addSpacing(20)
        
        self.btn_gen_vbmeta = QPushButton("Generate VBMeta")
        self.btn_gen_vbmeta.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_gen_vbmeta.setFixedHeight(28)
        self.btn_gen_vbmeta.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #f3f4f6;
                padding: 0 10px;
                border-radius: 4px;
                font-size: 9pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
        """)
        self.btn_gen_vbmeta.clicked.connect(self.handle_generate_vbmeta)
        sec_lay.addWidget(self.btn_gen_vbmeta)

        sec_lay.addStretch()
        
        content_layout.addWidget(security_group)

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
        self.btn_kb_refresh.setIcon(qta.icon('fa5s.sync', color='white'))
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

        # Loading Progress Bar
        self.kb_progress = QProgressBar()
        self.kb_progress.setFixedHeight(4)
        self.kb_progress.setTextVisible(False)
        self.kb_progress.setStyleSheet("""
            QProgressBar { background: #131418; border: none; }
            QProgressBar::chunk { background-color: #3b82f6; }
        """)
        self.kb_progress.hide()
        help_layout.addWidget(self.kb_progress)

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

        # Pagination Footer
        self.kb_pagination_lay = QHBoxLayout()
        self.btn_kb_prev = QPushButton("Previous")
        self.btn_kb_next = QPushButton("Next")
        
        style_pag = """
            QPushButton { 
                background-color: #1f2937; color: white; border: none; padding: 8px 15px; 
                border-radius: 6px; font-weight: bold; font-size: 9pt;
            }
            QPushButton:hover { background-color: #374151; }
            QPushButton:disabled { background-color: #0b0c10; color: #4b5563; }
        """
        self.btn_kb_prev.setStyleSheet(style_pag)
        self.btn_kb_next.setStyleSheet(style_pag)
        self.btn_kb_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_kb_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_kb_prev.setEnabled(False)
        self.btn_kb_next.setEnabled(False)
        
        self.btn_kb_prev.clicked.connect(lambda: self.change_kb_page(-1))
        self.btn_kb_next.clicked.connect(lambda: self.change_kb_page(1))
        
        self.kb_pagination_lay.addStretch()
        self.kb_pagination_lay.addWidget(self.btn_kb_prev)
        self.kb_pagination_lay.addSpacing(10)
        self.kb_pagination_lay.addWidget(self.btn_kb_next)
        self.kb_pagination_lay.addStretch()
        help_layout.addLayout(self.kb_pagination_lay)

        self.stack.addWidget(help_page)
        self.init_avb_page()

    def init_avb_page(self):
        avb_page = QWidget()
        avb_layout = QVBoxLayout(avb_page)
        avb_layout.setContentsMargins(0, 0, 0, 0)
        avb_layout.setSpacing(0)
        
        # Ensure all standard labels in this page inherit the correct dark theme color
        avb_page.setStyleSheet(f"QLabel {{ color: {TEXT_PRIMARY}; font-size: 10pt; }}")

        # Header
        header = QFrame()
        header.setFixedHeight(70)
        header.setStyleSheet(f"background-color: {BG_COLOR}; border-bottom: 1px solid {CARD_BORDER};")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(20, 0, 20, 0)
        
        icon = QLabel()
        icon.setPixmap(qta.icon('fa5s.shield-alt', color='#3b82f6').pixmap(QSize(28, 28)))
        tit_lay = QVBoxLayout()
        tit_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tit = QLabel("AVB Master Tool")
        tit.setStyleSheet(f"font-size: 15pt; font-weight: 800; color: {TEXT_PRIMARY};")
        sub = QLabel("Advanced Android Verified Boot Operations")
        sub.setStyleSheet(f"font-size: 9pt; color: {TEXT_SECONDARY};")
        tit_lay.addWidget(tit)
        tit_lay.addWidget(sub)
        
        h_lay.addWidget(icon)
        h_lay.addLayout(tit_lay)
        h_lay.addStretch()
        avb_layout.addWidget(header)

        # Tools Content - Scrollable
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_lay = QVBoxLayout(scroll_content)
        scroll_lay.setContentsMargins(20, 20, 20, 20)
        scroll_lay.setSpacing(20)

        def create_tool_card(title, description, icon_name):
            card = QFrame()
            card.setStyleSheet(f"background-color: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: 12px;")
            lay = QVBoxLayout(card)
            lay.setContentsMargins(20, 20, 20, 20)
            
            h = QHBoxLayout()
            i = QLabel()
            i.setPixmap(qta.icon(icon_name, color='#60a5fa').pixmap(QSize(24, 24)))
            t = QLabel(title)
            t.setStyleSheet(f"font-size: 12pt; font-weight: bold; color: {TEXT_PRIMARY};")
            h.addWidget(i)
            h.addWidget(t)
            h.addStretch()
            lay.addLayout(h)
            
            d = QLabel(description)
            d.setWordWrap(True)
            d.setStyleSheet(f"font-size: 9pt; color: {TEXT_SECONDARY}; margin-top: 5px;")
            lay.addWidget(d)
            lay.addSpacing(10)
            
            form = QGridLayout()
            form.setSpacing(10)
            form.setColumnMinimumWidth(0, 120)
            form.setColumnStretch(1, 1)
            lay.addLayout(form)
            return card, form

        # 1. VBMETA GENERATOR
        card_g, form_g = create_tool_card("Standalone VBMeta Generation", 
            "Create a new, unsigned ‘empty’ vbmeta image to bypass AVB on supported Android 10+ devices.", 
            "fa5s.magic")
        
        btn_run_g = QPushButton("Generate Empty VBMeta")
        btn_run_g.setFixedHeight(34)
        btn_run_g.clicked.connect(self.run_avb_generate_vbmeta)
        form_g.addWidget(btn_run_g, 0, 0, 1, 4)
        scroll_lay.addWidget(card_g)

        # 2. INTEGRITY VERIFICATION
        card_v, form_v = create_tool_card("Integrity & Verification", 
            "Compares image hashes against VBMeta descriptors to ensure partition has not been tampered with.", 
            "fa5s.check-circle")
        
        self.avb_v_img = QLineEdit()
        self.avb_v_img.setPlaceholderText("Select image...")
        btn_v_img = QPushButton("Browse")
        btn_v_img.clicked.connect(lambda: self.browse_avb_file(self.avb_v_img))
        
        self.avb_v_key = QLineEdit()
        self.avb_v_key.setPlaceholderText("Custom key (Optional)...")
        btn_v_key = QPushButton("Browse")
        btn_v_key.clicked.connect(lambda: self.browse_avb_file(self.avb_v_key))

        form_v.addWidget(QLabel("Target Image:"), 0, 0)
        form_v.addWidget(self.avb_v_img, 0, 1)
        form_v.addWidget(btn_v_img, 0, 2)
        form_v.addWidget(QLabel("Public Key:"), 1, 0)
        form_v.addWidget(self.avb_v_key, 1, 1)
        form_v.addWidget(btn_v_key, 1, 2)
        
        btn_run_v = QPushButton("Verify Integrity")
        btn_run_v.clicked.connect(self.run_avb_verify)
        form_v.addWidget(btn_run_v, 2, 0, 1, 3)
        scroll_lay.addWidget(card_v)

        # 2. FOOTER MANAGEMENT
        card_f, form_f = create_tool_card("Footer Append (Hash Footer)", 
            "Calculates image hash and appends an AVB footer. Required for devices without a separate VBMeta partition.", 
            "fa5s.file-signature")
            
        self.avb_f_img = QLineEdit()
        self.avb_f_name = QLineEdit("boot")
        self.avb_f_size = QLineEdit("33554432") # 32MB default
        
        form_f.addWidget(QLabel("Image:"), 0, 0)
        form_f.addWidget(self.avb_f_img, 0, 1)
        btn_f_img = QPushButton("Browse")
        btn_f_img.clicked.connect(lambda: self.browse_avb_file(self.avb_f_img))
        form_f.addWidget(btn_f_img, 0, 2)
        
        form_f.addWidget(QLabel("Part Name:"), 1, 0)
        form_f.addWidget(self.avb_f_name, 1, 1)
        form_f.addWidget(QLabel("Part Size (Bytes):"), 1, 2)
        form_f.addWidget(self.avb_f_size, 1, 3)
        
        btn_run_f = QPushButton("Calculate & Append Footer")
        btn_run_f.clicked.connect(self.run_avb_footer)
        form_f.addWidget(btn_run_f, 2, 0, 1, 4)
        scroll_lay.addWidget(card_f)

        # 3. SIGNATURE & ROLLBACK
        card_s, form_s = create_tool_card("Signature & Rollback Control", 
            "Sign images with custom RSA keys, manage rollback protection indices, and set bypass flags.", 
            "fa5s.key")
            
        self.avb_s_img = QLineEdit()
        self.avb_s_key = QLineEdit()
        self.avb_s_roll = QLineEdit("0")
        
        self.avb_s_alg = QComboBox()
        self.avb_s_alg.addItems(["SHA256_RSA2048", "SHA256_RSA4096", "SHA512_RSA4096", "SHA256_RSA8192"])
        
        form_s.addWidget(QLabel("Target Image:"), 0, 0)
        form_s.addWidget(self.avb_s_img, 0, 1)
        btn_s_img = QPushButton("Browse")
        btn_s_img.clicked.connect(lambda: self.browse_avb_file(self.avb_s_img))
        form_s.addWidget(btn_s_img, 0, 2)
        
        form_s.addWidget(QLabel("RSA Private Key:"), 1, 0)
        form_s.addWidget(self.avb_s_key, 1, 1)
        btn_s_key = QPushButton("Browse")
        btn_s_key.clicked.connect(lambda: self.browse_avb_file(self.avb_s_key))
        form_s.addWidget(btn_s_key, 1, 2)
        
        form_s.addWidget(QLabel("Algorithm:"), 2, 0)
        form_s.addWidget(self.avb_s_alg, 2, 1)
        form_s.addWidget(QLabel("Rollback Index:"), 2, 2)
        form_s.addWidget(self.avb_s_roll, 2, 3)
        
        btn_run_s = QPushButton("Apply Signature & Rollback")
        btn_run_s.clicked.connect(self.run_avb_patch)
        form_s.addWidget(btn_run_s, 3, 0, 1, 4)
        scroll_lay.addWidget(card_s)

        # 4. METADATA & INFO
        card_i, form_i = create_tool_card("Metadata & Sizing", 
            "Analyze AVB descriptors and calculate the required VBMeta overhead and partition sizing.", 
            "fa5s.info-circle")
        
        self.avb_i_img = QLineEdit()
        form_i.addWidget(QLabel("Image:"), 0, 0)
        form_i.addWidget(self.avb_i_img, 0, 1)
        btn_i_img = QPushButton("Browse")
        btn_i_img.clicked.connect(lambda: self.browse_avb_file(self.avb_i_img))
        form_i.addWidget(btn_i_img, 0, 2)
        
        btn_run_i = QPushButton("Analyze Metadata")
        btn_run_i.setFixedHeight(34)
        btn_run_i.clicked.connect(self.run_avb_info)
        form_i.addWidget(btn_run_i, 1, 0, 1, 3)
        scroll_lay.addWidget(card_i)



        # Ensure cards have max width for better appearance
        for i in range(scroll_lay.count()):
            w = scroll_lay.itemAt(i).widget()
            if w: w.setMaximumWidth(820)

        scroll_lay.addStretch()
        scroll.setWidget(scroll_content)
        avb_layout.addWidget(scroll)

        # Bottom Console
        console_lay = QVBoxLayout()
        console_lay.setContentsMargins(20, 0, 20, 20)
        self.avb_console = ConsoleWidget()
        self.avb_console.setFixedHeight(180)
        console_lay.addWidget(self.avb_console)
        avb_layout.addLayout(console_lay)

        self.stack.addWidget(avb_page)

    def switch_view(self, index):
        self.stack.setCurrentIndex(index)
        self.btn_dash.set_active(index == 0)
        self.btn_explore.set_active(index == 1)
        self.btn_help.set_active(index == 2)
        self.btn_avb.set_active(index == 3)
        if index == 2 and not self.loaded_articles:
            self.fetch_kb()

    # --- KNOWLEDGE BASE ---
    def change_kb_page(self, delta):
        new_offset = self.kb_offset + (delta * self.kb_limit)
        if new_offset < 0: return
        self.kb_offset = new_offset
        self.fetch_kb()

    def fetch_kb(self):
        self._clear_kb_ui()
        self.kb_progress.show()
        self.kb_progress.setRange(0, 0) # Indeterminate
        
        lbl = QLabel("Fetching Knowledge Base from remote server...")
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; padding: 10px; font-style: italic; font-size: 11pt;")
        self.lbl_search_meta.setText("Connecting...")
        self.kb_content_layout.addWidget(lbl)
        
        self.btn_kb_refresh.setEnabled(False)
        self.kb_worker = KBFetcherThread(HELP_DOC_URL, offset=self.kb_offset, limit=self.kb_limit)
        self.kb_worker.finished.connect(self.on_kb_fetched)
        self.kb_worker.start()

    def on_kb_fetched(self, success, data):
        self.btn_kb_refresh.setEnabled(True)
        self.kb_progress.hide()
        self._clear_kb_ui()

        if success and isinstance(data, dict) and "data" in data:
            discussions = data.get("data", [])
            included = data.get("included", [])
            links = data.get("links", {})
            
            # Update pagination buttons
            self.btn_kb_prev.setEnabled(self.kb_offset > 0)
            self.btn_kb_next.setEnabled("next" in links)
            
            def find_included(type_, id_):
                for item in included:
                    if item.get("type") == type_ and str(item.get("id")) == str(id_):
                        return item
                return None

            articles = []
            target_tags = {"official", "bootly", "guides-tutorials"}
            
            for disc in discussions:
                attrs = disc.get("attributes", {})
                title = attrs.get("title", "Untitled")
                slug = attrs.get("slug", "")
                article_url = f"https://bootly.harislab.tech/d/{slug}"
                
                # Extract Tags - Display names vs Filtering tokens
                display_tags = []
                filter_tokens = set()
                tags_rel = disc.get("relationships", {}).get("tags", {}).get("data", [])
                for t_ref in tags_rel:
                    t_obj = find_included("tags", t_ref.get("id"))
                    if t_obj:
                        attrs = t_obj.get("attributes", {})
                        t_name = attrs.get("name", "")
                        t_slug = attrs.get("slug", "")
                        if t_name not in display_tags:
                            display_tags.append(t_name)
                        filter_tokens.add(t_name.lower())
                        filter_tokens.add(t_slug.lower())
                
                # Check if ALL target tags are present in filter tokens
                if not target_tags.issubset(filter_tokens):
                    continue
                
                # Extract Content (Prefer contentHtml for better rendering)
                content = ""
                post_rel = disc.get("relationships", {}).get("firstPost", {}).get("data")
                if post_rel:
                    p_obj = find_included("posts", post_rel.get("id"))
                    if p_obj:
                        pattrs = p_obj.get("attributes", {})
                        # Try contentHtml first for rich content, then raw content
                        content = pattrs.get("contentHtml") or pattrs.get("content", "")
                
                articles.append({
                    "question": title,
                    "answer": content,
                    "tags": display_tags,
                    "url": article_url
                })
            
            self.loaded_articles = articles
            if not self.loaded_articles:
                lbl = QLabel("No articles found with the required tags.")
                lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; padding: 10px; font-size: 11pt;")
                self.kb_content_layout.addWidget(lbl)
                self.lbl_search_meta.setText("0 articles loaded")
            else:
                self.filter_kb(self.kb_search.text())
        elif success:
             # Fallback if structure is unexpected but success was True
             self.loaded_articles = []
             self.lbl_search_meta.setText("Error: Unexpected data structure.")
        else:
            # Fallback Local Data (if connection fails)
            self.loaded_articles = [
                {"question": "How do I unpack an Image?", "answer": "1. Go to your Dashboard.\n2. Click the 'Browse' button to select a bare `.img` file.\n3. Click 'Unpack' to extract it.", "tags": ["unpack", "Official", "Bootly", "Guides & Tutorial"]},
                {"question": "How do I repack an Image?", "answer": "1. Select an 'Active Project' folder.\n2. Click 'Repack'.\n3. Result is in the 'output' folder.", "tags": ["repack", "Official", "Bootly", "Guides & Tutorial"]}
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
                card = ArticleCard(art.get('question', 'Q?'), art.get('answer', 'A.'), art.get('tags', []), url=art.get('url', ''), highlight_term=q)
                # Auto-expand if specifically found via search and it is part of a small result set
                if q:
                    card.toggle_expand()
                self.kb_content_layout.addWidget(card)

        if count == 0 and self.loaded_articles:
            self.lbl_search_meta.setText(f"Found 0 matches for '{q}'")
            
            error_box = QFrame()
            error_box.setStyleSheet("background: transparent; border: none;")
            err_lay = QVBoxLayout(error_box)
            err_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            m = QLabel(f"No results found matching your search term.")
            m.setStyleSheet("color: #9ca3af; font-style: italic; font-size: 11pt; padding: 10px;")
            m.setAlignment(Qt.AlignmentFlag.AlignCenter)
            err_lay.addWidget(m)
            
            btn_ask = QPushButton("Ask in Community Hub 💬")
            btn_ask.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_ask.setFixedSize(220, 45)
            btn_ask.setStyleSheet("""
                QPushButton {
                    background-color: #3b82f6;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 10pt;
                }
                QPushButton:hover {
                    background-color: #2563eb;
                }
            """)
            btn_ask.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://bootly.harislab.tech/t/support-debugging")))
            err_lay.addWidget(btn_ask)
            
            self.kb_content_layout.addWidget(error_box)
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
                open_folder(path)

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
        
        default_name = f"{self.current_item}-repacked"
        while True:
            name, ok = QInputDialog.getText(self, 'Repack Image', 'Enter output filename (no extension):', QLineEdit.EchoMode.Normal, default_name)
            if not ok or not name:
                return
                
            filename = name.strip()
            if not filename.endswith('.img'):
                filename += '.img'
            
            dest_path = os.path.join(self.image_manager.output_path, filename)
            if os.path.exists(dest_path):
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("File Exists")
                msg_box.setText(f"The file '{filename}' already exists.")
                msg_box.setInformativeText("Do you want to replace the existing file or choose a different name?")
                replace_btn = msg_box.addButton("Replace", QMessageBox.ButtonRole.AcceptRole)
                rename_btn = msg_box.addButton("Rename", QMessageBox.ButtonRole.ActionRole)
                cancel_btn = msg_box.addButton(QMessageBox.StandardButton.Cancel)
                
                msg_box.exec()
                
                if msg_box.clickedButton() == rename_btn:
                    continue 
                elif msg_box.clickedButton() == cancel_btn:
                    return
            break

        # Start repack thread with chosen filename
        self.console.start_progress()
        self.console.log(f"Repacking to {filename}...", "REPACKING")
        self.btn_repack_file.setEnabled(False)
        
        # Explicitly pass keywords to avoid overlap with callback
        patch_v = self.cb_patch_vbmeta.isChecked()
        
        self.worker = WorkerThread(self.image_manager.repack, self.current_item, 
                                   patch_vbmeta=patch_v, custom_name=filename)
        self.worker.log_signal.connect(self.console_cb_signal)
        self.worker.finished.connect(self.on_repack_done)
        self.worker.start()

    def handle_generate_vbmeta(self):
        while True:
            name, ok = QInputDialog.getText(self, 'Generate VBMeta', 'Enter filename (no extension):', QLineEdit.EchoMode.Normal, "vbmeta_patched")
            if not ok or not name:
                return
                
            filename = name.strip()
            if not filename.endswith('.img'):
                filename += '.img'
            
            dest_path = os.path.join(self.image_manager.output_path, filename)
            if os.path.exists(dest_path):
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("File Exists")
                msg_box.setText(f"The file '{filename}' already exists.")
                msg_box.setInformativeText("Do you want to replace the existing file or choose a different name?")
                replace_btn = msg_box.addButton("Replace", QMessageBox.ButtonRole.AcceptRole)
                rename_btn = msg_box.addButton("Rename", QMessageBox.ButtonRole.ActionRole)
                cancel_btn = msg_box.addButton(QMessageBox.StandardButton.Cancel)
                
                msg_box.exec()
                
                if msg_box.clickedButton() == rename_btn:
                    continue # Loop back to ask for name again
                elif msg_box.clickedButton() == cancel_btn:
                    return
                # if clicked replace_btn, we fall through and execute
            
            # If we reached here, we either don't have a conflict or user chose Replace
            self.console.start_progress()
            self.console.log(f"Generating standalone VBMeta: {filename}...", "INFO")
            
            self.worker = WorkerThread(self.image_manager.generate_empty_vbmeta, filename)
            self.worker.log_signal.connect(self.console_cb_signal)
            self.worker.finished.connect(self.on_vbmeta_gen_done)
            self.worker.start()
            break

    def on_vbmeta_gen_done(self, success, res):
        self.console.stop_progress()
        if success:
            self.console.log("VBMeta generation complete.", "SUCCESS")
            if QMessageBox.question(self, 'Success', f"Generated successfully! Open output folder?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                open_folder(self.image_manager.output_path)
        else:
            self.console.log(f"Error generating VBMeta: {res}", "ERROR")
        
    def on_repack_done(self, success, res):
        self.console.stop_progress()
        self.btn_repack_file.setEnabled(True)
        if success:
            out_img = os.path.join(self.image_manager.output_path, f"{self.current_item}-repacked.img")
            self.console.log(f"Repack complete", "SUCCESS")
            if QMessageBox.question(self, 'Success', "Repacked! Open output folder?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                open_folder(self.image_manager.output_path)

    def handle_info(self):
        if not self.current_item: return
        self.console.start_progress()
        self.console.log("Fetching detailed info...", "INFO")
        target = self.current_item if self.current_type == "RAW" else f"{self.current_item}.img"
        info = self.image_manager.get_info(target)
        for line in str(info).split('\n'):
            if line.strip(): self.console.log(line.strip(), "INFO")
        self.console.stop_progress()

    # --- AVB MASTER TOOL LOGIC ---
    def browse_avb_file(self, target_edit):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", "All Files (*)")
        if path:
            target_edit.setText(path)

    def avb_console_cb(self, message):
        self.avb_console.log(message, "AVB_TOOL")

    def run_avb_verify(self):
        img = self.avb_v_img.text().strip()
        key = self.avb_v_key.text().strip()
        if not img:
            QMessageBox.warning(self, "Input Error", "Please select a target image for verification.")
            return
            
        self.avb_console.start_progress()
        self.worker = WorkerThread(self.image_manager.avb_verify_image, img, key_path=(key if key else None))
        self.worker.log_signal.connect(self.avb_console_cb)
        self.worker.finished.connect(lambda s, r: self.avb_console.stop_progress() or self.avb_console.log("Integrity verified successfully!" if s else "Verification failed.", "SUCCESS" if s else "ERROR"))
        self.worker.start()

    def run_avb_footer(self):
        img = self.avb_f_img.text().strip()
        name = self.avb_f_name.text().strip()
        size = self.avb_f_size.text().strip()
        if not img or not name or not size:
            QMessageBox.warning(self, "Input Error", "All fields are required for footer appending.")
            return

        self.avb_console.start_progress()
        self.worker = WorkerThread(self.image_manager.avb_add_hash_footer, img, name, size)
        self.worker.log_signal.connect(self.avb_console_cb)
        self.worker.finished.connect(lambda s, r: self.avb_console.stop_progress() or self.avb_console.log("Hash footer applied successfully!" if s else "Failed to apply hash footer.", "SUCCESS" if s else "ERROR"))
        self.worker.start()

    def run_avb_patch(self):
        img = self.avb_s_img.text().strip()
        key = self.avb_s_key.text().strip()
        roll = self.avb_s_roll.text().strip()
        alg = self.avb_s_alg.currentText()
        if not img:
            QMessageBox.warning(self, "Input Error", "Please select a target image to sign/patch.")
            return

        self.avb_console.start_progress()
        self.worker = WorkerThread(self.image_manager.avb_patch_vbmeta, img, 
                                   rollback_index=(int(roll) if roll.isdigit() else 0),
                                   key_path=(key if key else None),
                                   algorithm=(alg if key else None))
        self.worker.log_signal.connect(self.avb_console_cb)
        self.worker.finished.connect(lambda s, r: self.avb_console.stop_progress() or self.avb_console.log("Signature & Rollback settings applied successfully!" if s else "Failed to patch settings.", "SUCCESS" if s else "ERROR"))
        self.worker.start()

    def run_avb_info(self):
        img = self.avb_i_img.text().strip()
        if not img:
            QMessageBox.warning(self, "Input Error", "Please select an image to analyze.")
            return
        
        self.avb_console.start_progress()
        try:
            info = self.image_manager.avb_info_image(img)
            for line in info.split('\n'):
                if line.strip(): self.avb_console.log(line.strip(), "INFO")
        except Exception as e:
            self.avb_console.log(f"Error: {str(e)}", "ERROR")
        self.avb_console.stop_progress()

    def run_avb_generate_vbmeta(self):
        while True:
            name, ok = QInputDialog.getText(self, 'Generate VBMeta', 'Enter filename (no extension):', QLineEdit.EchoMode.Normal, "vbmeta_patched")
            if not ok or not name:
                return
                
            filename = name.strip()
            if not filename.endswith('.img'):
                filename += '.img'
            
            dest_path = os.path.join(self.image_manager.output_path, filename)
            if os.path.exists(dest_path):
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("File Exists")
                msg_box.setText(f"The file '{filename}' already exists.")
                msg_box.setInformativeText("Do you want to replace the existing file or choose a different name?")
                replace_btn = msg_box.addButton("Replace", QMessageBox.ButtonRole.AcceptRole)
                rename_btn = msg_box.addButton("Rename", QMessageBox.ButtonRole.ActionRole)
                cancel_btn = msg_box.addButton(QMessageBox.StandardButton.Cancel)
                
                msg_box.exec()
                
                if msg_box.clickedButton() == rename_btn:
                    continue
                elif msg_box.clickedButton() == cancel_btn:
                    return
            
            self.avb_console.start_progress()
            self.avb_console.log(f"Generating standalone disabled VBMeta: {filename}...", "INFO")
            
            self.worker = WorkerThread(self.image_manager.generate_empty_vbmeta, filename)
            self.worker.log_signal.connect(self.avb_console_cb)
            self.worker.finished.connect(lambda s, res: self.avb_console.stop_progress() or self.avb_console.log("VBMeta generation complete." if s else f"Error: {res}", "SUCCESS" if s else "ERROR"))
            self.worker.start()
            break

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Use a cross-platform font
    font = QFont("Sans Serif", 10)
    
    app.setStyleSheet(f"""
        QMessageBox, QDialog, QInputDialog {{
            background-color: {BG_COLOR};
        }}
        QMessageBox QLabel, QDialog QLabel, QInputDialog QLabel {{
            color: {TEXT_PRIMARY};
            font-size: 10pt;
        }}
        QPushButton {{
            background-color: #3b82f6;
            color: white;
            padding: 6px 20px;
            border-radius: 4px;
            font-weight: bold;
            border: none;
        }}
        QPushButton:hover {{
            background-color: #2563eb;
        }}
        QLineEdit {{
            background-color: #1f2937;
            border: 1px solid {CARD_BORDER};
            border-radius: 4px;
            color: {TEXT_PRIMARY};
            padding: 5px;
            selection-background-color: #3b82f6;
        }}
    """)
    
    window = BootlyApp()
    window.show()
    sys.exit(app.exec())
