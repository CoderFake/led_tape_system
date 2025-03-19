import pygame
import time
import numpy as np
from typing import Dict, List, Any, Tuple, Optional

import config
from models.light_effect import LightEffect
from views.ui_controls import Button, Slider, ToggleButton, DropdownList, ControlPanel, create_control_panel


class LEDSimulator:
    """
    Simulator for LED tape light using Pygame.
    """
    
    def __init__(self, light_effects: Dict[int, LightEffect], width: int = None, height: int = None):
        """
        Initialize the simulator.
        
        Args:
            light_effects (Dict[int, LightEffect]): Dictionary of light effects by ID
            width (int): Window width (defaults to config)
            height (int): Window height (defaults to config)
        """
        pygame.init()
        pygame.display.set_caption(config.WINDOW_TITLE)

        self.width = width if width is not None else config.WINDOW_WIDTH
        self.height = height if height is not None else config.WINDOW_HEIGHT
        
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.light_effects = light_effects
        self.running = False
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)

        self.fps_history = []
        self.frame_times = []
        self.last_frame_time = time.time()
        
        self.selected_effect = next(iter(light_effects.keys())) if light_effects else None

        self.show_stats = True
        self.show_segment_boundaries = True
        self.show_controls = True
        self.paused = False

        self._create_ui_controls()
        
    def _create_ui_controls(self):
        """
        Create UI controls.
        """
        self.control_panels = []
        
        main_panel = ControlPanel((10, 10, 200, 180), "Main Controls")

        def toggle_pause():
            self.paused = not self.paused
            
        pause_button = ToggleButton(
            (20, 40, 180, 30),
            "Pause",
            lambda state: setattr(self, 'paused', state)
        )
        main_panel.add_control(pause_button)
        
        stats_button = ToggleButton(
            (20, 80, 180, 30),
            "Show Stats",
            lambda state: setattr(self, 'show_stats', state),
            self.show_stats
        )
        main_panel.add_control(stats_button)

        boundaries_button = ToggleButton(
            (20, 120, 180, 30),
            "Show Boundaries",
            lambda state: setattr(self, 'show_segment_boundaries', state),
            self.show_segment_boundaries
        )
        main_panel.add_control(boundaries_button)

        def set_fps(value):
            config.MAX_FPS = int(value)
            
        fps_slider = Slider(
            (20, 160, 180, 20),
            10, 120, config.MAX_FPS,
            set_fps,
            step=1,
            format_func=lambda v: f"FPS: {int(v)}"
        )
        main_panel.add_control(fps_slider)
        
        self.control_panels.append(main_panel)

        if self.selected_effect is not None:
            effect_panel = create_control_panel(
                self.width - 220, 10, 210, 350,
                self.light_effects, 
                self.selected_effect
            )
            self.control_panels.append(effect_panel)
        
    def run(self):
        """
        Run the simulator main loop.
        """
        self.running = True
        
        while self.running:
            current_time = time.time()
            dt = current_time - self.last_frame_time
            self.last_frame_time = current_time
            self.frame_times.append(dt)

            if len(self.frame_times) > 60:
                self.frame_times.pop(0)

            for event in pygame.event.get():
                handled = False
                if self.show_controls:
                    for panel in self.control_panels:
                        if panel.handle_event(event):
                            handled = True
                            break

                if not handled:
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.KEYDOWN:
                        self._handle_key_event(event)
                    elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                        self._handle_mouse_event(event)

            self.screen.fill((0, 0, 0))

            if not self.paused:
                for effect_id, effect in self.light_effects.items():
                    effect.update_all()

            self._draw_leds()
            
            if self.show_stats:
                self._draw_stats()

            if self.show_controls:
                for panel in self.control_panels:
                    panel.draw(self.screen)
            
            pygame.display.flip()

            self.clock.tick(config.MAX_FPS)
 
            self.fps_history.append(self.clock.get_fps())
            if len(self.fps_history) > 60:
                self.fps_history.pop(0)

        pygame.quit()
        
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
            self.show_stats = not self.show_stats
        elif event.key == pygame.K_b:
            self.show_segment_boundaries = not self.show_segment_boundaries
        elif event.key == pygame.K_c:
            self.show_controls = not self.show_controls
        elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
            effect_id = event.key - pygame.K_1 + 1
            if effect_id in self.light_effects:
                self.selected_effect = effect_id
                if self.show_controls:
                    if len(self.control_panels) > 1:
                        self.control_panels.pop()
                    effect_panel = create_control_panel(
                        self.width - 220, 10, 210, 350,
                        self.light_effects, self.selected_effect
                    )
                    self.control_panels.append(effect_panel)
        
    def _handle_mouse_event(self, event):
        """
        Handle mouse events.
        
        Args:
            event (pygame.event.Event): Mouse event
        """
        pass
    
    def _draw_leds(self):
        """
        Draw all LEDs based on current light effects.
        """
        for effect_id, effect in self.light_effects.items():
            led_colors = effect.get_led_output()

            if not led_colors:
                continue
   
            led_count = effect.led_count
            max_led_width = self.width / led_count
            led_width = min(config.LED_SIZE, max_led_width)
            led_spacing = config.LED_SPACING
            total_width = led_count * (led_width + led_spacing) - led_spacing
            
            start_x = (self.width - total_width) / 2

            num_effects = len(self.light_effects)
            effect_height = self.height / num_effects
            led_height = min(effect_height * 0.8, config.LED_SIZE)
            y_offset = effect_id * effect_height
            
            if self.selected_effect == effect_id:
                pygame.draw.rect(self.screen, (40, 40, 40), 
                                 (0, y_offset, self.width, effect_height))

            label = self.font.render(f"Effect {effect_id}", True, (200, 200, 200))
            self.screen.blit(label, (10, y_offset + 5))
  
            for i, color in enumerate(led_colors):
                x = start_x + i * (led_width + led_spacing)
                y = y_offset + (effect_height - led_height) / 2
                
                pygame.draw.rect(self.screen, color, (x, y, led_width, led_height))
                
                if self.show_segment_boundaries:
                    for segment in effect.segments.values():
                        positions, _ = segment.get_light_data()
                        for pos in positions:
                            if 0 <= pos < led_count:
                                boundary_x = start_x + pos * (led_width + led_spacing)
                                pygame.draw.line(self.screen, (255, 255, 0), 
                                                (boundary_x, y_offset), 
                                                (boundary_x, y_offset + effect_height), 1)
    
    def _draw_stats(self):
        """
        Draw performance statistics.
        """

        avg_fps = sum(self.fps_history) / max(1, len(self.fps_history))
        
        if self.frame_times:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times) * 1000  # ms
            max_frame_time = max(self.frame_times) * 1000  # ms
        else:
            avg_frame_time = 0
            max_frame_time = 0
            
        total_segments = sum(len(effect.segments) for effect in self.light_effects.values())
        
        pygame.draw.rect(self.screen, (0, 0, 0, 128), (self.width // 2 - 140, 10, 280, 90))
        
        stats = [
            f"FPS: {avg_fps:.1f} / {config.MAX_FPS}",
            f"Frame Time: {avg_frame_time:.1f}ms (Max: {max_frame_time:.1f}ms)",
            f"Effects: {len(self.light_effects)}, Segments: {total_segments}",
            f"LED Count: {sum(effect.led_count for effect in self.light_effects.values())}"
        ]
        
        for i, text in enumerate(stats):
            surface = self.font.render(text, True, (255, 255, 255))
            self.screen.blit(surface, (self.width // 2 - 130, 15 + i * 20))