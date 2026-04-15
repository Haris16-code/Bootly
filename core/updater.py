import os
import sys
import sys
import json
import urllib.request
import zipfile
import subprocess
import shutil
from PyQt6.QtCore import QThread, pyqtSignal

CURRENT_VERSION = "1.2"
UPDATE_JSON_URL = "https://raw.githubusercontent.com/Haris16-code/Bootly/refs/heads/main/data/updates/update.json"

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

            # Dest file should always be a zip for this optimized flow
            dest_file = os.path.join(temp_dir, "update.zip")
            
            req = urllib.request.Request(url, headers={'User-Agent': 'BootlyUpdater/1.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                total_size = int(response.info().get('Content-Length', 0))
                
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

            # Extract zip
            with zipfile.ZipFile(dest_file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Clean up zip
            try:
                os.remove(dest_file)
            except:
                pass

            self.finished.emit(True, temp_dir)

        except Exception as e:
            self.finished.emit(False, str(e))

def apply_update(temp_dir, base_path):
    """Creates a script to replace existing files and restarts the app."""
    # Find inner folder natively extracted by github zip or others
    inner_folder = temp_dir
    possible_inner = [os.path.join(temp_dir, d) for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
    if len(possible_inner) == 1 and len(os.listdir(temp_dir)) == 1:
        inner_folder = possible_inner[0]

    # Detect if we are a compiled binary
    target_exe = sys.executable
    is_compiled = is_binary()
    
    # We only auto-replace for Windows Binaries
    if sys.platform == "win32" and is_compiled:
        bat_path = os.path.join(base_path, "updater.bat")
        
        # We use robocopy for better exclusion and reliability if available, otherwise xcopy
        # /MIR mirrors, but we don't want to delete input/output folders
        # /E copies subdirectories, including empty ones.
        # /Y suppresses prompting to confirm you want to overwrite an existing destination file.
        # We exclude input and output folders to preserve user data
        bat_content = f"""@echo off
title Bootly Auto-Updater
echo Waiting for Bootly to close...
timeout /t 2 /nobreak > nul

echo Updating files...
xcopy /s /y /q /i "{inner_folder}\\*" "{base_path}\\" /exclude:exclude_list.txt 2>nul
if %errorlevel% leq 4 (
    echo Update applied successfully.
) else (
    echo Error during update: %errorlevel%
)

echo Restarting Bootly...
start "" "{target_exe}"

echo Cleaning up...
rmdir /s /q "{temp_dir}"
del "exclude_list.txt"
del "%~f0"
"""
        # Create exclude list for xcopy
        exclude_path = os.path.join(base_path, "exclude_list.txt")
        with open(exclude_path, "w") as f:
            f.write("\\input\\\n")
            f.write("\\output\\\n")
            f.write("updater.bat\n")
            f.write("exclude_list.txt\n")

        with open(bat_path, "w") as f:
            f.write(bat_content)

        # Detach bat execution
        subprocess.Popen([bat_path], creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS, cwd=base_path)
        sys.exit(0)
    else:
        # For non-windows or non-binary, this function shouldn't be called if we follow the new plan
        # but as a safety measure, we do nothing or just log
        pass
