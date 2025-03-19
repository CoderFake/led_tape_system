import time
from typing import Dict, List, Any
import threading
import statistics
import logging


logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """
    Tracks and reports performance metrics.
    """
    
    def __init__(self, window_size: int = 100):
        """
        Initialize the performance monitor.
        
        Args:
            window_size (int): Number of measurements to keep for each metric
        """
        self.window_size = window_size
        self.metrics: Dict[str, List[float]] = {}
        self.start_times: Dict[str, float] = {}
        self.lock = threading.RLock()
        
    def start_measurement(self, name: str):
        """
        Start measuring a named operation.
        
        Args:
            name (str): Name of the operation
        """
        with self.lock:
            self.start_times[name] = time.time()
        
    def end_measurement(self, name: str):
        """
        End measuring a named operation and record the duration.
        
        Args:
            name (str): Name of the operation
        """
        with self.lock:
            if name not in self.start_times:
                logger.warning(f"No start time recorded for '{name}'")
                return
                
            duration = time.time() - self.start_times[name]
            
            if name not in self.metrics:
                self.metrics[name] = []
                
            self.metrics[name].append(duration)
            
            if len(self.metrics[name]) > self.window_size:
                self.metrics[name].pop(0)

            del self.start_times[name]
    
    def record_value(self, name: str, value: float):
        """
        Record a custom value metric.
        
        Args:
            name (str): Name of the metric
            value (float): Value to record
        """
        with self.lock:
            if name not in self.metrics:
                self.metrics[name] = []
                
            self.metrics[name].append(value)

            if len(self.metrics[name]) > self.window_size:
                self.metrics[name].pop(0)
    
    def get_metrics(self) -> Dict[str, Dict[str, float]]:
        """
        Get statistical metrics for all measurements.
        
        Returns:
            Dict[str, Dict[str, float]]: Metrics with statistics
        """
        result = {}
        
        with self.lock:
            for name, values in self.metrics.items():
                if not values:
                    continue
                    
                try:
                    result[name] = {
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "median": statistics.median(values),
                        "p95": self._percentile(values, 95),
                        "p99": self._percentile(values, 99),
                        "count": len(values),
                        "last": values[-1]
                    }
                except Exception as e:
                    logger.error(f"Error calculating metrics for '{name}': {e}")
                    result[name] = {"error": str(e)}
        
        return result
    
    def reset(self):
        """
        Reset all metrics.
        """
        with self.lock:
            self.metrics.clear()
            self.start_times.clear()
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """
        Calculate percentile value.
        
        Args:
            values (List[float]): List of values
            percentile (float): Percentile to calculate (0-100)
            
        Returns:
            float: Percentile value
        """
        values_sorted = sorted(values)
        k = (len(values_sorted) - 1) * percentile / 100.0
        f = int(k)
        c = k - f
        
        if f + 1 < len(values_sorted):
            return values_sorted[f] * (1 - c) + values_sorted[f + 1] * c
        else:
            return values_sorted[f]


class MemoryMonitor:
    """
    Monitors memory usage of the application.
    """
    
    def __init__(self, interval: float = 10.0):
        """
        Initialize the memory monitor.
        
        Args:
            interval (float): Monitoring interval in seconds
        """
        self.interval = interval
        self.running = False
        self.monitor_thread = None
        self.memory_usage = []
        self.max_samples = 100
    
    def start(self):
        """
        Start memory monitoring in a background thread.
        """
        if self.running:
            return
            
        self.running = True
        
        def monitor_loop():
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            
            while self.running:
                try:
                    memory_info = process.memory_info()

                    memory_mb = memory_info.rss / (1024 * 1024)
                    self.memory_usage.append(memory_mb)

                    if len(self.memory_usage) > self.max_samples:
                        self.memory_usage.pop(0)
                        
                    logger.debug(f"Current memory usage: {memory_mb:.2f} MB")
                    
                except Exception as e:
                    logger.error(f"Error monitoring memory: {e}")
                    
                time.sleep(self.interval)

        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"Started memory monitoring at {self.interval}s intervals")
    
    def stop(self):
        """
        Stop memory monitoring.
        """
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
            logger.info("Stopped memory monitoring")
    
    def get_usage(self) -> Dict[str, float]:
        """
        Get memory usage statistics.
        
        Returns:
            Dict[str, float]: Memory usage statistics in MB
        """
        if not self.memory_usage:
            return {"current": 0, "avg": 0, "max": 0, "min": 0}
            
        return {
            "current": self.memory_usage[-1],
            "avg": sum(self.memory_usage) / len(self.memory_usage),
            "max": max(self.memory_usage),
            "min": min(self.memory_usage)
        }