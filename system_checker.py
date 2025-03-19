"""
System checker for LED Tape Light System.
Detects system configuration and installs required dependencies.
"""
import platform
import subprocess
import sys
import os
import logging
from typing import Dict, List, Tuple, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SystemChecker")

# System categories
WINDOWS_INTEL = "windows_intel"
WINDOWS_AMD = "windows_amd"
MAC_INTEL = "mac_intel"
MAC_ARM = "mac_arm"
LINUX_INTEL = "linux_intel"
LINUX_AMD = "linux_amd"
LINUX_ARM = "linux_arm"
UNKNOWN = "unknown"

# Base dependencies required for all systems
BASE_DEPS = [
    "pygame>=2.1.0",
    "numpy>=1.20.0",
    "python-osc>=1.8.0",
    "psutil>=5.8.0"
]

# GPU acceleration dependencies
CUDA_DEPS = ["numba>=0.54.0"]
OPENCL_DEPS = ["pyopencl>=2021.1"]

# System-specific dependencies
SYSTEM_DEPS = {
    WINDOWS_INTEL: BASE_DEPS + CUDA_DEPS + OPENCL_DEPS,
    WINDOWS_AMD: BASE_DEPS + OPENCL_DEPS,
    MAC_INTEL: BASE_DEPS + OPENCL_DEPS,
    MAC_ARM: BASE_DEPS,  # M1/M2/M3 Macs have limited GPU acceleration support
    LINUX_INTEL: BASE_DEPS + CUDA_DEPS + OPENCL_DEPS,
    LINUX_AMD: BASE_DEPS + OPENCL_DEPS,
    LINUX_ARM: BASE_DEPS,
    UNKNOWN: BASE_DEPS
}


def detect_system() -> str:
    """
    Detect the current system type.
    
    Returns:
        str: System category
    """
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    logger.info(f"Detected system: {system} on {machine}")
    
    if system == "windows":
        # Check if AMD or Intel
        cpu_info = platform.processor().lower()
        if "amd" in cpu_info:
            return WINDOWS_AMD
        else:
            return WINDOWS_INTEL
            
    elif system == "darwin":  # macOS
        if machine == "arm64":
            return MAC_ARM
        else:
            return MAC_INTEL
            
    elif system == "linux":
        # Check architecture
        if "arm" in machine or "aarch" in machine:
            return LINUX_ARM
        else:
            # Check CPU vendor
            try:
                with open("/proc/cpuinfo", "r") as f:
                    cpu_info = f.read().lower()
                    if "amd" in cpu_info:
                        return LINUX_AMD
                    else:
                        return LINUX_INTEL
            except:
                # Default to Intel if we can't determine
                return LINUX_INTEL
                
    return UNKNOWN


def check_nvidia_gpu() -> bool:
    """
    Check if NVIDIA GPU is available.
    
    Returns:
        bool: True if NVIDIA GPU is detected
    """
    system = platform.system().lower()
    
    if system == "windows":
        try:
            output = subprocess.check_output("wmic path win32_VideoController get name", shell=True).decode()
            return "nvidia" in output.lower()
        except:
            return False
            
    elif system == "darwin":
        # macOS rarely has NVIDIA GPUs in modern systems
        return False
        
    elif system == "linux":
        try:
            output = subprocess.check_output("lspci | grep -i nvidia", shell=True).decode()
            return len(output) > 0
        except:
            return False
            
    return False


def check_amd_gpu() -> bool:
    """
    Check if AMD GPU is available.
    
    Returns:
        bool: True if AMD GPU is detected
    """
    system = platform.system().lower()
    
    if system == "windows":
        try:
            output = subprocess.check_output("wmic path win32_VideoController get name", shell=True).decode()
            return "amd" in output.lower() or "radeon" in output.lower()
        except:
            return False
            
    elif system == "darwin":
        # Many Macs have AMD GPUs
        try:
            output = subprocess.check_output("system_profiler SPDisplaysDataType", shell=True).decode()
            return "amd" in output.lower() or "radeon" in output.lower()
        except:
            return False
            
    elif system == "linux":
        try:
            output = subprocess.check_output("lspci | grep -i amd", shell=True).decode()
            return len(output) > 0
        except:
            try:
                output = subprocess.check_output("lspci | grep -i radeon", shell=True).decode()
                return len(output) > 0
            except:
                return False
                
    return False


def check_cuda_availability() -> bool:
    """
    Check if CUDA is available.
    
    Returns:
        bool: True if CUDA is available
    """
    try:
        output = subprocess.check_output("nvcc --version", shell=True).decode()
        return "cuda" in output.lower()
    except:
        return False


def check_opencl_availability() -> bool:
    """
    Check if OpenCL is available.
    
    Returns:
        bool: True if OpenCL is available
    """
    system = platform.system().lower()
    
    if system == "windows":
        # Check for OpenCL DLLs
        opencl_paths = [
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "System32", "OpenCL.dll"),
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "SysWOW64", "OpenCL.dll")
        ]
        return any(os.path.exists(path) for path in opencl_paths)
        
    elif system == "darwin":
        # OpenCL is typically available on macOS
        return True
        
    elif system == "linux":
        # Check for OpenCL libraries
        opencl_paths = [
            "/usr/lib/libOpenCL.so",
            "/usr/lib64/libOpenCL.so",
            "/usr/local/lib/libOpenCL.so"
        ]
        return any(os.path.exists(path) for path in opencl_paths)
        
    return False


def get_required_packages(system_type: str) -> List[str]:
    """
    Get the required packages for the given system type.
    
    Args:
        system_type (str): System category
        
    Returns:
        List[str]: List of required packages
    """
    packages = SYSTEM_DEPS.get(system_type, BASE_DEPS).copy()
    
    # Check for GPU acceleration capabilities
    has_nvidia = check_nvidia_gpu()
    has_amd = check_amd_gpu()
    has_cuda = check_cuda_availability()
    has_opencl = check_opencl_availability()
    
    logger.info(f"GPU detection: NVIDIA: {has_nvidia}, AMD: {has_amd}")
    logger.info(f"Acceleration: CUDA: {has_cuda}, OpenCL: {has_opencl}")
    
    # Adjust packages based on GPU detection
    if system_type in [WINDOWS_INTEL, LINUX_INTEL] and has_nvidia and has_cuda:
        # Make sure CUDA packages are included
        for pkg in CUDA_DEPS:
            if pkg not in packages:
                packages.append(pkg)
                
    if (has_nvidia or has_amd) and has_opencl:
        # Make sure OpenCL packages are included
        for pkg in OPENCL_DEPS:
            if pkg not in packages:
                packages.append(pkg)
                
    return packages


def check_installed_packages() -> Dict[str, bool]:
    """
    Check which packages are already installed.
    
    Returns:
        Dict[str, bool]: Dictionary of package status
    """
    installed = {}
    
    for package in BASE_DEPS + CUDA_DEPS + OPENCL_DEPS:
        # Extract package name (without version)
        pkg_name = package.split(">=")[0].split("==")[0].strip()
        
        try:
            __import__(pkg_name)
            installed[package] = True
        except ImportError:
            installed[package] = False
            
    return installed


def install_packages(packages: List[str]) -> bool:
    """
    Install the given packages using pip.
    
    Args:
        packages (List[str]): List of packages to install
        
    Returns:
        bool: True if all packages were installed successfully
    """
    if not packages:
        logger.info("No packages to install")
        return True
        
    logger.info(f"Installing packages: {', '.join(packages)}")
    
    try:
        # Use subprocess to call pip
        cmd = [sys.executable, "-m", "pip", "install"] + packages
        subprocess.check_call(cmd)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error installing packages: {e}")
        return False


def ensure_dependencies(auto_install: bool = False) -> Tuple[bool, List[str]]:
    """
    Ensure that all required dependencies are installed.
    
    Args:
        auto_install (bool): Whether to automatically install missing packages
        
    Returns:
        Tuple[bool, List[str]]: (Success status, Missing packages)
    """
    # Detect system type
    system_type = detect_system()
    logger.info(f"Detected system type: {system_type}")
    
    # Get required packages
    required_packages = get_required_packages(system_type)
    logger.info(f"Required packages: {required_packages}")
    
    # Check installed packages
    installed = check_installed_packages()
    
    # Find missing packages
    missing = [pkg for pkg in required_packages if not installed.get(pkg, False)]
    
    if not missing:
        logger.info("All required packages are already installed")
        return True, []
        
    logger.info(f"Missing packages: {missing}")
    
    if auto_install:
        # Install missing packages
        success = install_packages(missing)
        return success, [] if success else missing
    
    return False, missing


def main():
    """
    Main function.
    """
    print("LED Tape Light System - Dependency Checker")
    print("------------------------------------------")
    print(f"Python version: {platform.python_version()}")
    print(f"System: {platform.system()} {platform.release()} ({platform.machine()})")
    print()
    
    # Check dependencies
    success, missing = ensure_dependencies(auto_install=True)
    
    if success:
        print("All dependencies are installed.")
        print("You can now run the LED Tape Light System.")
    else:
        print("Some dependencies could not be installed automatically.")
        print("Please install the following packages manually:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\nYou can install them using:")
        print(f"  {sys.executable} -m pip install " + " ".join(missing))


if __name__ == "__main__":
    main()