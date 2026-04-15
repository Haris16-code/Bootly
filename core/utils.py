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

def get_linux_distro():
    """Identifies the Linux distribution type."""
    if get_os() != "linux":
        return None
    try:
        with open("/etc/os-release", "r") as f:
            content = f.read().lower()
            if "debian" in content or "ubuntu" in content or "pop" in content or "mint" in content:
                return "debian"
            if "fedora" in content or "rhel" in content or "centos" in content:
                return "fedora"
            if "arch" in content or "manjaro" in content:
                return "arch"
    except:
        pass
    return "generic"

def open_folder(path):
    """Opens a folder in the native file explorer."""
    os_type = get_os()
    if os_type == "windows":
        os.startfile(path)
    elif os_type == "macos":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])

def get_adb_path():
    """Returns the path to adb, checking internal bin folder then system PATH."""
    return get_bin_path("adb")

def get_fastboot_path():
    """Returns the path to fastboot, checking internal bin folder then system PATH."""
    return get_bin_path("fastboot")

def install_adb_fastboot(callback=None):
    """Runs OS-specific commands to install ADB and Fastboot."""
    os_type = get_os()
    cmd = None
    
    if os_type == "windows":
        cmd = "winget install -e --id Google.PlatformTools"
    elif os_type == "macos":
        cmd = "brew install --cask android-platform-tools"
    elif os_type == "linux":
        distro = get_linux_distro()
        if distro == "debian":
            cmd = "pkexec apt-get update && pkexec apt-get install -y android-sdk-platform-tools"
        elif distro == "fedora":
            cmd = "pkexec dnf install -y android-tools"
        elif distro == "arch":
            cmd = "pkexec pacman -S --noconfirm android-tools"
        else:
            return False, "Unsupported Linux distribution for auto-install."
            
    if not cmd:
        return False, "Unsupported OS for auto-install."
        
    if callback: callback(f"Executing: {cmd}")
    try:
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            if callback: callback(line.strip())
        process.wait()
        return process.returncode == 0, "Installation finished." if process.returncode == 0 else f"Process exited with code {process.returncode}"
    except Exception as e:
        return False, str(e)

def get_bin_path(utility):
    """
    Intelligently resolves the path to a binary tool or script.
    Search priority: bin/magisk -> bin/ -> bin/scripts/ -> Project Root -> system PATH.
    Handles .exe extension on Windows automatically.
    """
    os_type = get_os()
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ext = ".exe" if os_type == "windows" else ""
    
    # List of possible locations in order of priority
    search_dirs = [
        os.path.join(base_dir, 'bin', 'magisk'),
        os.path.join(base_dir, 'bin'),
        os.path.join(base_dir, 'bin', 'scripts'),
        base_dir # Root folder
    ]
    
    python_scripts = {"avbtool", "mkbootimg", "unpack_bootimg", "repack_bootimg", "sdat2img"}
    
    # 1. Check for binary versions first with current OS extension (e.g. adb.exe or magiskboot.exe)
    if ext:
        for d in search_dirs:
            bin_path = os.path.join(d, f"{utility}{ext}")
            if os.path.exists(bin_path):
                return bin_path
            
    # 2. Check for exact name (handles Linux/Mac binaries or tools without extension)
    for d in search_dirs:
        bin_path = os.path.join(d, utility)
        if os.path.exists(bin_path) and not os.path.isdir(bin_path):
            return bin_path

    # 3. Check for Python scripts if it's a known script
    if utility in python_scripts:
        script_path = os.path.join(base_dir, 'bin', 'scripts', f"{utility}.py")
        if os.path.exists(script_path):
            return script_path

    # 4. Fallback to system PATH
    sys_path = shutil.which(utility)
    if sys_path:
        return sys_path
        
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
