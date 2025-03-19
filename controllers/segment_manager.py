import threading
import time
import numpy as np
from typing import Dict, List, Tuple, Set, Any, Optional, Callable
import logging
from collections import defaultdict

from models.light_segment import LightSegment
from utils.memory_pool import SegmentPoolManager

logger = logging.getLogger(__name__)


class SegmentManager:
    """
    Manages light segments with optimized memory usage.
    """
    
    def __init__(self, max_segments: int = 10000):
        """
        Initialize the segment manager.
        
        Args:
            max_segments (int): Maximum number of segments to manage
        """
        self.segments: Dict[Tuple[int, int], LightSegment] = {}  
        self.segment_configs: Dict[Tuple[int, int], Dict[str, Any]] = {}  
        self.active_segments: Set[Tuple[int, int]] = set()
        self.max_segments = max_segments
        self.pool_manager = SegmentPoolManager()
        self.lock = threading.RLock()
 
        self.creation_count = 0
        self.reuse_count = 0
        self.update_count = 0
        self.last_cleanup = time.time()
        
    def create_segment(self, effect_id: int, segment_id: int, config: Dict[str, Any]) -> LightSegment:
        """
        Create or reuse a light segment.
        
        Args:
            effect_id (int): Effect ID
            segment_id (int): Segment ID
            config (Dict[str, Any]): Segment configuration
            
        Returns:
            LightSegment: Created or reused segment
        """
        with self.lock:
            key = (effect_id, segment_id)
            
            if key in self.segments:
                segment = self.segments[key]
                self._update_segment_config(segment, config)
                self.update_count += 1
                return segment
                
            if len(self.segments) >= self.max_segments:
                self._cleanup_inactive_segments()
                
            config_hash = self._hash_config(config)
            
            def create_segment_func():
                self.creation_count += 1
                return LightSegment(
                    segment_ID=segment_id,
                    color=config.get("color", [0, 0, 0, 0]),
                    transparency=config.get("transparency", [0.0, 0.0, 0.0, 0.0]),
                    length=config.get("length", [0, 0, 0]),
                    move_speed=config.get("move_speed", 0.0),
                    move_range=config.get("move_range", [0, 0]),
                    initial_position=config.get("initial_position", 0),
                    is_edge_reflect=config.get("is_edge_reflect", False),
                    dimmer_time=config.get("dimmer_time", [0, 0, 0, 0, 0])
                )
                
            segment = self.pool_manager.get_segment(config_hash, create_segment_func)
            
            if segment is not None:
                self._update_segment_config(segment, config)
                self.reuse_count += 1
                
            self.segments[key] = segment
            self.segment_configs[key] = config.copy()
            self.active_segments.add(key)
            
            return segment
            
    def update_segment(self, effect_id: int, segment_id: int, 
                     param_name: str, value: Any) -> bool:
        """
        Update a parameter of a segment.
        
        Args:
            effect_id (int): Effect ID
            segment_id (int): Segment ID
            param_name (str): Parameter name
            value (Any): New parameter value
            
        Returns:
            bool: True if updated successfully
        """
        with self.lock:
            key = (effect_id, segment_id)
            
            if key not in self.segments:
                logger.warning(f"Segment {segment_id} not found in effect {effect_id}")
                return False
                
            segment = self.segments[key]
            segment.update_param(param_name, value)
            
            if key in self.segment_configs:
                self.segment_configs[key][param_name] = value
                
            self.update_count += 1
            self.active_segments.add(key)
            
            return True
            
    def remove_segment(self, effect_id: int, segment_id: int) -> bool:
        """
        Remove a segment.
        
        Args:
            effect_id (int): Effect ID
            segment_id (int): Segment ID
            
        Returns:
            bool: True if removed successfully
        """
        with self.lock:
            key = (effect_id, segment_id)
            
            if key not in self.segments:
                return False
                
            segment = self.segments.pop(key)
            config = self.segment_configs.pop(key, None)
            self.active_segments.discard(key)
            
            if config:
                config_hash = self._hash_config(config)
                self.pool_manager.return_segment(config_hash, segment)
                
            return True
            
    def mark_active(self, effect_id: int, segment_id: int) -> bool:
        """
        Mark a segment as active.
        
        Args:
            effect_id (int): Effect ID
            segment_id (int): Segment ID
            
        Returns:
            bool: True if marked successfully
        """
        with self.lock:
            key = (effect_id, segment_id)
            
            if key not in self.segments:
                return False
                
            self.active_segments.add(key)
            return True
            
    def get_segment(self, effect_id: int, segment_id: int) -> Optional[LightSegment]:
        """
        Get a segment.
        
        Args:
            effect_id (int): Effect ID
            segment_id (int): Segment ID
            
        Returns:
            Optional[LightSegment]: The segment if found, None otherwise
        """
        key = (effect_id, segment_id)
        return self.segments.get(key)
        
    def get_all_segments(self, effect_id: int) -> Dict[int, LightSegment]:
        """
        Get all segments for an effect.
        
        Args:
            effect_id (int): Effect ID
            
        Returns:
            Dict[int, LightSegment]: Dictionary of segments by ID
        """
        result = {}
        
        with self.lock:
            for (eid, sid), segment in self.segments.items():
                if eid == effect_id:
                    result[sid] = segment
                    
        return result
        
    def get_active_segments(self) -> Dict[Tuple[int, int], LightSegment]:
        """
        Get all active segments.
        
        Returns:
            Dict[Tuple[int, int], LightSegment]: Dictionary of segments by (effect_id, segment_id)
        """
        result = {}
        
        with self.lock:
            for key in self.active_segments:
                if key in self.segments:
                    result[key] = self.segments[key]
                    
        return result
        
    def update_all_segments(self, fps: int):
        """
        Update all segments.
        
        Args:
            fps (int): Frames per second
        """
        with self.lock:
            for key, segment in self.segments.items():
                segment.update_position(fps)
                
            current_time = time.time()
            if current_time - self.last_cleanup > 60:  
                self._cleanup_inactive_segments()
                self.last_cleanup = current_time
                
    def _cleanup_inactive_segments(self):
        """
        Clean up inactive segments.
        """
        all_keys = set(self.segments.keys())
        inactive_keys = all_keys - self.active_segments
        if len(self.segments) > self.max_segments:
            remove_count = len(self.segments) - self.max_segments
            
            keys_to_remove = list(inactive_keys)[:remove_count]
            
            for key in keys_to_remove:
                segment = self.segments.pop(key)
                config = self.segment_configs.pop(key, None)
                
                if config:
                    config_hash = self._hash_config(config)
                    self.pool_manager.return_segment(config_hash, segment)
                    
            logger.debug(f"Cleaned up {len(keys_to_remove)} inactive segments")
            
        self.active_segments = set()
        
    def _update_segment_config(self, segment: LightSegment, config: Dict[str, Any]):
        """
        Update segment configuration.
        
        Args:
            segment (LightSegment): Segment to update
            config (Dict[str, Any]): New configuration
        """
        for param_name, value in config.items():
            if hasattr(segment, param_name):
                segment.update_param(param_name, value)
                
    def _hash_config(self, config: Dict[str, Any]) -> str:
        """
        Create a hash of a segment configuration for pooling.
        
        Args:
            config (Dict[str, Any]): Segment configuration
            
        Returns:
            str: Hash string
        """
        key_parts = []
        
        for key in ["color", "transparency", "length"]:
            if key in config:
                if isinstance(config[key], list):
                    key_parts.append(f"{key}:{len(config[key])}")
                else:
                    key_parts.append(f"{key}:1")
   
        return ":".join(key_parts)
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Get segment manager statistics.
        
        Returns:
            Dict[str, Any]: Statistics
        """
        with self.lock:
            return {
                "total_segments": len(self.segments),
                "active_segments": len(self.active_segments),
                "max_segments": self.max_segments,
                "creation_count": self.creation_count,
                "reuse_count": self.reuse_count,
                "update_count": self.update_count,
                "pool_stats": self.pool_manager.get_stats()
            }