
import numpy as np


def interpolate_color(color1, color2, ratio):
    """
    Interpolate between two colors.
    
    Args:
        color1 (list): RGB values of the first color [r, g, b]
        color2 (list): RGB values of the second color [r, g, b]
        ratio (float): Interpolation ratio (0-1)
        
    Returns:
        list: Interpolated RGB color [r, g, b]
    """
    return [
        int(color1[0] + (color2[0] - color1[0]) * ratio),
        int(color1[1] + (color2[1] - color1[1]) * ratio),
        int(color1[2] + (color2[2] - color1[2]) * ratio),
    ]


def blend_colors(colors, transparencies):
    """
    Blend multiple colors based on their transparencies.
    
    Args:
        colors (list): List of RGB colors [[r, g, b], ...]
        transparencies (list): List of transparency values [0-1]
        
    Returns:
        list: Blended RGB color [r, g, b]
    """
    if not colors:
        return [0, 0, 0]
    
    result = [0, 0, 0]
    total_alpha = 0.0
    
    for i in range(len(colors) - 1, -1, -1):
        alpha = 1.0 - transparencies[i]
        if alpha <= 0.0:
            continue
        
        remaining_alpha = 1.0 - total_alpha
        if remaining_alpha <= 0.0:
            break
            
        current_alpha = alpha * remaining_alpha
        total_alpha += current_alpha
        
        for j in range(3):
            result[j] += int(colors[i][j] * current_alpha)

    return [max(0, min(255, int(c / max(total_alpha, 0.001)))) for c in result]


def color_from_palette(color_index, palette_size=16777216):
    """
    Get RGB color from color index (0 to 16,777,215).
    Supports full 24-bit RGB color space (16.7 million colors).
    
    Args:
        color_index (int): Color index (0-16777215)
        palette_size (int): Total number of colors in palette
        
    Returns:
        list: RGB color [r, g, b]
    """
    color_index = max(0, min(palette_size - 1, color_index))
    r = (color_index >> 16) & 0xFF
    g = (color_index >> 8) & 0xFF
    b = color_index & 0xFF
    return [r, g, b]


def apply_dimming(color, dimming_factor):
    """
    Apply dimming factor to a color.
    
    Args:
        color (list): RGB color [r, g, b]
        dimming_factor (float): Dimming factor (0-1)
        
    Returns:
        list: Dimmed RGB color [r, g, b]
    """
    return [
        int(c * dimming_factor) for c in color
    ]


def calculate_gradient_colors(colors, length):
    """
    Calculate a gradient of colors for a given length.
    
    Args:
        colors (list): List of RGB colors [[r, g, b], ...]
        length (int): Number of colors to generate
        
    Returns:
        list: List of RGB colors for the gradient
    """
    if len(colors) < 2:
        return [colors[0]] * length if colors else [[0, 0, 0]] * length
    
    result = []
    segments = len(colors) - 1
    colors_per_segment = length // segments
    remainder = length % segments
    
    for i in range(segments):
        segment_length = colors_per_segment + (1 if i < remainder else 0)
        for j in range(segment_length):
            ratio = j / max(1, segment_length - 1)
            result.append(interpolate_color(colors[i], colors[i+1], ratio))
            
    return result