import time
import numpy as np
from typing import List, Any, Tuple

from utils.color_utils import (
    color_from_palette,
    interpolate_color,
    apply_dimming,
    calculate_gradient_colors
)


class LightSegment:
    """
    Represents a segment of light with specific properties like color, transparency, and movement.
    """
    
    def __init__(self, segment_ID: int, color: List[int], transparency: List[float], 
                 length: List[int], move_speed: float, move_range: List[int], 
                 initial_position: int, is_edge_reflect: bool, dimmer_time: List[int]):
        """
        Initialize a LightSegment.
        
        Args:
            segment_ID (int): Unique identifier for this segment
            color (list): List of 4 color indices from color palette
            transparency (list): List of transparency values (0.0-1.0) for each color point
            length (list): List of 3 length values for each segment section
            move_speed (float): Number of LED positions to move per second (+ for right, - for left)
            move_range (list): Range of movement [left_edge, right_edge]
            initial_position (int): Initial position of the segment
            is_edge_reflect (bool): Whether to reflect at edges
            dimmer_time (list): List of 5 time values for fade in/out control
        """
        self.segment_ID = segment_ID
        self.color = color
        self.transparency = transparency
        self.length = length
        self.move_speed = move_speed
        self.move_range = move_range
        self.initial_position = initial_position
        self.current_position = float(initial_position)
        self.is_edge_reflect = is_edge_reflect
        self.dimmer_time = dimmer_time
        self.time = 0.0
        self.start_time = time.time()
        self.direction = 1 if move_speed >= 0 else -1
        
        self.rgb_color = self.calculate_rgb()

        self.gradient_cache = {}
        self.update_gradient_cache()
        
    def update_param(self, param_name: str, value: Any):
        """
        Update a specific parameter.
        
        Args:
            param_name (str): Name of the parameter to update
            value (Any): New value for the parameter
        """
        if param_name == "color":
            setattr(self, param_name, value)
            self.rgb_color = self.calculate_rgb()
            self.update_gradient_cache()
        elif param_name == "length":
            setattr(self, param_name, value)
            self.update_gradient_cache()
        elif param_name == "move_speed":
            old_direction = self.direction
            self.move_speed = value
            self.direction = 1 if self.move_speed >= 0 else -1
            if old_direction != self.direction:
                self.update_gradient_cache()
        else:
            setattr(self, param_name, value)
    
    def update_gradient_cache(self):
        """
        Update the pre-calculated gradient cache for optimization.
        """
        self.gradient_cache = {}
    
    def calculate_rgb(self) -> List[List[int]]:
        """
        Calculate RGB values from color palette indices.
        
        Returns:
            List[List[int]]: List of RGB values [[r, g, b], ...]
        """
        return [color_from_palette(c) for c in self.color]
    
    def update_position(self, fps: int):
        """
        Update position based on the current frame rate.
        
        Args:
            fps (int): Frames per second
        """
        dt = 1.0 / fps
        self.time += dt

        delta = self.move_speed * dt
        new_position = self.current_position + delta
        
        if self.is_edge_reflect:
            if new_position < self.move_range[0]:
                overflow = self.move_range[0] - new_position
                new_position = self.move_range[0] + overflow
                self.move_speed *= -1
            elif new_position > self.move_range[1]:
                overflow = new_position - self.move_range[1]
                new_position = self.move_range[1] - overflow
                self.move_speed *= -1
        else:
            if new_position < self.move_range[0]:
                new_position = self.move_range[1] - (self.move_range[0] - new_position) % (self.move_range[1] - self.move_range[0] + 1)
            elif new_position > self.move_range[1]:
                new_position = self.move_range[0] + (new_position - self.move_range[0]) % (self.move_range[1] - self.move_range[0] + 1)
        
        self.current_position = new_position
    
    def apply_dimming(self) -> float:
        """
        Calculate dimming factor based on dimmer_time.
        
        Returns:
            float: Dimming factor (0.0-1.0)
        """
        if not self.dimmer_time or len(self.dimmer_time) < 5:
            return 1.0 
            
        delay_in, fade_in, stay, fade_out, delay_out = self.dimmer_time
        
        total_time = delay_in + fade_in + stay + fade_out + delay_out
        if total_time <= 0:
            return 1.0
            
        current_time = (time.time() - self.start_time) % total_time
        
        if current_time < delay_in:
            return 0.0 
        elif current_time < delay_in + fade_in:
            progress = (current_time - delay_in) / fade_in
            return progress
        elif current_time < delay_in + fade_in + stay:
            return 1.0
        elif current_time < delay_in + fade_in + stay + fade_out:
            progress = (current_time - delay_in - fade_in - stay) / fade_out
            return 1.0 - progress
        else:
            return 0.0  
    
    def get_light_data(self) -> Tuple[List[float], List[List[int]]]:
        """
        Calculate current light data based on position, transparency, and gradient.
        
        Returns:
            Tuple[List[float], List[List[int]]]: (Positions, Colors)
        """
        total_length = sum(self.length)
        if total_length <= 0:
            return [], []
            
        color_points = []
        position_offsets = [0]
        
        for i in range(len(self.length)):
            position_offsets.append(position_offsets[-1] + self.length[i])

        dimming_factor = self.apply_dimming()
        
        base_position = self.current_position
        if self.move_speed < 0:
            position_offsets = [total_length - offset for offset in reversed(position_offsets)]
            
        positions = [base_position + offset for offset in position_offsets]
      
        dimmed_colors = [apply_dimming(color, dimming_factor) for color in self.rgb_color]
        
        return positions, dimmed_colors