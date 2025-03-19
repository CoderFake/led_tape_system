"""
Configuration module for LED Tape Light System.
Loads configuration from .env file and environment variables.
"""
import os
import sys
import logging
from typing import Dict, Any, Optional
import multiprocessing

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
    _env_loaded = True
except ImportError:
    _env_loaded = False
    print("WARNING: python-dotenv not installed. Will use system environment variables only.")
    print("To enable .env file support: pip install python-dotenv")

# Setup logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("config")

# Helper functions to get environment variables with defaults
def _get_env_str(name: str, default: str) -> str:
    """Get string from environment variable or default."""
    return os.environ.get(name, default)

def _get_env_int(name: str, default: int) -> int:
    """Get integer from environment variable or default."""
    try:
        return int(os.environ.get(name, default))
    except (ValueError, TypeError):
        logger.warning(f"Invalid value for {name}, using default: {default}")
        return default

def _get_env_float(name: str, default: float) -> float:
    """Get float from environment variable or default."""
    try:
        return float(os.environ.get(name, default))
    except (ValueError, TypeError):
        logger.warning(f"Invalid value for {name}, using default: {default}")
        return default

def _get_env_bool(name: str, default: bool) -> bool:
    """Get boolean from environment variable or default."""
    val = os.environ.get(name, str(default).lower())
    if isinstance(val, bool):
        return val
    return val.lower() in ('true', 't', 'yes', 'y', '1')

# System configuration
CPU_COUNT = multiprocessing.cpu_count()

# Display settings
WINDOW_WIDTH = _get_env_int("WINDOW_WIDTH", 1200)
WINDOW_HEIGHT = _get_env_int("WINDOW_HEIGHT", 600)
WINDOW_TITLE = _get_env_str("WINDOW_TITLE", "LED Tape Light System")
LED_SIZE = _get_env_int("LED_SIZE", 10)
LED_SPACING = _get_env_int("LED_SPACING", 2)

# LED settings
DEFAULT_LED_COUNT = _get_env_int("DEFAULT_LED_COUNT", 120)
MAX_FPS = _get_env_int("MAX_FPS", 60)
CLUSTER_GROUP_SIZE = _get_env_int("CLUSTER_GROUP_SIZE", 100)

# Performance settings
USE_MULTIPROCESSING = _get_env_bool("USE_MULTIPROCESSING", False)
USE_GPU = _get_env_bool("USE_GPU", False)
MAX_WORKERS = _get_env_int("MAX_WORKERS", max(1, CPU_COUNT - 1))
BATCH_SIZE = _get_env_int("BATCH_SIZE", 1000)
SKIP_GPU_CHECK = _get_env_bool("SKIP_GPU_CHECK", True)
SPATIAL_INDEX_TYPE = _get_env_str("SPATIAL_INDEX_TYPE", "grid")

# Memory management
MAX_SEGMENTS_TOTAL = _get_env_int("MAX_SEGMENTS_TOTAL", 100000)
MAX_SEGMENTS_PER_EFFECT = _get_env_int("MAX_SEGMENTS_PER_EFFECT", 1000)
MAX_EFFECTS = _get_env_int("MAX_EFFECTS", 100)
MAX_LEDS_PER_CLUSTER = _get_env_int("MAX_LEDS_PER_CLUSTER", 1000)
OBJECT_POOL_SIZE = _get_env_int("OBJECT_POOL_SIZE", 10000)

# OSC settings
OSC_SERVER_IP = _get_env_str("OSC_SERVER_IP", "0.0.0.0")
OSC_SERVER_PORT = _get_env_int("OSC_SERVER_PORT", 8000)

# Logging settings
LOG_LEVEL = _get_env_str("LOG_LEVEL", "INFO")

# File paths
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".led_tape_system")
LOG_DIR = os.path.join(CONFIG_DIR, "logs")

# Create directories if they don't exist
for directory in [CONFIG_DIR, LOG_DIR]:
    os.makedirs(directory, exist_ok=True)

# Default color palette
DEFAULT_COLOR_PALETTE = {
    "red": 0xFF0000,
    "green": 0x00FF00,
    "blue": 0x0000FF,
    "white": 0xFFFFFF,
    "black": 0x000000,
    "yellow": 0xFFFF00,
    "cyan": 0x00FFFF,
    "magenta": 0xFF00FF,
}

# Show loaded configuration
def print_config():
    """Print the current configuration."""
    print("\n=== LED Tape Light System Configuration ===")
    
    sections = {
        "Display Settings": ["WINDOW_WIDTH", "WINDOW_HEIGHT", "WINDOW_TITLE", "LED_SIZE", "LED_SPACING"],
        "LED Settings": ["DEFAULT_LED_COUNT", "MAX_FPS", "CLUSTER_GROUP_SIZE"],
        "Performance Settings": ["USE_MULTIPROCESSING", "USE_GPU", "MAX_WORKERS", "BATCH_SIZE", "SKIP_GPU_CHECK"],
        "Memory Management": ["MAX_SEGMENTS_TOTAL", "MAX_SEGMENTS_PER_EFFECT", "MAX_EFFECTS", "MAX_LEDS_PER_CLUSTER"],
        "OSC Settings": ["OSC_SERVER_IP", "OSC_SERVER_PORT"],
        "System Information": ["CPU_COUNT"]
    }
    
    for section, keys in sections.items():
        print(f"\n{section}:")
        for key in keys:
            if key in globals():
                print(f"  {key}: {globals()[key]}")
    
    print(f"\nEnvironment configured from: {'Environment variables' if not _env_loaded else '.env file + Environment variables'}")
    print("========================================\n")

# Get all configuration as a dictionary
def get_all_config() -> Dict[str, Any]:
    """
    Get all configuration values.
    
    Returns:
        Dict[str, Any]: All configuration values
    """
    return {key: value for key, value in globals().items() 
            if key.isupper() and not key.startswith('_')}

# Apply configuration from dictionary
def apply_config(config_dict: Dict[str, Any]):
    """
    Apply configuration from dictionary.
    
    Args:
        config_dict (Dict[str, Any]): Configuration dictionary
    """
    for key, value in config_dict.items():
        if key.isupper() and key in globals():
            globals()[key] = value
            # Also set as environment variable for child processes
            os.environ[key] = str(value)