from typing import Dict, List, Any, Tuple
import numpy as np

from models.light_segment import LightSegment
from utils.color_utils import blend_colors, interpolate_color


class LightEffect:
    """
    Manages multiple light segments to create a combined lighting effect.
    """
    
    def __init__(self, effect_ID: int, led_count: int, fps: int):
        """
        Initialize a LightEffect.
        
        Args:
            effect_ID (int): Unique identifier for this effect
            led_count (int): Total number of LEDs
            fps (int): Frames per second for animation
        """
        self.effect_ID = effect_ID
        self.segments: Dict[int, LightSegment] = {}
        self.led_count = led_count
        self.fps = fps
        self.time_step = 1.0 / fps

        self.led_colors = np.zeros((led_count, 3), dtype=np.uint8)
        self.led_transparency = np.ones(led_count, dtype=np.float32)
        
    def add_segment(self, segment_ID: int, segment: LightSegment):
        """
        Add a light segment to this effect.
        
        Args:
            segment_ID (int): Unique identifier for the segment
            segment (LightSegment): The segment to add
        """
        self.segments[segment_ID] = segment
        
    def remove_segment(self, segment_ID: int) -> bool:
        """
        Remove a light segment from this effect.
        
        Args:
            segment_ID (int): ID of the segment to remove
            
        Returns:
            bool: True if segment was removed, False if not found
        """
        if segment_ID in self.segments:
            del self.segments[segment_ID]
            return True
        return False
        
    def update_segment_param(self, segment_ID: int, param_name: str, value: Any):
        """
        Update a parameter of a specific light segment.
        
        Args:
            segment_ID (int): ID of the segment to update
            param_name (str): Name of the parameter to update
            value (Any): New value for the parameter
        """
        if segment_ID in self.segments:
            self.segments[segment_ID].update_param(param_name, value)
            
    def update_all(self):
        """
        Update all light segments for the current frame.
        """
        for segment in self.segments.values():
            segment.update_position(self.fps)
            
    def get_led_output(self) -> List[List[int]]:
        """
        Calculate the final color values for all LEDs.
        
        Returns:
            List[List[int]]: List of RGB colors for each LED
        """
        led_colors = [[0, 0, 0] for _ in range(self.led_count)]
        led_transparency = [1.0 for _ in range(self.led_count)]

        for segment in self.segments.values():
            positions, colors = segment.get_light_data()
            
            if not positions or not colors:
                continue

            for i in range(len(positions) - 1):
                start_pos, end_pos = positions[i], positions[i+1]
                start_color, end_color = colors[i], colors[i+1]
                start_trans, end_trans = segment.transparency[i], segment.transparency[i+1]
                
                start_led = max(0, min(self.led_count - 1, int(start_pos)))
                end_led = max(0, min(self.led_count - 1, int(end_pos)))
                
                if start_led > self.led_count - 1 or end_led < 0:
                    continue
                    
                if start_led == end_led:
                    if led_transparency[start_led] > start_trans:
                        led_colors[start_led] = start_color
                        led_transparency[start_led] = start_trans
                else:
                    led_range = abs(end_led - start_led) + 1
                    direction = 1 if end_led >= start_led else -1
                    
                    for j in range(led_range):
                        pos = start_led + j * direction
                        if pos < 0 or pos >= self.led_count:
                            continue
                            
                        ratio = j / max(1, led_range - 1)
                        
                        color = interpolate_color(start_color, end_color, ratio)
                        trans = start_trans + (end_trans - start_trans) * ratio
                        
                        if led_transparency[pos] > trans:
                            led_colors[pos] = color
                            led_transparency[pos] = trans

        for i in range(self.led_count):
            opacity = 1.0 - led_transparency[i]
            if opacity > 0:
                led_colors[i] = [int(c * opacity) for c in led_colors[i]]
        
        return led_colors