import threading
from typing import Callable, List, Any, Optional, Dict
import logging
import time
import weakref

logger = logging.getLogger(__name__)


class ObjectPool:
    """
    Generic object pool to reuse objects and reduce memory allocations.
    """
    
    def __init__(self, create_func: Callable[[], Any], max_size: int = 1000):
        """
        Initialize the object pool.
        
        Args:
            create_func (Callable): Function to create new objects
            max_size (int): Maximum pool size
        """
        self.create_func = create_func
        self.max_size = max_size
        self.pool: List[Any] = []
        self.lock = threading.RLock()
        self.created_count = 0
        self.reused_count = 0
        self.returned_count = 0
        self.last_cleaned = time.time()
        self.used_objects: Dict[int, weakref.ref] = {}
        self.used_size = 0
        
    def get_object(self) -> Any:
        """
        Get an object from the pool or create a new one.
        
        Returns:
            Any: An object from the pool or a new one
        """
        with self.lock:
            if self.pool:
                obj = self.pool.pop()
                self.reused_count += 1
                logger.debug(f"Reused object from pool, {len(self.pool)} remaining")
            else:
                obj = self.create_func()
                self.created_count += 1
                logger.debug(f"Created new object, total created: {self.created_count}")

            self.used_objects[id(obj)] = weakref.ref(obj)
            self.used_size = len(self.used_objects)
            
            return obj
            
    def return_object(self, obj: Any):
        """
        Return an object to the pool.
        
        Args:
            obj: The object to return
        """
        with self.lock:

            if len(self.pool) >= self.max_size:
                logger.debug(f"Pool is full, discarding object")
                return
                
            self.pool.append(obj)
            self.returned_count += 1

            obj_id = id(obj)
            if obj_id in self.used_objects:
                del self.used_objects[obj_id]
                
            self.used_size = len(self.used_objects)
            logger.debug(f"Returned object to pool, total in pool: {len(self.pool)}")
            
    def cleanup(self, force: bool = False):
        """
        Clean up expired weak references.
        
        Args:
            force (bool): Force cleanup regardless of time since last cleanup
        """
        current_time = time.time()

        if not force and current_time - self.last_cleaned < 60:
            return
            
        with self.lock:
            expired = []
            for obj_id, ref in self.used_objects.items():
                if ref() is None:
                    expired.append(obj_id)
                    
            for obj_id in expired:
                del self.used_objects[obj_id]
                
            self.used_size = len(self.used_objects)
            self.last_cleaned = current_time
            
            if expired:
                logger.debug(f"Cleaned up {len(expired)} expired references")
                
    def clear(self):
        """
        Clear the pool.
        """
        with self.lock:
            self.pool.clear()
            logger.debug("Cleared object pool")
            
    def get_stats(self) -> Dict[str, int]:
        """
        Get pool statistics.
        
        Returns:
            Dict[str, int]: Pool statistics
        """
        with self.lock:
            return {
                "pool_size": len(self.pool),
                "max_size": self.max_size,
                "created_count": self.created_count,
                "reused_count": self.reused_count,
                "returned_count": self.returned_count,
                "used_size": self.used_size
            }


class SegmentPoolManager:
    """
    Manages pools of LightSegment objects with different configurations.
    """
    
    def __init__(self):
        """
        Initialize the segment pool manager.
        """
        self.pools: Dict[str, ObjectPool] = {}
        self.lock = threading.RLock()
        
    def get_segment(self, config_key: str, create_func: Callable[[], Any]) -> Any:
        """
        Get a segment from the appropriate pool.
        
        Args:
            config_key (str): Configuration key for the pool
            create_func (Callable): Function to create new segments
            
        Returns:
            Any: A segment from the pool or a new one
        """
        with self.lock:
            if config_key not in self.pools:
                self.pools[config_key] = ObjectPool(create_func, max_size=1000)

            return self.pools[config_key].get_object()
            
    def return_segment(self, config_key: str, segment: Any):
        """
        Return a segment to the appropriate pool.
        
        Args:
            config_key (str): Configuration key for the pool
            segment: The segment to return
        """
        with self.lock:
            if config_key in self.pools:
                self.pools[config_key].return_object(segment)
                
    def cleanup_all(self, force: bool = False):
        """
        Clean up all pools.
        
        Args:
            force (bool): Force cleanup regardless of time since last cleanup
        """
        with self.lock:
            for pool in self.pools.values():
                pool.cleanup(force)
                
    def get_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Get statistics for all pools.
        
        Returns:
            Dict[str, Dict[str, int]]: Statistics for all pools
        """
        with self.lock:
            return {key: pool.get_stats() for key, pool in self.pools.items()}