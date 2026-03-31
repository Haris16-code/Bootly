import os
import shutil
import subprocess

def get_bin_path(utility):
    """Returns the absolute path to a utility in the bin directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, 'bin', f"{utility}.exe")

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
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True,
            text=True,
            cwd=cwd
        )
        return process
    except Exception as e:
        return str(e)
