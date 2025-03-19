import numpy as np
from typing import List, Dict, Tuple, Set, Any, Optional, Callable
import logging
import threading
from collections import defaultdict

logger = logging.getLogger(__name__)


class SpatialIndex:
    """
    Base class for spatial indexing implementations.
    """
    
    def __init__(self):
        """
        Initialize the spatial index.
        """
        self.lock = threading.RLock()
        
    def insert(self, object_id: int, position: Tuple[float, float, float]) -> bool:
        """
        Insert an object into the index.
        
        Args:
            object_id (int): Unique object identifier
            position (Tuple[float, float, float]): 3D position
            
        Returns:
            bool: True if inserted successfully
        """
        return False
        
    def remove(self, object_id: int) -> bool:
        """
        Remove an object from the index.
        
        Args:
            object_id (int): Object identifier
            
        Returns:
            bool: True if removed successfully
        """
        return False
        
    def update(self, object_id: int, position: Tuple[float, float, float]) -> bool:
        """
        Update an object's position.
        
        Args:
            object_id (int): Object identifier
            position (Tuple[float, float, float]): New 3D position
            
        Returns:
            bool: True if updated successfully
        """
        self.remove(object_id)
        return self.insert(object_id, position)
        
    def query_point(self, position: Tuple[float, float, float], radius: float) -> List[int]:
        """
        Query objects near a point.
        
        Args:
            position (Tuple[float, float, float]): Query position
            radius (float): Search radius
            
        Returns:
            List[int]: List of object IDs within the radius
        """
        return []
        
    def query_range(self, min_point: Tuple[float, float, float], 
                  max_point: Tuple[float, float, float]) -> List[int]:
        """
        Query objects within a 3D range.
        
        Args:
            min_point (Tuple[float, float, float]): Minimum coordinates
            max_point (Tuple[float, float, float]): Maximum coordinates
            
        Returns:
            List[int]: List of object IDs within the range
        """
        return []
        
    def clear(self):
        """
        Clear the index.
        """
        pass


class GridIndex(SpatialIndex):
    """
    Grid-based spatial index for LED positions.
    """
    
    def __init__(self, cell_size: float = 10.0):
        """
        Initialize the grid index.
        
        Args:
            cell_size (float): Size of each grid cell
        """
        super().__init__()
        self.cell_size = cell_size
        self.grid: Dict[Tuple[int, int, int], Set[int]] = defaultdict(set)
        self.positions: Dict[int, Tuple[float, float, float]] = {}
        
    def _get_cell(self, position: Tuple[float, float, float]) -> Tuple[int, int, int]:
        """
        Get the grid cell for a position.
        
        Args:
            position (Tuple[float, float, float]): 3D position
            
        Returns:
            Tuple[int, int, int]: Grid cell coordinates
        """
        x, y, z = position
        return (int(x // self.cell_size), int(y // self.cell_size), int(z // self.cell_size))
        
    def insert(self, object_id: int, position: Tuple[float, float, float]) -> bool:
        """
        Insert an object into the index.
        
        Args:
            object_id (int): Unique object identifier
            position (Tuple[float, float, float]): 3D position
            
        Returns:
            bool: True if inserted successfully
        """
        with self.lock:
            self.remove(object_id)
            
            self.positions[object_id] = position
            
            cell = self._get_cell(position)
            self.grid[cell].add(object_id)
            
            return True
            
    def remove(self, object_id: int) -> bool:
        """
        Remove an object from the index.
        
        Args:
            object_id (int): Object identifier
            
        Returns:
            bool: True if removed successfully
        """
        with self.lock:
            if object_id not in self.positions:
                return False
                
            position = self.positions.pop(object_id)
            
            cell = self._get_cell(position)
            if cell in self.grid:
                self.grid[cell].discard(object_id)
                if not self.grid[cell]:
                    del self.grid[cell]
                    
            return True
            
    def query_point(self, position: Tuple[float, float, float], radius: float) -> List[int]:
        """
        Query objects near a point.
        
        Args:
            position (Tuple[float, float, float]): Query position
            radius (float): Search radius
            
        Returns:
            List[int]: List of object IDs within the radius
        """
        with self.lock:
            result = []
            
            cell_radius = int(radius / self.cell_size) + 1
            center_cell = self._get_cell(position)
            cx, cy, cz = center_cell
            
            radius_sq = radius * radius
            
            for x in range(cx - cell_radius, cx + cell_radius + 1):
                for y in range(cy - cell_radius, cy + cell_radius + 1):
                    for z in range(cz - cell_radius, cz + cell_radius + 1):
                        cell = (x, y, z)
                        if cell in self.grid:
                            for object_id in self.grid[cell]:
                                obj_pos = self.positions[object_id]
                                
                                dx = obj_pos[0] - position[0]
                                dy = obj_pos[1] - position[1]
                                dz = obj_pos[2] - position[2]
                                dist_sq = dx*dx + dy*dy + dz*dz
                                
                                if dist_sq <= radius_sq:
                                    result.append(object_id)
                                    
            return result
            
    def query_range(self, min_point: Tuple[float, float, float], 
                  max_point: Tuple[float, float, float]) -> List[int]:
        """
        Query objects within a 3D range.
        
        Args:
            min_point (Tuple[float, float, float]): Minimum coordinates
            max_point (Tuple[float, float, float]): Maximum coordinates
            
        Returns:
            List[int]: List of object IDs within the range
        """
        with self.lock:
            result = []
            
            min_cell = self._get_cell(min_point)
            max_cell = self._get_cell(max_point)
            
            min_x, min_y, min_z = min_cell
            max_x, max_y, max_z = max_cell
            
            for x in range(min_x, max_x + 1):
                for y in range(min_y, max_y + 1):
                    for z in range(min_z, max_z + 1):
                        cell = (x, y, z)
                        if cell in self.grid:
                            for object_id in self.grid[cell]:
                                obj_pos = self.positions[object_id]
                                
                                if (min_point[0] <= obj_pos[0] <= max_point[0] and
                                    min_point[1] <= obj_pos[1] <= max_point[1] and
                                    min_point[2] <= obj_pos[2] <= max_point[2]):
                                    result.append(object_id)
                                    
            return result
            
    def clear(self):
        """
        Clear the index.
        """
        with self.lock:
            self.grid.clear()
            self.positions.clear()
            
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the grid index.
        
        Returns:
            Dict[str, Any]: Index statistics
        """
        with self.lock:
            occupancy = [len(cell) for cell in self.grid.values()]
            
            return {
                "cell_size": self.cell_size,
                "object_count": len(self.positions),
                "cell_count": len(self.grid),
                "avg_occupancy": np.mean(occupancy) if occupancy else 0,
                "max_occupancy": max(occupancy) if occupancy else 0,
                "min_occupancy": min(occupancy) if occupancy else 0,
                "std_occupancy": np.std(occupancy) if occupancy else 0,
            }


class QuadTreeNode:
    """
    Node in a QuadTree spatial index.
    """
    
    def __init__(self, center: Tuple[float, float], size: float, depth: int = 0, max_depth: int = 8):
        """
        Initialize a QuadTree node.
        
        Args:
            center (Tuple[float, float]): Center coordinates
            size (float): Size of the node
            depth (int): Current depth
            max_depth (int): Maximum tree depth
        """
        self.center = center
        self.size = size
        self.depth = depth
        self.max_depth = max_depth
        self.objects: Dict[int, Tuple[float, float]] = {}
        self.children: List[Optional[QuadTreeNode]] = [None, None, None, None]  # NW, NE, SW, SE
        
    def is_leaf(self) -> bool:
        """
        Check if this is a leaf node.
        
        Returns:
            bool: True if leaf node
        """
        return all(child is None for child in self.children)
        
    def should_split(self) -> bool:
        """
        Check if this node should split.
        
        Returns:
            bool: True if should split
        """
        return self.depth < self.max_depth and len(self.objects) > 4
        
    def contains(self, position: Tuple[float, float]) -> bool:
        """
        Check if a position is within this node.
        
        Args:
            position (Tuple[float, float]): 2D position
            
        Returns:
            bool: True if within node
        """
        x, y = position
        cx, cy = self.center
        half_size = self.size / 2
        
        return (cx - half_size <= x <= cx + half_size and
                cy - half_size <= y <= cy + half_size)
                
    def get_child_index(self, position: Tuple[float, float]) -> int:
        """
        Get the index of the child node for a position.
        
        Args:
            position (Tuple[float, float]): 2D position
            
        Returns:
            int: Child index (0-3)
        """
        x, y = position
        cx, cy = self.center
        
        if y >= cy:
            return 0 if x < cx else 1  # NW, NE
        else:
            return 2 if x < cx else 3  # SW, SE
            
    def split(self):
        """
        Split this node into four children.
        """
        if not self.is_leaf():
            return
            
        cx, cy = self.center
        half_size = self.size / 2
        quarter_size = half_size / 2
        next_depth = self.depth + 1
        
        self.children[0] = QuadTreeNode((cx - quarter_size, cy + quarter_size), half_size, next_depth, self.max_depth)  # NW
        self.children[1] = QuadTreeNode((cx + quarter_size, cy + quarter_size), half_size, next_depth, self.max_depth)  # NE
        self.children[2] = QuadTreeNode((cx - quarter_size, cy - quarter_size), half_size, next_depth, self.max_depth)  # SW
        self.children[3] = QuadTreeNode((cx + quarter_size, cy - quarter_size), half_size, next_depth, self.max_depth)  # SE
        
        objects = self.objects
        self.objects = {}
        
        for obj_id, position in objects.items():
            child_idx = self.get_child_index(position)
            self.children[child_idx].insert(obj_id, position)


class QuadTreeIndex(SpatialIndex):
    """
    QuadTree-based spatial index for 2D LED positions.
    """
    
    def __init__(self, center: Tuple[float, float] = (0, 0), size: float = 1000.0, max_depth: int = 8):
        """
        Initialize the QuadTree index.
        
        Args:
            center (Tuple[float, float]): Center coordinates
            size (float): Size of the root node
            max_depth (int): Maximum tree depth
        """
        super().__init__()
        self.root = QuadTreeNode(center, size, 0, max_depth)
        self.object_positions: Dict[int, Tuple[float, float, float]] = {}
        
    def insert(self, object_id: int, position: Tuple[float, float, float]) -> bool:
        """
        Insert an object into the index.
        
        Args:
            object_id (int): Unique object identifier
            position (Tuple[float, float, float]): 3D position
            
        Returns:
            bool: True if inserted successfully
        """
        with self.lock:
            pos_2d = (position[0], position[1])
            self.object_positions[object_id] = position
            
            return self._insert_recursive(self.root, object_id, pos_2d)
            
    def _insert_recursive(self, node: QuadTreeNode, object_id: int, position: Tuple[float, float]) -> bool:
        """
        Recursively insert an object into the QuadTree.
        
        Args:
            node (QuadTreeNode): Current node
            object_id (int): Object identifier
            position (Tuple[float, float]): 2D position
            
        Returns:
            bool: True if inserted successfully
        """
        if not node.contains(position):
            return False
            
        if node.is_leaf() or node.depth == node.max_depth:
            node.objects[object_id] = position
            
            if node.should_split():
                node.split()
                
            return True
            
        child_idx = node.get_child_index(position)
        return self._insert_recursive(node.children[child_idx], object_id, position)
        
    def remove(self, object_id: int) -> bool:
        """
        Remove an object from the index.
        
        Args:
            object_id (int): Object identifier
            
        Returns:
            bool: True if removed successfully
        """
        with self.lock:
            if object_id not in self.object_positions:
                return False
                
            position = self.object_positions.pop(object_id)
            pos_2d = (position[0], position[1])
            
            return self._remove_recursive(self.root, object_id, pos_2d)
            
    def _remove_recursive(self, node: QuadTreeNode, object_id: int, position: Tuple[float, float]) -> bool:
        """
        Recursively remove an object from the QuadTree.
        
        Args:
            node (QuadTreeNode): Current node
            object_id (int): Object identifier
            position (Tuple[float, float]): 2D position
            
        Returns:
            bool: True if removed successfully
        """
        if not node.contains(position):
            return False
            
        if object_id in node.objects:
            del node.objects[object_id]
            return True
            
        if node.is_leaf():
            return False
            
        child_idx = node.get_child_index(position)
        return self._remove_recursive(node.children[child_idx], object_id, position)
        
    def query_point(self, position: Tuple[float, float, float], radius: float) -> List[int]:
        """
        Query objects near a point.
        
        Args:
            position (Tuple[float, float, float]): Query position
            radius (float): Search radius
            
        Returns:
            List[int]: List of object IDs within the radius
        """
        with self.lock:
            pos_2d = (position[0], position[1])
            
            result = []
            self._query_point_recursive(self.root, pos_2d, radius, result)
            
            return result
            
    def _query_point_recursive(self, node: QuadTreeNode, position: Tuple[float, float], 
                             radius: float, result: List[int]):
        """
        Recursively query objects near a point.
        
        Args:
            node (QuadTreeNode): Current node
            position (Tuple[float, float]): 2D query position
            radius (float): Search radius
            result (List[int]): List to store results
        """
        if not self._intersects_circle(node, position, radius):
            return
            
        for obj_id, obj_pos in node.objects.items():
            dx = obj_pos[0] - position[0]
            dy = obj_pos[1] - position[1]
            dist_sq = dx*dx + dy*dy
            
            if dist_sq <= radius*radius:
                result.append(obj_id)
                
        if node.is_leaf():
            return
            
        for child in node.children:
            if child is not None:
                self._query_point_recursive(child, position, radius, result)
                
    def _intersects_circle(self, node: QuadTreeNode, position: Tuple[float, float], radius: float) -> bool:
        """
        Check if a node intersects a circle.
        
        Args:
            node (QuadTreeNode): QuadTree node
            position (Tuple[float, float]): Circle center
            radius (float): Circle radius
            
        Returns:
            bool: True if intersects
        """
        cx, cy = node.center
        px, py = position
        half_size = node.size / 2
        
        closest_x = max(cx - half_size, min(px, cx + half_size))
        closest_y = max(cy - half_size, min(py, cy + half_size))

        dx = closest_x - px
        dy = closest_y - py
        dist_sq = dx*dx + dy*dy
        
        return dist_sq <= radius*radius
        
    def query_range(self, min_point: Tuple[float, float, float], 
                  max_point: Tuple[float, float, float]) -> List[int]:
        """
        Query objects within a 3D range.
        
        Args:
            min_point (Tuple[float, float, float]): Minimum coordinates
            max_point (Tuple[float, float, float]): Maximum coordinates
            
        Returns:
            List[int]: List of object IDs within the range
        """
        with self.lock:
            min_2d = (min_point[0], min_point[1])
            max_2d = (max_point[0], max_point[1])
            
            result = []
            self._query_range_recursive(self.root, min_2d, max_2d, result)
            
            return result
            
    def _query_range_recursive(self, node: QuadTreeNode, min_point: Tuple[float, float], 
                             max_point: Tuple[float, float], result: List[int]):
        """
        Recursively query objects within a range.
        
        Args:
            node (QuadTreeNode): Current node
            min_point (Tuple[float, float]): Minimum coordinates
            max_point (Tuple[float, float]): Maximum coordinates
            result (List[int]): List to store results
        """
        if not self._intersects_range(node, min_point, max_point):
            return

        for obj_id, obj_pos in node.objects.items():
            if (min_point[0] <= obj_pos[0] <= max_point[0] and
                min_point[1] <= obj_pos[1] <= max_point[1]):
                result.append(obj_id)

        if node.is_leaf():
            return
            
        for child in node.children:
            if child is not None:
                self._query_range_recursive(child, min_point, max_point, result)
                
    def _intersects_range(self, node: QuadTreeNode, min_point: Tuple[float, float], 
                        max_point: Tuple[float, float]) -> bool:
        """
        Check if a node intersects a range.
        
        Args:
            node (QuadTreeNode): QuadTree node
            min_point (Tuple[float, float]): Minimum coordinates
            max_point (Tuple[float, float]): Maximum coordinates
            
        Returns:
            bool: True if intersects
        """
        cx, cy = node.center
        half_size = node.size / 2
        
        node_min_x = cx - half_size
        node_min_y = cy - half_size
        node_max_x = cx + half_size
        node_max_y = cy + half_size
        
        return not (node_max_x < min_point[0] or node_min_x > max_point[0] or
                   node_max_y < min_point[1] or node_min_y > max_point[1])
                   
    def clear(self):
        """
        Clear the index.
        """
        with self.lock:
            self.root = QuadTreeNode(self.root.center, self.root.size, 0, self.root.max_depth)
            self.object_positions.clear()


def create_spatial_index(index_type: str = "grid", **kwargs) -> SpatialIndex:
    """
    Create a spatial index of the specified type.
    
    Args:
        index_type (str): Type of index ("grid" or "quadtree")
        **kwargs: Additional parameters for the index
        
    Returns:
        SpatialIndex: Spatial index instance
    """
    if index_type.lower() == "grid":
        cell_size = kwargs.get("cell_size", 10.0)
        return GridIndex(cell_size)
    elif index_type.lower() == "quadtree":
        center = kwargs.get("center", (0, 0))
        size = kwargs.get("size", 1000.0)
        max_depth = kwargs.get("max_depth", 8)
        return QuadTreeIndex(center, size, max_depth)
    else:
        logger.warning(f"Unknown index type: {index_type}, falling back to grid index")
        return GridIndex()