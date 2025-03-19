import pygame
import time
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
import pygame_gui

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
        
        # Cài đặt responsive
        self.min_width = 800
        self.min_height = 600
        
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
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
        
        # Tạo GUI manager cho UI responsive
        self.gui_manager = pygame_gui.UIManager((self.width, self.height))
        
        # Tạo các panel có thể thu gọn 
        self.panels = {}
        self.dragging_panel = None
        self.drag_offset = (0, 0)
        
        self._create_ui_controls()
        self._create_responsive_panels()
        
    def _create_responsive_panels(self):
        """
        Tạo các panel UI có thể thu gọn và di chuyển
        """
        # Panel điều khiển chính
        self.panels['main'] = {
            'rect': pygame.Rect(10, 10, 250, 200),
            'collapsed': False,
            'title': 'Điều khiển chính',
            'controls': []
        }
        
        # Panel điều khiển hiệu ứng
        self.panels['effects'] = {
            'rect': pygame.Rect(self.width - 260, 10, 250, 350),
            'collapsed': False,
            'title': 'Hiệu ứng',
            'controls': []
        }
        
        # Panel quản lý thiết bị
        self.panels['devices'] = {
            'rect': pygame.Rect(10, self.height - 210, 250, 200),
            'collapsed': True,
            'title': 'Thiết bị',
            'controls': []
        }
        
        # Panel timeline
        self.panels['timeline'] = {
            'rect': pygame.Rect(self.width - 260, self.height - 160, 250, 150),
            'collapsed': True,
            'title': 'Timeline',
            'controls': []
        }
        
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
            
        # Thêm controls vào panels
        self.panels['main']['controls'] = [pause_button, stats_button, boundaries_button, fps_slider]
        
    def resize(self, new_width, new_height):
        """
        Xử lý sự kiện thay đổi kích thước cửa sổ.
        
        Args:
            new_width (int): Chiều rộng mới
            new_height (int): Chiều cao mới
        """
        self.width = max(self.min_width, new_width)
        self.height = max(self.min_height, new_height)
        
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        self.gui_manager.set_window_resolution((self.width, self.height))
        
        # Cập nhật vị trí của các panel
        if 'effects' in self.panels:
            self.panels['effects']['rect'].x = self.width - 260
            
        if 'devices' in self.panels:
            self.panels['devices']['rect'].y = self.height - 210
            
        if 'timeline' in self.panels:
            self.panels['timeline']['rect'].x = self.width - 260
            self.panels['timeline']['rect'].y = self.height - 160
        
    def run(self):
        """
        Run the simulator main loop.
        """
        self.running = True
        
        while self.running:
            time_delta = self.clock.tick(config.MAX_FPS) / 1000.0
            current_time = time.time()
            dt = current_time - self.last_frame_time
            self.last_frame_time = current_time
            self.frame_times.append(dt)

            if len(self.frame_times) > 60:
                self.frame_times.pop(0)

            for event in pygame.event.get():
                # Xử lý sự kiện UI manager
                self.gui_manager.process_events(event)
                
                # Xử lý thay đổi kích thước cửa sổ
                if event.type == pygame.VIDEORESIZE:
                    self.resize(event.w, event.h)
                
                # Xử lý các sự kiện khác
                handled = self._handle_panel_events(event)
                
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

            # Vẽ các panel UI responsive
            self._draw_responsive_panels()
            
            # Cập nhật và vẽ UI manager
            self.gui_manager.update(time_delta)
            self.gui_manager.draw_ui(self.screen)
            
            pygame.display.flip()
 
            self.fps_history.append(self.clock.get_fps())
            if len(self.fps_history) > 60:
                self.fps_history.pop(0)

        pygame.quit()
        
    def _handle_panel_events(self, event):
        """
        Xử lý sự kiện cho các panel có thể kéo thả.
        
        Args:
            event (pygame.event.Event): Sự kiện pygame
            
        Returns:
            bool: True nếu sự kiện đã được xử lý
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()
            
            # Kiểm tra xem đã click vào title bar của panel nào không
            for panel_id, panel in self.panels.items():
                title_rect = pygame.Rect(panel['rect'].x, panel['rect'].y, panel['rect'].width, 30)
                
                if title_rect.collidepoint(mouse_pos):
                    # Click vào nút collapse
                    collapse_rect = pygame.Rect(panel['rect'].x + panel['rect'].width - 30, panel['rect'].y, 30, 30)
                    if collapse_rect.collidepoint(mouse_pos):
                        panel['collapsed'] = not panel['collapsed']
                        return True
                    
                    # Bắt đầu kéo panel
                    self.dragging_panel = panel_id
                    self.drag_offset = (mouse_pos[0] - panel['rect'].x, mouse_pos[1] - panel['rect'].y)
                    return True
                    
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging_panel:
                self.dragging_panel = None
                return True
                
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging_panel:
                mouse_pos = pygame.mouse.get_pos()
                panel = self.panels[self.dragging_panel]
                
                # Cập nhật vị trí panel theo chuột
                new_x = mouse_pos[0] - self.drag_offset[0]
                new_y = mouse_pos[1] - self.drag_offset[1]
                
                # Giới hạn panel trong cửa sổ
                new_x = max(0, min(self.width - panel['rect'].width, new_x))
                new_y = max(0, min(self.height - panel['rect'].height, new_y))
                
                panel['rect'].x = new_x
                panel['rect'].y = new_y
                
                return True
                
        return False
        
    def _draw_responsive_panels(self):
        """
        Vẽ các panel UI responsive
        """
        for panel_id, panel in self.panels.items():
            rect = panel['rect']
            
            # Vẽ header của panel
            header_rect = pygame.Rect(rect.x, rect.y, rect.width, 30)
            pygame.draw.rect(self.screen, (60, 60, 80), header_rect)
            pygame.draw.rect(self.screen, (100, 100, 120), header_rect, 1)
            
            # Vẽ tiêu đề
            title_surface = self.font.render(panel['title'], True, (220, 220, 220))
            title_rect = title_surface.get_rect(midleft=(rect.x + 10, rect.y + 15))
            self.screen.blit(title_surface, title_rect)
            
            # Vẽ nút collapse
            collapse_rect = pygame.Rect(rect.x + rect.width - 30, rect.y, 30, 30)
            pygame.draw.rect(self.screen, (80, 80, 100), collapse_rect)
            
            if panel['collapsed']:
                # Vẽ dấu +
                pygame.draw.line(self.screen, (220, 220, 220), 
                                 (collapse_rect.centerx - 5, collapse_rect.centery),
                                 (collapse_rect.centerx + 5, collapse_rect.centery), 2)
                pygame.draw.line(self.screen, (220, 220, 220), 
                                 (collapse_rect.centerx, collapse_rect.centery - 5),
                                 (collapse_rect.centerx, collapse_rect.centery + 5), 2)
            else:
                # Vẽ dấu -
                pygame.draw.line(self.screen, (220, 220, 220), 
                                 (collapse_rect.centerx - 5, collapse_rect.centery),
                                 (collapse_rect.centerx + 5, collapse_rect.centery), 2)
                
                # Vẽ body của panel
                body_rect = pygame.Rect(rect.x, rect.y + 30, rect.width, rect.height - 30)
                pygame.draw.rect(self.screen, (40, 40, 50, 200), body_rect)
                pygame.draw.rect(self.screen, (100, 100, 120), body_rect, 1)
                
                # Vẽ các controls
                # Các controls có thể vẽ thông qua UIManager hoặc tự vẽ tại đây
        
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
            
            # Tính toán kích thước LED dựa trên kích thước cửa sổ 
            max_led_width = (self.width * 0.9) / led_count
            led_width = min(config.LED_SIZE, max_led_width)
            led_spacing = config.LED_SPACING
            total_width = led_count * (led_width + led_spacing) - led_spacing
            
            start_x = (self.width - total_width) / 2

            num_effects = len(self.light_effects)
            effect_height = (self.height * 0.7) / num_effects
            led_height = min(effect_height * 0.8, config.LED_SIZE)
            y_offset = effect_id * effect_height + (self.height * 0.15)
            
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
        
        # Vẽ thống kê trên màn hình với vị trí responsive
        stats_x = self.width // 2 - 140
        stats_y = 10
        
        pygame.draw.rect(self.screen, (0, 0, 0, 128), (stats_x, stats_y, 280, 90))
        
        stats = [
            f"FPS: {avg_fps:.1f} / {config.MAX_FPS}",
            f"Frame Time: {avg_frame_time:.1f}ms (Max: {max_frame_time:.1f}ms)",
            f"Effects: {len(self.light_effects)}, Segments: {total_segments}",
            f"LED Count: {sum(effect.led_count for effect in self.light_effects.values())}"
        ]
        
        for i, text in enumerate(stats):
            surface = self.font.render(text, True, (255, 255, 255))
            self.screen.blit(surface, (stats_x + 10, stats_y + 5 + i * 20))