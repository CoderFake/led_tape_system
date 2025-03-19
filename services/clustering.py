import numpy as np
from typing import List, Dict, Set, Tuple, Optional, Any
import logging
from collections import defaultdict
import threading

from models.light_effect import LightEffect

logger = logging.getLogger(__name__)


class LEDCluster:
    """
    Represents a cluster of LEDs with similar properties or spatial proximity.
    """
    
    def __init__(self, cluster_id: int, led_indices: List[int] = None):
        """
        Initialize a LED cluster.
        
        Args:
            cluster_id (int): Unique identifier for this cluster
            led_indices (List[int]): List of LED indices in this cluster
        """
        self.cluster_id = cluster_id
        self.led_indices = led_indices or []
        self.effect_ids: Set[int] = set() 
        self.position = (0, 0, 0) 
        self.bounding_box = ((0, 0, 0), (0, 0, 0)) 
        self.priority = 0  
        self.active = True
        
    def add_led(self, led_index: int):
        """
        Add a LED to this cluster.
        
        Args:
            led_index (int): Index of the LED to add
        """
        if led_index not in self.led_indices:
            self.led_indices.append(led_index)
            
    def remove_led(self, led_index: int):
        """
        Remove a LED from this cluster.
        
        Args:
            led_index (int): Index of the LED to remove
        """
        if led_index in self.led_indices:
            self.led_indices.remove(led_index)
            
    def add_effect(self, effect_id: int):
        """
        Add an effect to this cluster.
        
        Args:
            effect_id (int): ID of the effect to add
        """
        self.effect_ids.add(effect_id)
        
    def remove_effect(self, effect_id: int):
        """
        Remove an effect from this cluster.
        
        Args:
            effect_id (int): ID of the effect to remove
        """
        self.effect_ids.discard(effect_id)
        
    def update_position(self, positions: List[Tuple[float, float, float]]):
        """
        Update the cluster position based on LED positions.
        
        Args:
            positions (List[Tuple[float, float, float]]): List of LED positions (x, y, z)
        """
        if not positions:
            return
            
        positions_array = np.array(positions)
        centroid = positions_array.mean(axis=0)
        self.position = tuple(centroid)

        min_pos = positions_array.min(axis=0)
        max_pos = positions_array.max(axis=0)
        self.bounding_box = (tuple(min_pos), tuple(max_pos))
        
    def get_info(self) -> Dict[str, Any]:
        """
        Get cluster information.
        
        Returns:
            Dict[str, Any]: Cluster information
        """
        return {
            "cluster_id": self.cluster_id,
            "led_count": len(self.led_indices),
            "effect_count": len(self.effect_ids),
            "position": self.position,
            "bounding_box": self.bounding_box,
            "priority": self.priority,
            "active": self.active
        }


class ClusteringService:
    """
    Service for clustering LEDs based on various criteria.
    """
    
    def __init__(self, max_leds_per_cluster: int = 1000):
        """
        Initialize the clustering service.
        
        Args:
            max_leds_per_cluster (int): Maximum number of LEDs per cluster
        """
        self.clusters: Dict[int, LEDCluster] = {}
        self.led_to_cluster: Dict[int, int] = {}  
        self.max_leds_per_cluster = max_leds_per_cluster
        self.next_cluster_id = 1
        self.lock = threading.RLock()
        
    def create_cluster(self, led_indices: List[int] = None) -> int:
        """
        Create a new cluster.
        
        Args:
            led_indices (List[int]): List of LED indices to add to the cluster
            
        Returns:
            int: Cluster ID
        """
        with self.lock:
            cluster_id = self.next_cluster_id
            self.next_cluster_id += 1
            
            cluster = LEDCluster(cluster_id, led_indices)
            self.clusters[cluster_id] = cluster

            if led_indices:
                for led_index in led_indices:
                    self.led_to_cluster[led_index] = cluster_id
                    
            logger.debug(f"Created cluster {cluster_id} with {len(led_indices or [])} LEDs")
            
            return cluster_id
    
    def delete_cluster(self, cluster_id: int) -> bool:
        """
        Delete a cluster.
        
        Args:
            cluster_id (int): ID of the cluster to delete
            
        Returns:
            bool: True if deleted, False if not found
        """
        with self.lock:
            if cluster_id not in self.clusters:
                return False

            for led_index in self.clusters[cluster_id].led_indices:
                self.led_to_cluster.pop(led_index, None)

            del self.clusters[cluster_id]
            
            logger.debug(f"Deleted cluster {cluster_id}")
            
            return True
    
    def add_led_to_cluster(self, cluster_id: int, led_index: int) -> bool:
        """
        Add a LED to a cluster.
        
        Args:
            cluster_id (int): ID of the cluster
            led_index (int): Index of the LED to add
            
        Returns:
            bool: True if added, False if cluster not found
        """
        with self.lock:
            if cluster_id not in self.clusters:
                return False
            
            if led_index in self.led_to_cluster and self.led_to_cluster[led_index] != cluster_id:
                old_cluster_id = self.led_to_cluster[led_index]
                if old_cluster_id in self.clusters:
                    self.clusters[old_cluster_id].remove_led(led_index)

            self.clusters[cluster_id].add_led(led_index)
            self.led_to_cluster[led_index] = cluster_id
            
            return True
    
    def get_cluster_for_led(self, led_index: int) -> Optional[int]:
        """
        Get the cluster ID for a LED.
        
        Args:
            led_index (int): Index of the LED
            
        Returns:
            Optional[int]: Cluster ID if found, None otherwise
        """
        return self.led_to_cluster.get(led_index)
    
    def cluster_by_linear_groups(self, led_count: int, group_size: int) -> List[int]:
        """
        Cluster LEDs into linear groups of fixed size.
        
        Args:
            led_count (int): Total number of LEDs
            group_size (int): Size of each group
            
        Returns:
            List[int]: List of cluster IDs
        """
        with self.lock:
            self.clusters.clear()
            self.led_to_cluster.clear()

            cluster_ids = []
            
            for i in range(0, led_count, group_size):
                start_index = i
                end_index = min(i + group_size, led_count)
                led_indices = list(range(start_index, end_index))
                
                cluster_id = self.create_cluster(led_indices)
                cluster_ids.append(cluster_id)
                
            logger.info(f"Created {len(cluster_ids)} linear clusters with group size {group_size}")
            
            return cluster_ids
    
    def cluster_by_effects(self, effects: Dict[int, LightEffect]) -> List[int]:
        """
        Cluster LEDs based on which effects they are used in.
        
        Args:
            effects (Dict[int, LightEffect]): Dictionary of effects
            
        Returns:
            List[int]: List of cluster IDs
        """
        with self.lock:
            led_to_effects: Dict[int, Set[int]] = defaultdict(set)

            for effect_id, effect in effects.items():
                led_count = effect.led_count
                for i in range(led_count):
                    led_to_effects[i].add(effect_id)

            effect_groups: Dict[frozenset, List[int]] = defaultdict(list)
            
            for led_index, effect_ids in led_to_effects.items():
                effect_key = frozenset(effect_ids)
                effect_groups[effect_key].append(led_index)

            cluster_ids = []
            
            for effect_key, led_indices in effect_groups.items():
                for i in range(0, len(led_indices), self.max_leds_per_cluster):
                    group = led_indices[i:i + self.max_leds_per_cluster]
                    cluster_id = self.create_cluster(group)

                    for effect_id in effect_key:
                        self.clusters[cluster_id].add_effect(effect_id)
                        
                    cluster_ids.append(cluster_id)
            
            logger.info(f"Created {len(cluster_ids)} effect-based clusters")
            
            return cluster_ids
    
    def get_clusters_for_effect(self, effect_id: int) -> List[int]:
        """
        Get clusters associated with an effect.
        
        Args:
            effect_id (int): Effect ID
            
        Returns:
            List[int]: List of cluster IDs
        """
        with self.lock:
            return [
                cluster.cluster_id
                for cluster in self.clusters.values()
                if effect_id in cluster.effect_ids
            ]
    
    def get_active_clusters(self) -> List[int]:
        """
        Get all active clusters.
        
        Returns:
            List[int]: List of active cluster IDs
        """
        with self.lock:
            return [
                cluster.cluster_id
                for cluster in self.clusters.values()
                if cluster.active
            ]
    
    def set_cluster_priority(self, cluster_id: int, priority: int):
        """
        Set the priority of a cluster.
        
        Args:
            cluster_id (int): Cluster ID
            priority (int): Priority value
        """
        with self.lock:
            if cluster_id in self.clusters:
                self.clusters[cluster_id].priority = priority
                
    def set_cluster_active(self, cluster_id: int, active: bool):
        """
        Set whether a cluster is active.
        
        Args:
            cluster_id (int): Cluster ID
            active (bool): Whether the cluster is active
        """
        with self.lock:
            if cluster_id in self.clusters:
                self.clusters[cluster_id].active = active
                
    def get_cluster_info(self, cluster_id: int) -> Optional[Dict[str, Any]]:
        """
        Get information about a cluster.
        
        Args:
            cluster_id (int): Cluster ID
            
        Returns:
            Optional[Dict[str, Any]]: Cluster information if found, None otherwise
        """
        with self.lock:
            if cluster_id in self.clusters:
                return self.clusters[cluster_id].get_info()
            return None
    
    def get_all_cluster_info(self) -> Dict[int, Dict[str, Any]]:
        """
        Get information about all clusters.
        
        Returns:
            Dict[int, Dict[str, Any]]: Dictionary of cluster information by ID
        """
        with self.lock:
            return {
                cluster_id: cluster.get_info()
                for cluster_id, cluster in self.clusters.items()
            }