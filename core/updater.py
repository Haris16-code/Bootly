import os
import sys
import sys
import json
import urllib.request
import zipfile
import subprocess
import shutil
from PyQt6.QtCore import QThread, pyqtSignal

CURRENT_VERSION = "1.0"
UPDATE_JSON_URL = "https://github.com/Haris16-code/Bootly/raw/refs/heads/main/data/updates/update.json"

def is_binary():
    return getattr(sys, 'frozen', False)

class UpdateCheckerThread(QThread):
    finished = pyqtSignal(bool, dict, str)

    def run(self):
        try:
            req = urllib.request.Request(UPDATE_JSON_URL, headers={'User-Agent': 'BootlyUpdater/1.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                
                # Compare versions simply
                remote_ver = data.get("latest_version", "0.0")
                if self._parse_ver(remote_ver) > self._parse_ver(CURRENT_VERSION):
                    self.finished.emit(True, data, "")
                else:
                    self.finished.emit(False, {}, "Already up to date.")
        except Exception as e:
            self.finished.emit(False, {}, str(e))

    def _parse_ver(self, v_str):
        try:
            return [int(x) for x in v_str.replace('v', '').split('.')]
        except:
            return [0]

class UpdateDownloaderThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, data, base_path):
        super().__init__()
        self.data = data
        self.base_path = base_path

    def run(self):
        try:
            temp_dir = os.path.join(self.base_path, "temp_update")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)

            url = self.data.get("binary_url") if is_binary() else self.data.get("source_url")
            if not url:
                self.finished.emit(False, "No suitable update URL found in JSON.")
                return

            req = urllib.request.Request(url, headers={'User-Agent': 'BootlyUpdater/1.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                total_size = int(response.info().get('Content-Length', 0))
                
                dest_file = os.path.join(temp_dir, "update.exe" if is_binary() else "update.zip")
                
                downloaded = 0
                with open(dest_file, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk: break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = int((downloaded / total_size) * 100)
                            self.progress.emit(pct)

            if not is_binary():
                # Extract zip
                with zipfile.ZipFile(dest_file, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                os.remove(dest_file)

            self.finished.emit(True, temp_dir)

        except Exception as e:
            self.finished.emit(False, str(e))

def apply_update(temp_dir, base_path):
    bat_path = os.path.join(base_path, "updater.bat")
    
    if is_binary():
        target_exe = sys.executable
        new_exe = os.path.join(temp_dir, "update.exe")
        bat_content = f"""@echo off
timeout /t 2 /nobreak > nul
copy /Y "{new_exe}" "{target_exe}"
start "" "{target_exe}"
rmdir /s /q "{temp_dir}"
del "%~f0"
"""
    else:
        # Find inner folder natively extracted by github zip
        inner_folder = temp_dir
        for item in os.listdir(temp_dir):
            full_path = os.path.join(temp_dir, item)
            if os.path.isdir(full_path) and len(os.listdir(temp_dir)) == 1:
                inner_folder = full_path
                break
                
        bat_content = f"""@echo off
timeout /t 2 /nobreak > nul
xcopy /s /y /q "{inner_folder}\\*" "{base_path}\\"
start "" python "{os.path.join(base_path, 'main.py')}"
rmdir /s /q "{temp_dir}"
del "%~f0"
"""

    with open(bat_path, "w") as f:
        f.write(bat_content)

    # Detach bat execution
    subprocess.Popen([bat_path], creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS)
    sys.exit(0)
