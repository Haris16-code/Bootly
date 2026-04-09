import os
import shutil
import subprocess
import platform

def get_os():
    """Returns the current operating system (windows, linux, darwin)."""
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    elif system == "darwin":
        return "macos"
    return "linux"

def open_folder(path):
    """Opens a folder in the native file explorer."""
    os_type = get_os()
    if os_type == "windows":
        os.startfile(path)
    elif os_type == "macos":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])

def get_bin_path(utility):
    """Returns the absolute path to a utility or script."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os_type = get_os()
    
    # Tools implemented as Python scripts
    python_scripts = ['mkbootimg', 'unpack_bootimg', 'repack_bootimg', 'avbtool']
    
    # Mapping for Windows binaries if different from script name
    win_bin_map = {
        'unpack_bootimg': 'unpackbootimg'
    }
    
    if utility in python_scripts:
        script_path = os.path.join(base_dir, 'bin', 'scripts', f"{utility}.py")
        if os_type == "windows":
            win_name = win_bin_map.get(utility, utility)
            bin_path = os.path.join(base_dir, 'bin', f"{win_name}.exe")
            if os.path.exists(bin_path):
                return bin_path
            return script_path
        else:
            return script_path

    # Standard utilities
    if os_type == "windows":
        return os.path.join(base_dir, 'bin', f"{utility}.exe")
    else:
        # On Linux/Mac, assume standard utilities are in PATH
        # We check common names
        return utility

def ensure_dir(directory):
    """Ensures a directory exists."""
    if not os.path.exists(directory):
        os.makedirs(directory)

def clear_dir(directory):
    """Deletes all contents of a directory."""
    if os.path.exists(directory):
        shutil.rmtree(directory)
        os.makedirs(directory)

def run_command(command, cwd=None):
    """Runs a shell command and returns the output."""
    try:
        # Use shell=True for complex piping, but on Mac/Linux handle lists properly
        if isinstance(command, list):
            cmd_str = " ".join(command)
        else:
            cmd_str = command
            
        process = subprocess.Popen(
            cmd_str,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True,
            text=True,
            cwd=cwd
        )
        return process
    except Exception as e:
        return str(e)
