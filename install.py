#!/usr/bin/env python3
"""
Installation script for LED Tape Light System.
"""
import os
import sys
import platform
import subprocess
import shutil
import argparse
import logging
from typing import List, Dict, Any, Optional

# Import system checker
try:
    from system_checker import ensure_dependencies, detect_system
except ImportError:
    print("Error: system_checker.py not found.")
    print("Please make sure you are running this script from the project root directory.")
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Installer")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Install LED Tape Light System")
    parser.add_argument("--no-deps", action="store_true", help="Skip dependency installation")
    parser.add_argument("--force", action="store_true", help="Force installation even if already installed")
    parser.add_argument("--install-dir", type=str, default=None, help="Installation directory")
    return parser.parse_args()


def check_python_version() -> bool:
    """
    Check if Python version is compatible.
    
    Returns:
        bool: True if Python version is compatible
    """
    major, minor, _ = platform.python_version_tuple()
    
    if int(major) < 3 or (int(major) == 3 and int(minor) < 7):
        logger.error("Python 3.7 or newer is required")
        return False
        
    return True


def create_virtual_environment(venv_dir: str) -> bool:
    """
    Create a virtual environment.
    
    Args:
        venv_dir (str): Path to virtual environment directory
        
    Returns:
        bool: True if successful
    """
    logger.info(f"Creating virtual environment at {venv_dir}")
    
    try:
        subprocess.check_call([sys.executable, "-m", "venv", venv_dir])
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error creating virtual environment: {e}")
        return False


def get_venv_python(venv_dir: str) -> str:
    """
    Get the path to the Python executable in the virtual environment.
    
    Args:
        venv_dir (str): Path to virtual environment directory
        
    Returns:
        str: Path to Python executable
    """
    if platform.system() == "Windows":
        return os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        return os.path.join(venv_dir, "bin", "python")


def copy_project_files(src_dir: str, dest_dir: str) -> bool:
    """
    Copy project files to installation directory.
    
    Args:
        src_dir (str): Source directory
        dest_dir (str): Destination directory
        
    Returns:
        bool: True if successful
    """
    logger.info(f"Copying project files from {src_dir} to {dest_dir}")
    
    try:
        # Create destination directory if it doesn't exist
        os.makedirs(dest_dir, exist_ok=True)
        
        # Copy all Python files
        for root, _, files in os.walk(src_dir):
            # Skip virtual environment directories
            if "venv" in root or ".env" in root or "__pycache__" in root:
                continue
                
            # Get relative path from source directory
            rel_path = os.path.relpath(root, src_dir)
            
            # Create corresponding directory in destination
            dest_path = os.path.join(dest_dir, rel_path)
            os.makedirs(dest_path, exist_ok=True)
            
            # Copy files
            for file in files:
                if file.endswith(".py") or file.endswith(".md") or file.endswith(".txt"):
                    src_file = os.path.join(root, file)
                    dest_file = os.path.join(dest_path, file)
                    shutil.copy2(src_file, dest_file)
                    
        return True
        
    except Exception as e:
        logger.error(f"Error copying project files: {e}")
        return False


def create_launcher(install_dir: str) -> bool:
    """
    Create a launcher script for the application.
    
    Args:
        install_dir (str): Installation directory
        
    Returns:
        bool: True if successful
    """
    logger.info("Creating launcher script")
    
    try:
        venv_python = get_venv_python(os.path.join(install_dir, "venv"))
        
        if platform.system() == "Windows":
            # Create a .bat file for Windows
            launcher_path = os.path.join(install_dir, "run_led_system.bat")
            
            with open(launcher_path, "w") as f:
                f.write(f'@echo off\n')
                f.write(f'echo Starting LED Tape Light System...\n')
                f.write(f'"{venv_python}" "{os.path.join(install_dir, "main.py")}"\n')
                f.write(f'if errorlevel 1 pause\n')
                
        else:
            # Create a shell script for Unix-like systems
            launcher_path = os.path.join(install_dir, "run_led_system.sh")
            
            with open(launcher_path, "w") as f:
                f.write(f'#!/bin/bash\n')
                f.write(f'echo "Starting LED Tape Light System..."\n')
                f.write(f'"{venv_python}" "{os.path.join(install_dir, "main.py")}"\n')
                
            # Make it executable
            os.chmod(launcher_path, 0o755)
            
        logger.info(f"Created launcher: {launcher_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating launcher: {e}")
        return False


def install_system(args):
    """
    Install LED Tape Light System.
    
    Args:
        args: Command line arguments
    """
    logger.info("Starting installation of LED Tape Light System")
    
    # Check Python version
    if not check_python_version():
        logger.error("Installation aborted: Python version incompatible")
        return False
        
    # Determine installation directory
    if args.install_dir:
        install_dir = args.install_dir
    else:
        # Default to user's home directory
        home_dir = os.path.expanduser("~")
        install_dir = os.path.join(home_dir, "led_tape_system")
        
    logger.info(f"Installation directory: {install_dir}")
    
    # Check if already installed
    if os.path.exists(install_dir) and not args.force:
        logger.warning(f"Installation directory already exists: {install_dir}")
        logger.warning("Use --force to overwrite existing installation")
        return False
        
    # Create installation directory
    os.makedirs(install_dir, exist_ok=True)
    
    # Create virtual environment
    venv_dir = os.path.join(install_dir, "venv")
    if not create_virtual_environment(venv_dir):
        logger.error("Installation aborted: Failed to create virtual environment")
        return False
        
    # Install dependencies
    if not args.no_deps:
        logger.info("Installing dependencies...")
        
        # Get path to Python in virtual environment
        venv_python = get_venv_python(venv_dir)
        
        # Install system_checker first
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            checker_path = os.path.join(script_dir, "system_checker.py")
            dest_checker_path = os.path.join(install_dir, "system_checker.py")
            
            # Copy system_checker.py to installation directory
            shutil.copy2(checker_path, dest_checker_path)
            
            # Run system_checker with virtual environment Python
            subprocess.check_call([venv_python, dest_checker_path])
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error installing dependencies: {e}")
            logger.warning("Installation will continue, but some features may not work")
            
    # Copy project files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not copy_project_files(script_dir, install_dir):
        logger.error("Installation aborted: Failed to copy project files")
        return False
        
    # Create launcher
    if not create_launcher(install_dir):
        logger.warning("Failed to create launcher script")
        
    logger.info("Installation completed successfully")
    
    if platform.system() == "Windows":
        logger.info(f"You can run the system using: {os.path.join(install_dir, 'run_led_system.bat')}")
    else:
        logger.info(f"You can run the system using: {os.path.join(install_dir, 'run_led_system.sh')}")
        
    return True


def main():
    """
    Main function.
    """
    print("LED Tape Light System - Installer")
    print("----------------------------------")
    
    args = parse_args()
    
    if install_system(args):
        print("\nInstallation completed successfully!")
    else:
        print("\nInstallation failed or was aborted.")
        sys.exit(1)


if __name__ == "__main__":
    main()