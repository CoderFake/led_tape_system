import pygame
import time
import math
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
import threading
import logging

from models.light_effect import LightEffect
from controllers.effect_manager import EffectManager
from services.clustering import ClusteringService

logger = logging.getLogger(__name__)


class PreviewSettings:
    """
    Settings for LED preview.
    """
    
    def __init__(self):
        """
        Initialize preview settings.
        """
        self.width = 1200
        self.height = 800
        self.background_color = (20, 20, 20)
        self.fps = 60
        
        self.led_size = 5
        self.led_spacing = 0
        self.brightness = 1.0
        
        self.layout_type = "linear" 
        self.layout_params = {}
        
        self.zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.show_labels = True
        self.show_stats = True
        self.show_controls = False
        
    def update(self, settings: Dict[str, Any]):
        """
        Update settings from a dictionary.
        
        Args:
            settings (Dict[str, Any]): New settings values
        """
        for key, value in settings.items():
            if hasattr(self, key):
                setattr(self, key, value)


class LargeScalePreview:
    """
    Preview for large-scale LED installations.
    """
    
    def __init__(self, effect_manager: EffectManager, 
                clustering_service: Optional[ClusteringService] = None):
        """
        Initialize the large-scale preview.
        
        Args:
            effect_manager (EffectManager): Effect manager
            clustering_service (ClusteringService): Optional clustering service
        """
        self.effect_manager = effect_manager
        self.clustering_service = clustering_service
        self.settings = PreviewSettings()
        self.running = False
        self.paused = False
        
        self.screen = None
        self.clock = None
        self.font = None
        self.ui_elements = []
        
        self.led_positions = []
        self.led_colors = []
        self.led_clusters = {}
        
        self.fps_history = []
        self.render_times = []
        self.last_frame_time = 0
        
        self.selected_cluster = None
        self.selected_effect = None
        self.mouse_pos = (0, 0)
        
        self.lock = threading.RLock()
        
    def initialize(self):
        """
        Initialize the preview display.
        """
        if self.screen is not None:
            return
            
        pygame.init()
        pygame.display.set_caption("LED Tape Light System - Large Scale Preview")
        self.screen = pygame.display.set_mode((self.settings.width, self.settings.height))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        
        self._generate_layout()
        
        logger.info(f"Initialized preview with {len(self.led_positions)} LEDs")
        
    def _generate_layout(self):
        """
        Generate LED positions based on layout settings.
        """
        layout_type = self.settings.layout_type
        
        if layout_type == "linear":
            self._generate_linear_layout()
        elif layout_type == "grid":
            self._generate_grid_layout()
        elif layout_type == "circle":
            self._generate_circle_layout()
        elif layout_type == "custom":
            self._load_custom_layout()
        else:
            logger.warning(f"Unknown layout type: {layout_type}, defaulting to linear")
            self._generate_linear_layout()
            
        self.led_colors = [[0, 0, 0] for _ in range(len(self.led_positions))]
        
        if self.clustering_service:
            self._generate_clusters()
            
    def _generate_linear_layout(self):
        """
        Generate positions for a linear layout.
        """
        led_count = self.settings.layout_params.get("led_count", 100)
        rows = self.settings.layout_params.get("rows", 1)
        spacing = self.settings.layout_params.get("spacing", 10)
        row_spacing = self.settings.layout_params.get("row_spacing", 20)
        start_x = self.settings.layout_params.get("start_x", 50)
        start_y = self.settings.layout_params.get("start_y", 50)
        
        self.led_positions = []
        
        for row in range(rows):
            y = start_y + row * row_spacing
            for i in range(led_count):
                x = start_x + i * spacing
                self.led_positions.append((x, y))
                
    def _generate_grid_layout(self):
        """
        Generate positions for a grid layout.
        """
        width = self.settings.layout_params.get("width", 10)
        height = self.settings.layout_params.get("height", 10)
        spacing = self.settings.layout_params.get("spacing", 20)
        start_x = self.settings.layout_params.get("start_x", 50)
        start_y = self.settings.layout_params.get("start_y", 50)
        
        self.led_positions = []
        
        for y in range(height):
            for x in range(width):
                pos_x = start_x + x * spacing
                pos_y = start_y + y * spacing
                self.led_positions.append((pos_x, pos_y))
                
    def _generate_circle_layout(self):
        """
        Generate positions for a circular layout.
        """
        led_count = self.settings.layout_params.get("led_count", 100)
        radius = self.settings.layout_params.get("radius", 200)
        center_x = self.settings.layout_params.get("center_x", self.settings.width // 2)
        center_y = self.settings.layout_params.get("center_y", self.settings.height // 2)
        
        self.led_positions = []
        
        for i in range(led_count):
            angle = 2 * math.pi * i / led_count
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            self.led_positions.append((x, y))
            
    def _load_custom_layout(self):
        """
        Load a custom layout from settings.
        """
        positions = self.settings.layout_params.get("positions", [])
        self.led_positions = positions
        
    def _generate_clusters(self):
        """
        Generate LED clusters if clustering service is available.
        """
        if not self.clustering_service:
            return
            
        clusters = self.clustering_service.get_all_cluster_info()
        
        self.led_clusters = {}
        
        for cluster_id, cluster_info in clusters.items():
            led_indices = cluster_info.get("led_indices", [])
            for led_index in led_indices:
                if 0 <= led_index < len(self.led_positions):
                    self.led_clusters[led_index] = cluster_id
                    
    def update_led_colors(self):
        """
        Update LED colors from active effects.
        """
        with self.lock:
            effects = self.effect_manager.effects
            active_effect_ids = self.effect_manager.active_effect_ids
            
            self.led_colors = [[0, 0, 0] for _ in range(len(self.led_positions))]

            for effect_id in active_effect_ids:
                if effect_id not in effects:
                    continue
                    
                effect = effects[effect_id]
                led_count = min(effect.led_count, len(self.led_positions))
                
                effect_colors = effect.get_led_output()
                
                for i in range(led_count):
                    self.led_colors[i][0] = max(self.led_colors[i][0], effect_colors[i][0])
                    self.led_colors[i][1] = max(self.led_colors[i][1], effect_colors[i][1])
                    self.led_colors[i][2] = max(self.led_colors[i][2], effect_colors[i][2])
                
    def run(self):
        """
        Run the preview.
        """
        if self.running:
            return
            
        self.initialize()
        self.running = True
        
        try:
            while self.running:
                self._process_events()
                
                if not self.paused:
                    self._update()
                    
                self._render()
                
                self.clock.tick(self.settings.fps)
                
        except Exception as e:
            logger.error(f"Error in preview: {e}")
            
        finally:
            pygame.quit()
            self.screen = None
            self.running = False
            
    def _process_events(self):
        """
        Process pygame events.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._handle_key_event(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._handle_mouse_button_event(event)
            elif event.type == pygame.MOUSEMOTION:
                self.mouse_pos = event.pos
                
    def _handle_key_event(self, event):
        """
        Handle keyboard events.
        
        Args:
            event (pygame.event.Event): Keyboard event
        """
        if event.key == pygame.K_ESCAPE:
            self.running = False
        elif event.key == pygame.K_SPACE:
            self.paused = not self.paused
        elif event.key == pygame.K_s:
            self.settings.show_stats = not self.settings.show_stats
        elif event.key == pygame.K_l:
            self.settings.show_labels = not self.settings.show_labels
        elif event.key == pygame.K_c:
            self.settings.show_controls = not self.settings.show_controls
        elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
            self.settings.zoom *= 1.1
        elif event.key == pygame.K_MINUS:
            self.settings.zoom /= 1.1
        elif event.key == pygame.K_r:
            self.settings.zoom = 1.0
            self.settings.pan_x = 0
            self.settings.pan_y = 0
            
    def _handle_mouse_button_event(self, event):
        """
        Handle mouse button events.
        
        Args:
            event (pygame.event.Event): Mouse button event
        """
        if event.button == 1:  
            selected_led, distance = self._find_nearest_led(event.pos)
            
            if selected_led is not None and distance < 10:
                if selected_led in self.led_clusters:
                    self.selected_cluster = self.led_clusters[selected_led]
                else:
                    self.selected_cluster = None
                    
        elif event.button == 3:  
            pass
        elif event.button == 4: 
            self.settings.zoom *= 1.1
        elif event.button == 5:
            self.settings.zoom /= 1.1
            
    def _find_nearest_led(self, pos):
        """
        Find the nearest LED to a position.
        
        Args:
            pos (Tuple[int, int]): Position to check
            
        Returns:
            Tuple[int, float]: Index of nearest LED and distance, or (None, float('inf'))
        """
        if not self.led_positions:
            return None, float('inf')
            
        nearest_led = None
        min_distance = float('inf')
        
        for i, led_pos in enumerate(self.led_positions):
            x = led_pos[0] * self.settings.zoom + self.settings.pan_x
            y = led_pos[1] * self.settings.zoom + self.settings.pan_y
            
            dx = x - pos[0]
            dy = y - pos[1]
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance < min_distance:
                min_distance = distance
                nearest_led = i
                
        return nearest_led, min_distance
        
    def _update(self):
        """
        Update preview state.
        """
        self.effect_manager.update_all()
        
        self.update_led_colors()
        
        current_time = time.time()
        dt = current_time - self.last_frame_time
        self.last_frame_time = current_time
        
        self.render_times.append(dt * 1000)
        self.fps_history.append(self.clock.get_fps())
        
        if len(self.render_times) > 60:
            self.render_times.pop(0)
        if len(self.fps_history) > 60:
            self.fps_history.pop(0)
            
    def _render(self):
        """
        Render the preview.
        """
        self.screen.fill(self.settings.background_color)
        
        self._draw_leds()
        
        if self.settings.show_stats:
            self._draw_stats()
            
        if self.settings.show_controls:
            self._draw_controls()
            
        pygame.display.flip()
        
    def _draw_leds(self):
        """
        Draw all LEDs.
        """
        led_size = self.settings.led_size
        brightness = self.settings.brightness
        
        for i, (pos, color) in enumerate(zip(self.led_positions, self.led_colors)):
            x = pos[0] * self.settings.zoom + self.settings.pan_x
            y = pos[1] * self.settings.zoom + self.settings.pan_y
            
            scaled_color = [min(255, int(c * brightness)) for c in color]
            
            if self.selected_cluster is not None and i in self.led_clusters and self.led_clusters[i] == self.selected_cluster:
                pygame.draw.circle(self.screen, (255, 255, 255), (int(x), int(y)), led_size + 2)
                
            pygame.draw.circle(self.screen, scaled_color, (int(x), int(y)), led_size)
            
        if self.settings.show_labels:
            self._draw_labels()
            
    def _draw_labels(self):
        """
        Draw labels for LEDs and clusters.
        """
        drawn_clusters = set()
        
        for i, pos in enumerate(self.led_positions):
            x = pos[0] * self.settings.zoom + self.settings.pan_x
            y = pos[1] * self.settings.zoom + self.settings.pan_y
            
            if i % 10 == 0:
                label = self.font.render(str(i), True, (200, 200, 200))
                self.screen.blit(label, (int(x) + 10, int(y) - 10))
                
            if i in self.led_clusters:
                cluster_id = self.led_clusters[i]
                
                if cluster_id not in drawn_clusters:
                    label = self.font.render(f"C{cluster_id}", True, (200, 200, 100))
                    self.screen.blit(label, (int(x) + 10, int(y) + 10))
                    drawn_clusters.add(cluster_id)
                    
    def _draw_stats(self):
        """
        Draw performance statistics.
        """
        avg_fps = sum(self.fps_history) / max(1, len(self.fps_history))
        avg_render_time = sum(self.render_times) / max(1, len(self.render_times))
        max_render_time = max(self.render_times) if self.render_times else 0
        
        stats = [
            f"FPS: {avg_fps:.1f}",
            f"Render Time: {avg_render_time:.1f}ms (Max: {max_render_time:.1f}ms)",
            f"LEDs: {len(self.led_positions)}",
            f"Active Effects: {len(self.effect_manager.active_effect_ids)}",
            f"Zoom: {self.settings.zoom:.2f}",
            f"Selected Cluster: {self.selected_cluster}" if self.selected_cluster is not None else "No Cluster Selected"
        ]

        pygame.draw.rect(self.screen, (0, 0, 0, 128), (10, 10, 300, 150))

        for i, text in enumerate(stats):
            surface = self.font.render(text, True, (255, 255, 255))
            self.screen.blit(surface, (20, 20 + i * 24))
            
    def _draw_controls(self):
        """
        Draw control information.
        """
        controls = [
            "Controls:",
            "ESC: Quit",
            "Space: Pause/Resume",
            "S: Toggle Stats",
            "L: Toggle Labels",
            "C: Toggle Controls",
            "+/-: Zoom In/Out",
            "R: Reset View",
            "Mouse Wheel: Zoom",
            "Left Click: Select LED/Cluster"
        ]

        pygame.draw.rect(self.screen, (0, 0, 0, 128), (self.settings.width - 210, 10, 200, 24 * len(controls) + 10))

        for i, text in enumerate(controls):
            surface = self.font.render(text, True, (255, 255, 255))
            self.screen.blit(surface, (self.settings.width - 200, 20 + i * 24))
            
    def set_layout(self, layout_type: str, layout_params: Dict[str, Any]):
        """
        Set the LED layout.
        
        Args:
            layout_type (str): Type of layout ("linear", "grid", "circle", "custom")
            layout_params (Dict[str, Any]): Layout parameters
        """
        with self.lock:
            self.settings.layout_type = layout_type
            self.settings.layout_params = layout_params

            self._generate_layout()
            
    def set_effect_manager(self, effect_manager: EffectManager):
        """
        Set the effect manager.
        
        Args:
            effect_manager (EffectManager): New effect manager
        """
        with self.lock:
            self.effect_manager = effect_manager
            
    def set_clustering_service(self, clustering_service: ClusteringService):
        """
        Set the clustering service.
        
        Args:
            clustering_service (ClusteringService): New clustering service
        """
        with self.lock:
            self.clustering_service = clustering_service

            if self.led_positions:
                self._generate_clusters()
                
    def get_settings(self) -> PreviewSettings:
        """
        Get current preview settings.
        
        Returns:
            PreviewSettings: Current settings
        """
        return self.settings
        
    def update_settings(self, settings: Dict[str, Any]):
        """
        Update preview settings.
        
        Args:
            settings (Dict[str, Any]): New settings values
        """
        with self.lock:
            self.settings.update(settings)
            
    def set_selected_cluster(self, cluster_id: int):
        """
        Set the selected cluster.
        
        Args:
            cluster_id (int): Cluster ID
        """
        self.selected_cluster = cluster_id
        
    def set_selected_effect(self, effect_id: int):
        """
        Set the selected effect.
        
        Args:
            effect_id (int): Effect ID
        """
        self.selected_effect = effect_id