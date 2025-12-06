#!/usr/bin/env python3
"""
Job Tracker - Easy Installer
============================
This script sets up everything you need to run Job Tracker.
Just run: python install.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header():
    print(f"""
{Colors.BLUE}{Colors.BOLD}
     ╦╔═╗╔╗   ╔╦╗╦═╗╔═╗╔═╗╦╔═╔═╗╦═╗
     ║║ ║╠╩╗   ║ ╠╦╝╠═╣║  ╠╩╗║╣ ╠╦╝
    ╚╝╚═╝╚═╝   ╩ ╩╚═╩ ╩╚═╝╩ ╩╚═╝╩╚═
{Colors.END}
    Easy Installer for Job Tracker
    ===============================
    """)

def print_step(step, message):
    print(f"{Colors.BLUE}[{step}]{Colors.END} {message}")

def print_success(message):
    print(f"{Colors.GREEN}✓{Colors.END} {message}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠{Colors.END} {message}")

def print_error(message):
    print(f"{Colors.RED}✗{Colors.END} {message}")

def check_python_version():
    """Check if Python version is 3.9+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print_error(f"Python 3.9+ required. You have {version.major}.{version.minor}")
        print("Please install a newer version of Python from https://python.org")
        return False
    print_success(f"Python {version.major}.{version.minor} detected")
    return True

def create_virtual_environment():
    """Create a virtual environment if it doesn't exist."""
    venv_path = Path("venv")
    if venv_path.exists():
        print_success("Virtual environment already exists")
        return True

    print_step("2", "Creating virtual environment...")
    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print_success("Virtual environment created")
        return True
    except subprocess.CalledProcessError:
        print_error("Failed to create virtual environment")
        return False

def get_pip_command():
    """Get the correct pip command for the virtual environment."""
    if sys.platform == "win32":
        return str(Path("venv/Scripts/pip.exe"))
    return str(Path("venv/bin/pip"))

def get_python_command():
    """Get the correct python command for the virtual environment."""
    if sys.platform == "win32":
        return str(Path("venv/Scripts/python.exe"))
    return str(Path("venv/bin/python"))

def install_dependencies():
    """Install required packages."""
    print_step("3", "Installing dependencies (this may take a minute)...")
    pip = get_pip_command()

    try:
        # Upgrade pip first
        subprocess.run([pip, "install", "--upgrade", "pip"],
                      check=True, capture_output=True)

        # Install requirements
        subprocess.run([pip, "install", "-r", "requirements.txt"],
                      check=True, capture_output=True)
        print_success("Dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print_error("Failed to install dependencies")
        print(e.stderr.decode() if e.stderr else "Unknown error")
        return False

def setup_directories():
    """Create necessary directories."""
    print_step("4", "Setting up directories...")

    dirs = ["data", "data/resumes", "config"]
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

    print_success("Directories created")
    return True

def setup_config():
    """Set up configuration files."""
    print_step("5", "Setting up configuration...")

    env_path = Path("config/.env")
    env_example = Path("config/.env.example")

    if not env_path.exists() and env_example.exists():
        shutil.copy(env_example, env_path)
        print_success("Created config/.env from template")
    elif not env_path.exists():
        # Create a basic .env file
        with open(env_path, 'w') as f:
            f.write("# Job Tracker Configuration\n")
            f.write("# Add your OpenAI API key for email classification (optional)\n")
            f.write("# OPENAI_API_KEY=your-key-here\n")
        print_success("Created config/.env")
    else:
        print_success("Configuration file exists")

    return True

def create_start_script():
    """Create easy start scripts for different platforms."""
    print_step("6", "Creating start scripts...")

    # Unix/Mac start script
    unix_script = """#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
echo ""
echo "Starting Job Tracker..."
echo "Open http://localhost:8000 in your browser"
echo "Press Ctrl+C to stop"
echo ""
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

    with open("start.sh", 'w') as f:
        f.write(unix_script)
    os.chmod("start.sh", 0o755)

    # Windows start script
    windows_script = """@echo off
cd /d "%~dp0"
call venv\\Scripts\\activate.bat
echo.
echo Starting Job Tracker...
echo Open http://localhost:8000 in your browser
echo Press Ctrl+C to stop
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
"""

    with open("start.bat", 'w') as f:
        f.write(windows_script)

    print_success("Created start.sh (Mac/Linux) and start.bat (Windows)")
    return True

def print_next_steps():
    """Print instructions for the user."""
    python_cmd = get_python_command()

    print(f"""
{Colors.GREEN}{Colors.BOLD}Installation Complete!{Colors.END}
{Colors.GREEN}======================{Colors.END}

{Colors.BOLD}To start Job Tracker:{Colors.END}

  Mac/Linux:  ./start.sh
  Windows:    start.bat

  Or manually: {python_cmd} -m uvicorn app.main:app --host 0.0.0.0 --port 8000

{Colors.BOLD}Then open:{Colors.END} http://localhost:8000

{Colors.BOLD}Optional Setup:{Colors.END}

  1. Gmail Sync: Add your Gmail API credentials to config/
     - See the Email Sync page for instructions

  2. AI Classification: Add your OpenAI API key to config/.env
     - Get a key at https://platform.openai.com/api-keys

{Colors.BOLD}Access from your phone:{Colors.END}

  Find your computer's IP address and open:
  http://YOUR_IP:8000 on your phone's browser
  (Make sure you're on the same WiFi network)

{Colors.YELLOW}Need help?{Colors.END} Visit the Email Sync page for setup guides.
""")

def main():
    print_header()

    # Change to script directory
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)

    print_step("1", "Checking Python version...")
    if not check_python_version():
        return 1

    if not create_virtual_environment():
        return 1

    if not install_dependencies():
        return 1

    if not setup_directories():
        return 1

    if not setup_config():
        return 1

    if not create_start_script():
        return 1

    print_next_steps()
    return 0

if __name__ == "__main__":
    sys.exit(main())
