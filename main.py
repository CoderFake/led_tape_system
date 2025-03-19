import argparse
import time
import random
import logging
import sys
import os
import multiprocessing
from typing import Dict, Any, Optional
import config

def setup_logging():
    """
    Set up logging based on configuration.
    """
    numeric_level = getattr(logging, config.LOG_LEVEL.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
        
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=numeric_level, format=log_format)
    
    try:
        log_file = os.path.join(config.LOG_DIR, f"led_system_{time.strftime('%Y%m%d_%H%M%S')}.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))
        
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"WARNING: Could not set up file logging: {e}")
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting LED Tape Light System")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"System: {os.name}")
    logger.info(f"CPU count: {multiprocessing.cpu_count()}")
    logger.info(f"Log level: {config.LOG_LEVEL}")

try:
    from system_checker import ensure_dependencies
    
    deps_ok, missing_deps = ensure_dependencies(auto_install=True)
    
    if not deps_ok:
        print("ERROR: Some dependencies are missing and could not be installed automatically.")
        print("Please install the following packages manually:")
        for pkg in missing_deps:
            print(f"  - {pkg}")
        print("\nYou can install them using:")
        print(f"  {sys.executable} -m pip install " + " ".join(missing_deps))
        sys.exit(1)
        
except ImportError:
    print("WARNING: system_checker.py not found, skipping dependency check.")
    print("If you encounter import errors, please install the required dependencies manually.")
    

from models.light_segment import LightSegment
from models.light_effect import LightEffect
from models.effect_factory import EffectFactory
from controllers.osc_handler import OSCHandlerFactory
from controllers.effect_manager import EffectManager
from controllers.segment_manager import SegmentManager
from views.simulator import LEDSimulator
from views.preview import LargeScalePreview, PreviewSettings
from services.clustering import ClusteringService
from services.scheduler import Scheduler, Priority
from services.distribution import DistributionService
from utils.performance import PerformanceMonitor, MemoryMonitor
from utils.memory_pool import ObjectPool
from optimization.gpu_acceleration import get_accelerator
from optimization.batching import BatchProcessor
from optimization.spatial_indexing import create_spatial_index


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='LED Tape Light System')
    parser.add_argument('--no-gui', action='store_true', help='Run without GUI')
    parser.add_argument('--preview', action='store_true', help='Run with large-scale preview')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--osc-ip', type=str, default=config.OSC_SERVER_IP, help='OSC server IP')
    parser.add_argument('--osc-port', type=int, default=config.OSC_SERVER_PORT, help='OSC server port')
    parser.add_argument('--led-count', type=int, default=config.DEFAULT_LED_COUNT, help='Number of LEDs')
    parser.add_argument('--fps', type=int, default=config.MAX_FPS, help='Frames per second')
    parser.add_argument('--workers', type=int, default=config.MAX_WORKERS, help='Number of workers')
    parser.add_argument('--skip-gpu-check', action='store_true', help='Skip GPU acceleration check')
    parser.add_argument('--show-config', action='store_true', help='Show configuration and exit')
    return parser.parse_args()


def check_gpu_support():
    """
    Check GPU support and log information.
    """
    logger = logging.getLogger(__name__)
    
    if config.SKIP_GPU_CHECK:
        logger.info("GPU check skipped due to configuration")
        return
    
    try:
        import pygame
        logger.info(f"Pygame version: {pygame.version.ver}")
        
        sdl_version = ".".join(map(str, pygame.version.SDL))
        logger.info(f"SDL version: {sdl_version}")
        
    except ImportError:
        logger.warning("Pygame not found, visualization will not be available")
    
    try:
        import numpy as np
        logger.info(f"NumPy version: {np.__version__}")
    except ImportError:
        logger.warning("NumPy not found, performance will be degraded")
    
    if config.USE_GPU:
        cuda_available = False
        try:
            import numba
            from numba import cuda
            
            if cuda.is_available():
                device = cuda.get_current_device()
                logger.info(f"CUDA device: {device.name} (Compute {device.compute_capability[0]}.{device.compute_capability[1]})")
                cuda_available = True
            else:
                logger.info("CUDA is installed but no CUDA device is available")
                
        except ImportError:
            logger.info("Numba/CUDA not available, CUDA acceleration disabled")
        except Exception as e:
            logger.warning(f"Error checking CUDA support: {e}")
        
        opencl_available = False
        try:
            import pyopencl as cl
            
            try:
                platforms = cl.get_platforms()
                if platforms:
                    logger.info(f"OpenCL platforms found: {len(platforms)}")
                    opencl_available = True
                    
                    for i, platform in enumerate(platforms):
                        logger.info(f"  Platform {i+1}: {platform.name} ({platform.version})")
                        
                        try:
                            devices = platform.get_devices()
                            logger.info(f"    Devices: {len(devices)}")
                            
                            for j, device in enumerate(devices):
                                logger.info(f"      Device {j+1}: {device.name} ({device.type})")
                                
                        except Exception as dev_e:
                            logger.info(f"    Could not enumerate devices: {dev_e}")
                else:
                    logger.info("OpenCL is installed but no OpenCL platforms found")
            except Exception as e:
                logger.info(f"OpenCL error: {e}")
                logger.info("No OpenCL platforms available on this system")
                
        except ImportError:
            logger.info("PyOpenCL not available, OpenCL acceleration disabled")
        except Exception as e:
            logger.warning(f"Error checking OpenCL support: {e}")
            
        if not cuda_available and not opencl_available:
            logger.warning("No GPU acceleration available, falling back to CPU")
            config.USE_GPU = False
    else:
        logger.info("GPU acceleration disabled in configuration")


def create_demo_effects(effect_factory: EffectFactory, 
                      led_count: int, fps: int = 60) -> Dict[int, LightEffect]:
    """
    Create demo light effects.
    
    Args:
        effect_factory (EffectFactory): Effect factory
        led_count (int): Number of LEDs
        fps (int): Frames per second
        
    Returns:
        Dict[int, LightEffect]: Dictionary of effects by ID
    """
    effects = {}
    
    rainbow_effect = effect_factory.create_effect(
        template_id="rainbow",
        effect_id=1,
        led_count=led_count,
        fps=fps,
        parameters={
            "speed": 15.0,
            "brightness": 1.0
        }
    )
    if rainbow_effect:
        effects[1] = rainbow_effect

    pulse_effect = effect_factory.create_effect(
        template_id="pulse",
        effect_id=2,
        led_count=led_count,
        fps=fps,
        parameters={
            "color": 0x00FFFF, 
            "pulse_speed": 0.5
        }
    )
    if pulse_effect:
        effects[2] = pulse_effect
    
    chase_effect = effect_factory.create_effect(
        template_id="chase",
        effect_id=3,
        led_count=led_count,
        fps=fps,
        parameters={
            "segment_count": 5,
            "segment_length": 3,
            "gap_length": 10,
            "speed": 30.0,
            "color": 0xFF0088 
        }
    )
    if chase_effect:
        effects[3] = chase_effect
    
    return effects


def main():
    args = parse_args()
    
    if args.show_config:
        config.print_config()
        return
    
    if args.osc_ip:
        config.OSC_SERVER_IP = args.osc_ip
    if args.osc_port:
        config.OSC_SERVER_PORT = args.osc_port
    if args.led_count:
        config.DEFAULT_LED_COUNT = args.led_count
    if args.fps:
        config.MAX_FPS = args.fps
    if args.workers:
        config.MAX_WORKERS = args.workers
    if args.skip_gpu_check:
        config.SKIP_GPU_CHECK = True
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    if not config.SKIP_GPU_CHECK:
        check_gpu_support()
    
    logger.info("Initializing system components")
    
    if config.USE_GPU:
        gpu_accelerator = get_accelerator()
        logger.info(f"GPU acceleration: {gpu_accelerator.get_device_info()}")
    
    segment_manager = SegmentManager(max_segments=config.MAX_SEGMENTS_TOTAL)
    effect_factory = EffectFactory()
    effect_manager = EffectManager(max_workers=config.MAX_WORKERS, 
                                 use_multiprocessing=config.USE_MULTIPROCESSING,
                                 batch_size=config.BATCH_SIZE)
    
    perf_monitor = PerformanceMonitor()
    memory_monitor = MemoryMonitor()
    memory_monitor.start()
    
    spatial_index = create_spatial_index(config.SPATIAL_INDEX_TYPE)
    
    clustering_service = ClusteringService(max_leds_per_cluster=config.MAX_LEDS_PER_CLUSTER)
    
    scheduler = Scheduler(max_workers=config.MAX_WORKERS)
    scheduler.start()
    
    distribution_service = DistributionService(num_workers=config.MAX_WORKERS, 
                                           clustering_service=clustering_service)
    
    effects = create_demo_effects(effect_factory, config.DEFAULT_LED_COUNT, config.MAX_FPS)
    
    for effect_id, effect in effects.items():
        effect_manager.add_effect(effect_id, effect)
        logger.info(f"Added effect {effect_id}: {effect.__class__.__name__}")
    
    clustering_service.cluster_by_linear_groups(config.DEFAULT_LED_COUNT, config.CLUSTER_GROUP_SIZE)
    logger.info(f"Clustered {config.DEFAULT_LED_COUNT} LEDs into {len(clustering_service.clusters)} clusters")
    
    osc_handler = OSCHandlerFactory.create(effect_manager.effects, config.OSC_SERVER_IP, config.OSC_SERVER_PORT)
    osc_handler.start()
    logger.info(f"Started OSC server on {config.OSC_SERVER_IP}:{config.OSC_SERVER_PORT}")
    
    effect_manager.start_scheduled_updates(config.MAX_FPS)
    logger.info(f"Started scheduled updates at {config.MAX_FPS} FPS")
    
    try:
        if args.headless:
            logger.info("Running in headless mode")
            
            while True:
                time.sleep(1.0)
                
                if int(time.time()) % 60 == 0:  
                    status = effect_manager.get_status()
                    mem_usage = memory_monitor.get_usage()
                    logger.info(f"Status: {status}")
                    logger.info(f"Memory usage: {mem_usage['current']:.2f} MB")
                    
        elif args.preview:
            logger.info("Running with large-scale preview")
            
            preview_settings = PreviewSettings()
            preview_settings.width = config.WINDOW_WIDTH
            preview_settings.height = config.WINDOW_HEIGHT
            preview_settings.led_size = config.LED_SIZE

            preview = LargeScalePreview(effect_manager, clustering_service)
            preview.update_settings({
                "layout_type": "linear",
                "layout_params": {
                    "led_count": config.DEFAULT_LED_COUNT,
                    "rows": 1,
                    "spacing": 10,
                    "start_x": 50,
                    "start_y": config.WINDOW_HEIGHT // 2
                }
            })
            
            preview.run()
            
        elif not args.no_gui:
            logger.info("Running with simulator")
            
            simulator = LEDSimulator(effect_manager.effects, config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
            simulator.run()
            
        else:
            logger.info("Running without GUI")
            
            while True:
                time.sleep(1.0)
                
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        
    except Exception as e:
        logger.error(f"Error in main loop: {e}", exc_info=True)
        
    finally:
        logger.info("Shutting down...")
        
        effect_manager.stop_scheduled_updates()
        scheduler.stop()
        memory_monitor.stop()
        
        osc_handler.stop()
        
        distribution_service.shutdown()
        
        logger.info("Shutdown complete")


if __name__ == "__main__":
    if sys.platform == 'win32':
        multiprocessing.freeze_support()
        
    main()