"""
Effect Manager for large-scale LED Tape Light System.
Handles thousands or millions of light effects efficiently.
"""
import time
from typing import Dict, List, Set, Optional, Tuple, Any  # Thêm Any vào imports
import numpy as np
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import logging

from models.light_effect import LightEffect
from utils.performance import PerformanceMonitor
from utils.memory_pool import ObjectPool

# Set up logging
logger = logging.getLogger(__name__)


class EffectManager:
    """
    Manages large numbers of light effects efficiently.
    Uses multi-threading, pooling, and batching for performance.
    """
    
    def __init__(self, 
                 max_workers: int = None,
                 use_multiprocessing: bool = False,
                 batch_size: int = 100):
        """
        Initialize the effect manager.
        
        Args:
            max_workers (int, optional): Maximum number of worker threads/processes
            use_multiprocessing (bool): Whether to use multiprocessing
            batch_size (int): Number of effects to process in a batch
        """
        self.effects: Dict[int, LightEffect] = {}
        self.effect_groups: Dict[str, Set[int]] = {}  # Group effects for batch processing
        self.active_effect_ids: Set[int] = set()  # Track active effects
        self.batch_size = batch_size
        self.use_multiprocessing = use_multiprocessing
        
        # Determine number of workers (default to CPU count)
        self.max_workers = max_workers if max_workers else multiprocessing.cpu_count()
        
        # Create executor for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
            
        # Create performance monitor
        self.perf_monitor = PerformanceMonitor()
        
        # Create object pool for reusing effect objects
        self.effect_pool = ObjectPool(
            create_func=lambda: None,  # Will be replaced with actual creation function
            max_size=10000  # Maximum pool size
        )
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        # Scheduled updates
        self.update_interval = 1.0 / 60.0  # Default to 60 FPS
        self.last_update_time = time.time()
        self.update_thread = None
        self.running = False
        
        logger.info(f"EffectManager initialized with {self.max_workers} workers, "
                   f"multiprocessing={use_multiprocessing}, batch_size={batch_size}")
        
    def add_effect(self, effect_id: int, effect: LightEffect, group: str = "default") -> bool:
        """
        Add a light effect to the manager.
        
        Args:
            effect_id (int): Unique identifier for the effect
            effect (LightEffect): The effect to add
            group (str): Group name for batch processing
            
        Returns:
            bool: True if added successfully, False if already exists
        """
        with self.lock:
            if effect_id in self.effects:
                logger.warning(f"Effect {effect_id} already exists")
                return False
                
            self.effects[effect_id] = effect
            self.active_effect_ids.add(effect_id)
            
            # Add to group
            if group not in self.effect_groups:
                self.effect_groups[group] = set()
            self.effect_groups[group].add(effect_id)
            
            logger.debug(f"Added effect {effect_id} to group '{group}'")
            return True
            
    def remove_effect(self, effect_id: int) -> bool:
        """
        Remove a light effect from the manager.
        
        Args:
            effect_id (int): ID of the effect to remove
            
        Returns:
            bool: True if removed, False if not found
        """
        with self.lock:
            if effect_id not in self.effects:
                logger.warning(f"Effect {effect_id} not found")
                return False
                
            # Remove from all groups
            for group in self.effect_groups.values():
                group.discard(effect_id)
                
            # Get the effect and return to pool if possible
            effect = self.effects.pop(effect_id)
            self.active_effect_ids.discard(effect_id)
            
            # Try to return to object pool
            try:
                self.effect_pool.return_object(effect)
                logger.debug(f"Returned effect {effect_id} to pool")
            except Exception as e:
                logger.warning(f"Failed to return effect to pool: {e}")
                
            logger.debug(f"Removed effect {effect_id}")
            return True
            
    def get_effect(self, effect_id: int) -> Optional[LightEffect]:
        """
        Get a light effect by ID.
        
        Args:
            effect_id (int): ID of the effect to get
            
        Returns:
            LightEffect: The effect if found, None otherwise
        """
        return self.effects.get(effect_id)
        
    def update_all(self) -> Dict[str, float]:
        """
        Update all active light effects.
        Uses parallel processing for efficiency.
        
        Returns:
            Dict[str, float]: Performance metrics
        """
        self.perf_monitor.start_measurement("update_all")
        
        with self.lock:
            active_effects = {
                effect_id: effect 
                for effect_id, effect in self.effects.items()
                if effect_id in self.active_effect_ids
            }
            
        if not active_effects:
            self.perf_monitor.end_measurement("update_all")
            return self.perf_monitor.get_metrics()
            
        # Update effects in batches
        self.perf_monitor.start_measurement("batch_updates")
        
        # Group effects into batches
        batches = []
        current_batch = []
        
        for effect in active_effects.values():
            current_batch.append(effect)
            
            if len(current_batch) >= self.batch_size:
                batches.append(current_batch)
                current_batch = []
                
        if current_batch:
            batches.append(current_batch)
            
        # Submit batches to executor
        futures = []
        for batch in batches:
            futures.append(self.executor.submit(self._process_batch, batch))
            
        # Wait for all batches to complete
        for future in futures:
            future.result()
            
        self.perf_monitor.end_measurement("batch_updates")
        self.perf_monitor.end_measurement("update_all")
        
        return self.perf_monitor.get_metrics()
        
    def _process_batch(self, batch: List[LightEffect]):
        """
        Process a batch of effects in parallel.
        
        Args:
            batch (List[LightEffect]): Batch of effects to process
        """
        for effect in batch:
            effect.update_all()
            
    def start_scheduled_updates(self, fps: int = 60):
        """
        Start scheduled updates in a background thread.
        
        Args:
            fps (int): Frames per second for updates
        """
        if self.running:
            logger.warning("Scheduled updates already running")
            return
            
        self.update_interval = 1.0 / fps
        self.running = True
        
        def update_loop():
            while self.running:
                current_time = time.time()
                elapsed = current_time - self.last_update_time
                
                if elapsed >= self.update_interval:
                    metrics = self.update_all()
                    self.last_update_time = current_time
                    
                    # Log performance metrics periodically
                    if current_time % 10 < self.update_interval:  # Log every ~10 seconds
                        logger.info(f"Performance metrics: {metrics}")
                else:
                    # Sleep for the remaining time
                    sleep_time = max(0.001, self.update_interval - elapsed)
                    time.sleep(sleep_time)
        
        # Start update thread
        self.update_thread = threading.Thread(target=update_loop, daemon=True)
        self.update_thread.start()
        logger.info(f"Started scheduled updates at {fps} FPS")
        
    def stop_scheduled_updates(self):
        """
        Stop scheduled updates.
        """
        if not self.running:
            logger.warning("Scheduled updates not running")
            return
            
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=1.0)
            logger.info("Stopped scheduled updates")
            
    def get_status(self) -> Dict[str, Any]:
        """
        Get status information about the effect manager.
        
        Returns:
            Dict[str, Any]: Status information
        """
        with self.lock:
            return {
                "total_effects": len(self.effects),
                "active_effects": len(self.active_effect_ids),
                "groups": {group: len(ids) for group, ids in self.effect_groups.items()},
                "pool_size": self.effect_pool.used_size,
                "performance": self.perf_monitor.get_metrics(),
                "workers": self.max_workers,
                "multiprocessing": self.use_multiprocessing,
                "batch_size": self.batch_size,
                "update_interval": self.update_interval,
            }