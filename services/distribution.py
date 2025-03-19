import threading
import time
import queue
import multiprocessing
import os
import numpy as np
import socket
import json
from typing import Dict, List, Tuple, Set, Any, Optional, Callable, Union
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Future

from models.light_effect import LightEffect
from services.clustering import ClusteringService
from optimization.batching import BatchProcessor

logger = logging.getLogger(__name__)


class WorkItem:
    """
    Represents a unit of work for distributed processing.
    """
    
    def __init__(self, work_id: str, work_type: str, data: Any, priority: int = 0):
        """
        Initialize a work item.
        
        Args:
            work_id (str): Unique identifier for this work item
            work_type (str): Type of work (e.g., "update_effect", "render")
            data (Any): Work data
            priority (int): Priority (lower is higher priority)
        """
        self.work_id = work_id
        self.work_type = work_type
        self.data = data
        self.priority = priority
        self.created_time = time.time()
        self.start_time = None
        self.end_time = None
        self.worker_id = None
        
    def __lt__(self, other):
        """
        Compare work items for priority queue.
        """
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.created_time < other.created_time


class Worker:
    """
    Worker for processing distributed work items.
    """
    
    def __init__(self, worker_id: str, handler_map: Dict[str, Callable[[Any], Any]]):
        """
        Initialize a worker.
        
        Args:
            worker_id (str): Unique identifier for this worker
            handler_map (Dict[str, Callable]): Map of work types to handler functions
        """
        self.worker_id = worker_id
        self.handler_map = handler_map
        self.running = False
        self.thread = None
        self.work_queue = queue.PriorityQueue()
        self.result_queue = queue.Queue()
        self.current_work = None
        self.processed_count = 0
        self.error_count = 0
        
    def start(self):
        """
        Start the worker thread.
        """
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._worker_loop)
        self.thread.daemon = True
        self.thread.start()
        
    def stop(self):
        """
        Stop the worker thread.
        """
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
            
    def queue_work(self, work_item: WorkItem):
        """
        Queue a work item for processing.
        
        Args:
            work_item (WorkItem): The work item to process
        """
        self.work_queue.put(work_item)
        
    def get_result(self, timeout: float = 0.0) -> Optional[Tuple[WorkItem, Any]]:
        """
        Get a processed result.
        
        Args:
            timeout (float): Timeout in seconds (0 means non-blocking)
            
        Returns:
            Optional[Tuple[WorkItem, Any]]: Tuple of work item and result, or None if no result
        """
        try:
            return self.result_queue.get(block=timeout > 0, timeout=timeout)
        except queue.Empty:
            return None
            
    def get_status(self) -> Dict[str, Any]:
        """
        Get worker status.
        
        Returns:
            Dict[str, Any]: Worker status
        """
        return {
            "worker_id": self.worker_id,
            "running": self.running,
            "queue_size": self.work_queue.qsize(),
            "result_queue_size": self.result_queue.qsize(),
            "current_work": self.current_work.work_id if self.current_work else None,
            "processed_count": self.processed_count,
            "error_count": self.error_count
        }
        
    def _worker_loop(self):
        """
        Main worker loop.
        """
        while self.running:
            try:
                work_item = self.work_queue.get(block=True, timeout=0.1)
                
                self.current_work = work_item
                work_item.start_time = time.time()
                work_item.worker_id = self.worker_id
                
                try:
                    handler = self.handler_map.get(work_item.work_type)
                    
                    if handler:
                        result = handler(work_item.data)
                        
                        work_item.end_time = time.time()
                        self.result_queue.put((work_item, result))
                        self.processed_count += 1
                    else:
                        logger.error(f"No handler for work type: {work_item.work_type}")
                        self.error_count += 1
                        
                except Exception as e:
                    logger.error(f"Error processing work item {work_item.work_id}: {e}")
                    work_item.end_time = time.time()
                    self.result_queue.put((work_item, None))
                    self.error_count += 1
                    
                finally:
                    self.current_work = None
                    self.work_queue.task_done()
                    
            except queue.Empty:
                pass


class DistributionService:
    """
    Service for distributing work across multiple workers.
    """
    
    def __init__(self, num_workers: int = None, clustering_service: Optional[ClusteringService] = None):
        """
        Initialize the distribution service.
        
        Args:
            num_workers (int): Number of worker threads (None for CPU count)
            clustering_service (ClusteringService): Clustering service for work distribution
        """
        self.num_workers = num_workers or max(1, os.cpu_count() - 1)
        self.clustering_service = clustering_service
        self.workers: Dict[str, Worker] = {}
        self.work_items: Dict[str, WorkItem] = {}
        self.results: Dict[str, Any] = {}
        self.lock = threading.RLock()
        self.work_types: Dict[str, Dict[str, Any]] = {}
        self.executor = ThreadPoolExecutor(max_workers=self.num_workers)
        self.futures: Dict[str, Future] = {}
        self.batch_processor = BatchProcessor(batch_size=1000, max_workers=self.num_workers)
        
        self.default_handler_map = {
            "update_effect": self._handle_update_effect,
            "render": self._handle_render
        }
        
        self._init_workers()
        
    def _init_workers(self):
        """
        Initialize worker threads.
        """
        with self.lock:
            for i in range(self.num_workers):
                worker_id = f"worker-{i+1}"
                worker = Worker(worker_id, self.default_handler_map)
                self.workers[worker_id] = worker
                
            for worker in self.workers.values():
                worker.start()
                
            logger.info(f"Started {len(self.workers)} workers")
            
    def register_work_type(self, work_type: str, handler: Callable[[Any], Any], 
                          description: str = "", priority: int = 0):
        """
        Register a work type with a handler.
        
        Args:
            work_type (str): Type of work
            handler (Callable): Handler function
            description (str): Description of the work type
            priority (int): Default priority
        """
        with self.lock:
            self.work_types[work_type] = {
                "handler": handler,
                "description": description,
                "priority": priority
            }
            
            for worker in self.workers.values():
                worker.handler_map[work_type] = handler
                
            logger.debug(f"Registered work type: {work_type}")
            
    def distribute_work(self, work_type: str, data: Any, work_id: str = None, 
                       priority: int = None) -> str:
        """
        Distribute a work item to a worker.
        
        Args:
            work_type (str): Type of work
            data (Any): Work data
            work_id (str): Optional work ID (generated if None)
            priority (int): Priority (lower is higher priority)
            
        Returns:
            str: Work ID
        """
        with self.lock:
            if work_id is None:
                work_id = f"{work_type}-{time.time()}-{len(self.work_items)}"
                
            if priority is None and work_type in self.work_types:
                priority = self.work_types[work_type].get("priority", 0)
            elif priority is None:
                priority = 0
                
            work_item = WorkItem(work_id, work_type, data, priority)
            self.work_items[work_id] = work_item
            
            worker_id = f"worker-{hash(work_id) % self.num_workers + 1}"
            worker = self.workers.get(worker_id)
            
            if worker:
                worker.queue_work(work_item)
                logger.debug(f"Distributed work {work_id} to worker {worker_id}")
            else:
                logger.error(f"Worker not found: {worker_id}")
                
            return work_id
            
    def check_results(self, timeout: float = 0.1) -> List[Tuple[str, Any]]:
        """
        Check for completed results.
        
        Args:
            timeout (float): Timeout in seconds
            
        Returns:
            List[Tuple[str, Any]]: List of (work_id, result) tuples
        """
        results = []
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            found_result = False
            
            for worker in self.workers.values():
                result = worker.get_result()
                
                if result:
                    work_item, data = result
                    self.results[work_item.work_id] = data
                    results.append((work_item.work_id, data))
                    found_result = True
                    
            if not found_result:
                break
                
        return results
        
    def get_result(self, work_id: str, wait: bool = False, timeout: float = None) -> Optional[Any]:
        """
        Get a specific result.
        
        Args:
            work_id (str): Work ID
            wait (bool): Whether to wait for the result
            timeout (float): Timeout in seconds
            
        Returns:
            Optional[Any]: Result data or None if not available
        """
        if work_id in self.results:
            return self.results[work_id]
            
        if not wait:
            return None
            
        start_time = time.time()
        
        while timeout is None or time.time() - start_time < timeout:
            self.check_results(0.1)
            
            if work_id in self.results:
                return self.results[work_id]
                
        return None
        
    def shutdown(self):
        """
        Shut down the distribution service.
        """
        logger.info("Shutting down distribution service")
        
        for worker in self.workers.values():
            worker.stop()
            
        self.executor.shutdown(wait=False)
        
    def _handle_update_effect(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle updating an effect.
        
        Args:
            data (Dict[str, Any]): Effect data
            
        Returns:
            Dict[str, Any]: Result data
        """
        try:
            effect_id = data.get("effect_id")
            effect = data.get("effect")
            
            if not effect:
                return {"success": False, "error": "No effect provided"}
                
            effect.update_all()
            
            return {
                "success": True,
                "effect_id": effect_id,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error updating effect: {e}")
            return {"success": False, "error": str(e)}
            
    def _handle_render(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle rendering LED data.
        
        Args:
            data (Dict[str, Any]): Render data
            
        Returns:
            Dict[str, Any]: Result data
        """
        try:
            led_count = data.get("led_count", 0)
            effects = data.get("effects", {})
            
            if not effects:
                return {
                    "success": True,
                    "led_data": [[0, 0, 0]] * led_count,
                    "timestamp": time.time()
                }
                
            led_data = [[0, 0, 0] for _ in range(led_count)]
            
            for effect_id, effect in effects.items():
                effect_data = effect.get_led_output()
                
                for i in range(min(len(led_data), len(effect_data))):
                    led_data[i][0] = max(led_data[i][0], effect_data[i][0])
                    led_data[i][1] = max(led_data[i][1], effect_data[i][1])
                    led_data[i][2] = max(led_data[i][2], effect_data[i][2])
                    
            return {
                "success": True,
                "led_data": led_data,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error rendering: {e}")
            return {"success": False, "error": str(e)}
            
    def distribute_effect_updates(self, effects: Dict[int, LightEffect]) -> List[str]:
        """
        Distribute effect updates across workers.
        
        Args:
            effects (Dict[int, LightEffect]): Effects to update
            
        Returns:
            List[str]: List of work IDs
        """
        work_ids = []
        
        if self.clustering_service:
            clusters = self.clustering_service.get_all_cluster_info()
            
            for cluster_id, cluster_info in clusters.items():
                cluster_effects = {}
                
                for effect_id in cluster_info.get("effect_ids", []):
                    if effect_id in effects:
                        cluster_effects[effect_id] = effects[effect_id]
                        
                if cluster_effects:
                    work_id = self.distribute_work("update_cluster", {
                        "cluster_id": cluster_id,
                        "effects": cluster_effects
                    })
                    work_ids.append(work_id)
                    
        else:
            for effect_id, effect in effects.items():
                work_id = self.distribute_work("update_effect", {
                    "effect_id": effect_id,
                    "effect": effect
                })
                work_ids.append(work_id)
                
        return work_ids
        
    def render_leds(self, led_count: int, effects: Dict[int, LightEffect]) -> str:
        """
        Render LED data from multiple effects.
        
        Args:
            led_count (int): Number of LEDs
            effects (Dict[int, LightEffect]): Effects to render
            
        Returns:
            str: Work ID
        """
        work_id = self.distribute_work("render", {
            "led_count": led_count,
            "effects": effects
        })
        
        return work_id
        
    def get_worker_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all workers.
        
        Returns:
            Dict[str, Dict[str, Any]]: Worker statistics
        """
        return {worker_id: worker.get_status() for worker_id, worker in self.workers.items()}
        
    def get_work_status(self, work_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a work item.
        
        Args:
            work_id (str): Work ID
            
        Returns:
            Optional[Dict[str, Any]]: Work item status
        """
        with self.lock:
            if work_id not in self.work_items:
                return None
                
            work_item = self.work_items[work_id]
            
            return {
                "work_id": work_item.work_id,
                "work_type": work_item.work_type,
                "priority": work_item.priority,
                "created_time": work_item.created_time,
                "start_time": work_item.start_time,
                "end_time": work_item.end_time,
                "worker_id": work_item.worker_id,
                "completed": work_id in self.results,
                "duration": (work_item.end_time - work_item.start_time) if work_item.end_time else None
            }