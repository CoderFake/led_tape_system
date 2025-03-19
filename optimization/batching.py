import numpy as np
from typing import List, Dict, Tuple, Any, Callable, Optional
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Processes LED calculations in batches for improved performance.
    """
    
    def __init__(self, batch_size: int = 1000, max_workers: int = None):
        """
        Initialize the batch processor.
        
        Args:
            batch_size (int): Maximum number of LEDs per batch
            max_workers (int): Maximum number of worker threads
        """
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.lock = threading.RLock()
        
        self.processed_batches = 0
        self.processed_leds = 0
        self.total_processing_time = 0.0
        self.start_time = time.time()
        
    def process_led_segments(self, segments: List[Dict[str, Any]], 
                            process_func: Callable[[Dict[str, Any]], Any]) -> List[Any]:
        """
        Process LED segments in batches.
        
        Args:
            segments (List[Dict[str, Any]]): List of segment data
            process_func (Callable): Function to process each segment
            
        Returns:
            List[Any]: List of results
        """
        if not segments:
            return []
            
        start_time = time.time()
        
        batches = []
        current_batch = []
        current_size = 0
        
        for segment in segments:
            segment_size = segment.get("size", 1)

            if current_size + segment_size > self.batch_size and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_size = 0
                
            current_batch.append(segment)
            current_size += segment_size
            
        if current_batch:
            batches.append(current_batch)
            
        futures = []
        for batch in batches:
            futures.append(self.executor.submit(self._process_batch, batch, process_func))

        results = []
        for future in futures:
            batch_results = future.result()
            results.extend(batch_results)

        processing_time = time.time() - start_time
        self.processed_batches += len(batches)
        self.processed_leds += sum(len(batch) for batch in batches)
        self.total_processing_time += processing_time
        
        return results
        
    def _process_batch(self, batch: List[Dict[str, Any]], 
                     process_func: Callable[[Dict[str, Any]], Any]) -> List[Any]:
        """
        Process a batch of segments.
        
        Args:
            batch (List[Dict[str, Any]]): Batch of segments
            process_func (Callable): Function to process each segment
            
        Returns:
            List[Any]: List of results
        """
        results = []
        for segment in batch:
            try:
                result = process_func(segment)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing segment: {e}")
                results.append(None)
                
        return results
        
    def process_led_buffer(self, led_buffer: np.ndarray, led_count: int,
                         process_func: Callable[[np.ndarray, int, int], None]) -> bool:
        """
        Process a large LED buffer in batches.
        
        Args:
            led_buffer (np.ndarray): LED buffer array
            led_count (int): Total number of LEDs
            process_func (Callable): Function to process each batch (takes buffer, start, count)
            
        Returns:
            bool: True if successful
        """
        if led_count <= 0:
            return True
            
        start_time = time.time()

        num_batches = (led_count + self.batch_size - 1) // self.batch_size

        futures = []
        for i in range(num_batches):
            start_index = i * self.batch_size
            count = min(self.batch_size, led_count - start_index)
            
            futures.append(self.executor.submit(process_func, led_buffer, start_index, count))

        for future in futures:
            future.result()
            
        processing_time = time.time() - start_time
        self.processed_batches += num_batches
        self.processed_leds += led_count
        self.total_processing_time += processing_time
        
        return True
        
    def reset_statistics(self):
        """
        Reset performance statistics.
        """
        with self.lock:
            self.processed_batches = 0
            self.processed_leds = 0
            self.total_processing_time = 0.0
            self.start_time = time.time()
            
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get performance statistics.
        
        Returns:
            Dict[str, Any]: Performance statistics
        """
        with self.lock:
            elapsed = time.time() - self.start_time
            
            return {
                "batch_size": self.batch_size,
                "max_workers": self.max_workers,
                "processed_batches": self.processed_batches,
                "processed_leds": self.processed_leds,
                "total_processing_time": self.total_processing_time,
                "elapsed_time": elapsed,
                "leds_per_second": self.processed_leds / max(0.001, self.total_processing_time),
                "batches_per_second": self.processed_batches / max(0.001, self.total_processing_time),
                "average_batch_time": self.total_processing_time / max(1, self.processed_batches)
            }