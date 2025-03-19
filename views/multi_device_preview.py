import pygame
import time
import math
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
import threading
import logging
import json
import os

from models.light_effect import LightEffect
from controllers.effect_manager import EffectManager
from services.clustering import ClusteringService
from controllers.device_manager import DeviceManager
from utils.color_utils import interpolate_color

logger = logging.getLogger(__name__)


class LayoutSettings:
    """
    Settings for LED layout in multi-device preview.
        """
    def __init__(self, effect_manager: EffectManager=None, device_manager: Optional[DeviceManager] = None,
                clustering_service: Optional[ClusteringService] = None):
        """
        Initialize the multi-device preview.
        
        Args:
            effect_manager (EffectManager): Effect manager
            device_manager (DeviceManager): Device manager
            clustering_service (ClusteringService): Clustering service
        """
        self.effect_manager = effect_manager
        self.device_manager = device_manager
        self.clustering_service = clustering_service
        
        # Khởi tạo settings
        self.layout_settings = LayoutSettings()
        self.width = 1200
        self.height = 800
        self.background_color = (20, 20, 30)
        self.fps = 60
        
        self.led_size = 5
        self.led_spacing = 0
        self.brightness = 1.0
        
        self.zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.show_labels = True
        self.show_stats = True
        self.show_controls = True
        self.show_grid = True
        self.grid_size = 20
        
        # Thông tin UI và xử lý tương tác
        self.screen = None
        self.font = None
        self.big_font = None
        self.clock = None
        self.running = False
        self.paused = False
        
        # Chuột và tương tác
        self.dragging = False
        self.drag_start = (0, 0)
        self.selected_device = None
        self.selected_segment = None
        self.selected_led = None
        self.edit_mode = False
        
        # Theo dõi hiệu suất
        self.fps_history = []
        self.render_times = []
        self.last_frame_time = 0
        

        self.device_positions = {}  
        self.segment_positions = {}
        self.led_colors = {} 
        
        self.tools = ["pan", "select", "add_device", "add_segment", "edit", "delete"]
        self.current_tool = "pan"
        self.tool_buttons = {}  
        
        self.panels = {
            "tools": pygame.Rect(10, 10, 50, 300),
            "properties": pygame.Rect(70, 10, 300, 300),  
            "devices": pygame.Rect(10, self.height - 210, 300, 200),  
            "effects": pygame.Rect(self.width - 310, 10, 300, 300)  
        }
        self.collapsed_panels = set()
        self.minimized_panels = set()  
        self.dragging_panel = None
        self.drag_offset = (0, 0)

        self.ui_buttons = {} 
        self.ui_dropdowns = {}  
        self.ui_sliders = {}  

        self.status_bar_height = 30
        self.status_text = ""
        
        self.lock = threading.RLock()

        def save_to_file(self, filename: str) -> bool:
            """
            Save layout settings to JSON file.
            
            Args:
                filename (str): Filename to save to
                
            Returns:
                bool: True if saved successfully
            """
            try:
                data = {
                    "devices": self.devices,
                    "segments": self.segments,
                    "layout_type": self.layout_type,
                    "layout_params": self.layout_params,
                    "background_color": self.background_color,
                    "grid_size": self.grid_size,
                    "show_grid": self.show_grid,
                    "show_labels": self.show_labels,
                    "show_device_boxes": self.show_device_boxes,
                    "show_segment_boxes": self.show_segment_boxes
                }
                
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                    
                logger.info(f"Saved layout to {filename}")
                return True
                
            except Exception as e:
                logger.error(f"Error saving layout: {e}")
                return False
                
        def load_from_file(self, filename: str) -> bool:
            """
            Load layout settings from JSON file.
            
            Args:
                filename (str): Filename to load from
                
            Returns:
                bool: True if loaded successfully
            """
            try:
                if not os.path.exists(filename):
                    logger.warning(f"Layout file not found: {filename}")
                    return False
                    
                with open(filename, 'r') as f:
                    data = json.load(f)
                    
                self.devices = data.get("devices", {})
                self.segments = data.get("segments", {})
                self.layout_type = data.get("layout_type", "custom")
                self.layout_params = data.get("layout_params", {})
                self.background_color = data.get("background_color", (20, 20, 30))
                self.grid_size = data.get("grid_size", 10)
                self.show_grid = data.get("show_grid", True)
                self.show_labels = data.get("show_labels", True)
                self.show_device_boxes = data.get("show_device_boxes", True)
                self.show_segment_boxes = data.get("show_segment_boxes", True)
                
                logger.info(f"Loaded layout from {filename}")
                return True
                
            except Exception as e:
                logger.error(f"Error loading layout: {e}")
                return False
                
        def add_device(self, device_id: str, name: str, led_count: int, position: Tuple[int, int] = (0, 0), 
                    rotation: float = 0.0, color: Tuple[int, int, int] = (200, 200, 200)) -> bool:
            """
            Add a device to the layout.
            
            Args:
                device_id (str): Device ID
                name (str): Device name
                led_count (int): Number of LEDs
                position (Tuple[int, int]): Device position (x, y)
                rotation (float): Rotation in degrees
                color (Tuple[int, int, int]): Device color
                
            Returns:
                bool: True if added successfully
            """
            if device_id in self.devices:
                logger.warning(f"Device {device_id} already exists in layout")
                return False
                
            self.devices[device_id] = {
                "name": name,
                "led_count": led_count,
                "position": position,
                "rotation": rotation,
                "color": color,
                "segments": []
            }
            
            logger.info(f"Added device {device_id} to layout")
            return True
            
        def add_segment(self, segment_id: str, device_id: str, start: int, end: int, 
                    position: Tuple[int, int] = None, rotation: float = None) -> bool:
            """
            Add a segment to the layout.
            
            Args:
                segment_id (str): Segment ID
                device_id (str): Device ID
                start (int): Start LED index
                end (int): End LED index
                position (Tuple[int, int]): Segment position (x, y)
                rotation (float): Rotation in degrees
                
            Returns:
                bool: True if added successfully
            """
            if segment_id in self.segments:
                logger.warning(f"Segment {segment_id} already exists in layout")
                return False
                
            if device_id not in self.devices:
                logger.warning(f"Device {device_id} not found in layout")
                return False
                
            if start < 0 or end >= self.devices[device_id]["led_count"] or start > end:
                logger.warning(f"Invalid segment range: {start}-{end}")
                return False
                
            # Sử dụng vị trí và góc của thiết bị nếu không được chỉ định
            if position is None:
                position = self.devices[device_id]["position"]
                
            if rotation is None:
                rotation = self.devices[device_id]["rotation"]
                
            self.segments[segment_id] = {
                "device_id": device_id,
                "start": start,
                "end": end,
                "position": position,
                "rotation": rotation
            }
            
            # Thêm segment vào danh sách segment của thiết bị
            self.devices[device_id]["segments"].append(segment_id)
            
            logger.info(f"Added segment {segment_id} to device {device_id}")
            return True
            
        def remove_device(self, device_id: str) -> bool:
            """
            Remove a device from the layout.
            
            Args:
                device_id (str): Device ID
                
            Returns:
                bool: True if removed successfully
            """
            if device_id not in self.devices:
                logger.warning(f"Device {device_id} not found in layout")
                return False
                
            # Xóa tất cả các segment thuộc thiết bị
            for segment_id in list(self.segments.keys()):
                if self.segments[segment_id]["device_id"] == device_id:
                    del self.segments[segment_id]
                    
            # Xóa thiết bị
            del self.devices[device_id]
            
            logger.info(f"Removed device {device_id} from layout")
            return True
            
        def remove_segment(self, segment_id: str) -> bool:
            """
            Remove a segment from the layout.
            
            Args:
                segment_id (str): Segment ID
                
            Returns:
                bool: True if removed successfully
            """
            if segment_id not in self.segments:
                logger.warning(f"Segment {segment_id} not found in layout")
                return False
                
            device_id = self.segments[segment_id]["device_id"]
            
            # Xóa segment khỏi danh sách segment của thiết bị
            if device_id in self.devices:
                if segment_id in self.devices[device_id]["segments"]:
                    self.devices[device_id]["segments"].remove(segment_id)
                    
            # Xóa segment
            del self.segments[segment_id]
            
            logger.info(f"Removed segment {segment_id} from layout")
            return True


class MultiDevicePreview:
    """
    Advanced preview for multiple devices with custom layouts.
    """
    
    def __init__(self, effect_manager: EffectManager, device_manager: Optional[DeviceManager] = None,
               clustering_service: Optional[ClusteringService] = None):
        """
        Initialize the multi-device preview.
        
        Args:
            effect_manager (EffectManager): Effect manager
            device_manager (DeviceManager): Device manager
            clustering_service (ClusteringService): Clustering service
        """
        self.effect_manager = effect_manager
        self.device_manager = device_manager
        self.clustering_service = clustering_service
        
        # Khởi tạo settings
        self.layout_settings = LayoutSettings()
        self.width = 1200
        self.height = 800
        self.background_color = (20, 20, 30)
        self.fps = 60
        
        self.led_size = 5
        self.led_spacing = 0
        self.brightness = 1.0
        
        self.zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.show_labels = True
        self.show_stats = True
        self.show_controls = True
        self.show_grid = True
        self.grid_size = 20
        
        # Thông tin UI và xử lý tương tác
        self.screen = None
        self.font = None
        self.big_font = None
        self.clock = None
        self.running = False
        self.paused = False
        
        # Chuột và tương tác
        self.dragging = False
        self.drag_start = (0, 0)
        self.selected_device = None
        self.selected_segment = None
        self.selected_led = None
        self.edit_mode = False
        
        # Theo dõi hiệu suất
        self.fps_history = []
        self.render_times = []
        self.last_frame_time = 0
        
        # Dữ liệu LED và segment
        self.device_positions = {}  # {device_id: [(x, y), ...]}
        self.segment_positions = {}  # {segment_id: [(x, y), ...]}
        self.led_colors = {}  # {device_id: [(r, g, b), ...]}
        
        # Các công cụ trong UI
        self.tools = ["pan", "select", "add_device", "add_segment", "edit", "delete"]
        self.current_tool = "pan"
        self.tool_buttons = {}  # {tool: rect}
        
        # Các panel UI
        self.panels = {
            "tools": pygame.Rect(10, 10, 50, 300),
            "properties": pygame.Rect(self.width - 310, 10, 300, 300),
            "devices": pygame.Rect(10, self.height - 210, 300, 200),
            "effects": pygame.Rect(self.width - 310, self.height - 210, 300, 200)
        }
        self.collapsed_panels = set()
        self.dragging_panel = None
        self.drag_offset = (0, 0)
        
        # Khóa thread
        self.lock = threading.RLock()
    
    def initialize(self):
        """
        Initialize the preview display.
        """
        if self.screen is not None:
            return
            
        pygame.init()
        pygame.display.set_caption("LED Multi-Device Preview")
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.big_font = pygame.font.Font(None, 36)
        
        # Khởi tạo vị trí công cụ
        tool_y = 20
        for tool in self.tools:
            self.tool_buttons[tool] = pygame.Rect(20, tool_y, 30, 30)
            tool_y += 40
        
        # Tạo layout mặc định nếu chưa có
        if not self.layout_settings.devices:
            self._create_default_layout()
            
        # Khởi tạo vị trí LED dựa trên layout
        self._generate_positions()
        
        logger.info(f"Initialized multi-device preview")
    
    def _create_default_layout(self):
        """
        Create a default layout with some devices and segments.
        """
        # Thêm một số thiết bị mẫu
        self.layout_settings.add_device("dev1", "ESP32-1", 150, (200, 200), 0, (255, 100, 100))
        self.layout_settings.add_device("dev2", "ESP32-2", 150, (400, 400), 90, (100, 255, 100))
        self.layout_settings.add_device("dev3", "ESP32-3", 150, (600, 200), 180, (100, 100, 255))
        
        # Thêm các segment cho từng thiết bị
        self.layout_settings.add_segment("seg1", "dev1", 0, 49, (200, 200), 0)
        self.layout_settings.add_segment("seg2", "dev1", 50, 99, (250, 200), 0)
        self.layout_settings.add_segment("seg3", "dev1", 100, 149, (300, 200), 0)
        
        self.layout_settings.add_segment("seg4", "dev2", 0, 49, (400, 400), 90)
        self.layout_settings.add_segment("seg5", "dev2", 50, 99, (400, 450), 90)
        self.layout_settings.add_segment("seg6", "dev2", 100, 149, (400, 500), 90)
        
        self.layout_settings.add_segment("seg7", "dev3", 0, 149, (600, 200), 180)
    
    def _generate_positions(self):
        """
        Generate LED positions based on layout settings.
        """
        with self.lock:
            self.device_positions = {}
            self.segment_positions = {}
            
            # Tính toán vị trí LED cho từng thiết bị
            for device_id, device_info in self.layout_settings.devices.items():
                led_count = device_info["led_count"]
                device_pos = device_info["position"]
                rotation = device_info["rotation"]
                
                # Tạo vị trí mặc định cho tất cả LED trong thiết bị
                positions = []
                
                for i in range(led_count):
                    # Đặt LED theo đường thẳng ngang
                    x = device_pos[0] + i * (self.led_size + self.led_spacing) * math.cos(math.radians(rotation))
                    y = device_pos[1] + i * (self.led_size + self.led_spacing) * math.sin(math.radians(rotation))
                    positions.append((x, y))
                    
                self.device_positions[device_id] = positions
                
                # Khởi tạo màu LED là đen
                self.led_colors[device_id] = [(0, 0, 0)] * led_count
                
            # Tạo vị trí LED cho từng segment
            for segment_id, segment_info in self.layout_settings.segments.items():
                device_id = segment_info["device_id"]
                start = segment_info["start"]
                end = segment_info["end"]
                
                if device_id in self.device_positions:
                    device_positions = self.device_positions[device_id]
                    if 0 <= start < end < len(device_positions):
                        self.segment_positions[segment_id] = device_positions[start:end+1]
    
    def update_led_colors(self):
        """
        Update LED colors from active effects.
        """
        with self.lock:
            # Thiết lập màu đen cho tất cả LED
            for device_id, positions in self.device_positions.items():
                self.led_colors[device_id] = [(0, 0, 0)] * len(positions)
                
            # Lấy màu từ các hiệu ứng đang hoạt động
            effects = self.effect_manager.effects
            active_effect_ids = self.effect_manager.active_effect_ids
            
            for effect_id in active_effect_ids:
                if effect_id not in effects:
                    continue
                    
                effect = effects[effect_id]
                
                # Áp dụng màu từ hiệu ứng cho các segment
                for segment_id, segment_info in self.layout_settings.segments.items():
                    device_id = segment_info["device_id"]
                    start = segment_info["start"]
                    end = segment_info["end"]
                    
                    if device_id not in self.led_colors:
                        continue
                        
                    # Lấy màu đầu ra của hiệu ứng
                    effect_colors = effect.get_led_output()
                    effect_led_count = len(effect_colors)
                    
                    if effect_led_count == 0:
                        continue
                    
                    # Map màu từ hiệu ứng vào segment
                    segment_length = end - start + 1
                    
                    for i in range(segment_length):
                        # Map index từ segment sang effect
                        effect_idx = min(int(i * effect_led_count / segment_length), effect_led_count - 1)
                        
                        if effect_idx < len(effect_colors):
                            # Kết hợp màu (lấy giá trị lớn nhất)
                            led_idx = start + i
                            if led_idx < len(self.led_colors[device_id]):
                                current_color = self.led_colors[device_id][led_idx]
                                effect_color = effect_colors[effect_idx]
                                
                                self.led_colors[device_id][led_idx] = (
                                    max(current_color[0], effect_color[0]),
                                    max(current_color[1], effect_color[1]),
                                    max(current_color[2], effect_color[2])
                                )
    
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
                
                self.clock.tick(self.fps)
                
        except Exception as e:
            logger.error(f"Error in preview: {e}", exc_info=True)
            
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
                
            elif event.type == pygame.VIDEORESIZE:
                self.width, self.height = event.size
                self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
                
                # Cập nhật vị trí panel
                self.panels["properties"] = pygame.Rect(70, 10, 300, 300)
                self.panels["devices"] = pygame.Rect(10, self.height - 210, 300, 200)
                self.panels["effects"] = pygame.Rect(self.width - 310, 10, 300, 300)
                
            elif event.type == pygame.KEYDOWN:
                self._handle_key_event(event)
                
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._handle_mouse_button_down(event)
                
            elif event.type == pygame.MOUSEBUTTONUP:
                self._handle_mouse_button_up(event)
                
            elif event.type == pygame.MOUSEMOTION:
                self._handle_mouse_motion(event)

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
        elif event.key == pygame.K_l:
            self.show_labels = not self.show_labels
        elif event.key == pygame.K_g:
            self.show_grid = not self.show_grid
        elif event.key == pygame.K_c:
            self.show_controls = not self.show_controls
        elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
            self.zoom *= 1.1
        elif event.key == pygame.K_MINUS:
            self.zoom /= 1.1
        elif event.key == pygame.K_r:
            self.zoom = 1.0
            self.pan_x = 0
            self.pan_y = 0
        elif event.key == pygame.K_p:
            self.current_tool = "pan"
        elif event.key == pygame.K_s:
            self.current_tool = "select"
        elif event.key == pygame.K_e:
            self.current_tool = "edit"
        elif event.key == pygame.K_d:
            self.current_tool = "delete"

    def _handle_mouse_button_down(self, event):
        """
        Handle mouse button down events.
        
        Args:
            event (pygame.event.Event): Mouse event
        """
        mouse_pos = event.pos
        
        # Kiểm tra xem có nhấp vào nút công cụ không
        for tool, rect in self.tool_buttons.items():
            if rect.collidepoint(mouse_pos):
                self.current_tool = tool
                return
        
        # Kiểm tra tương tác với UI controls (buttons, dropdowns, sliders)
        if self._handle_ui_controls(event):
            return
        
        # Kiểm tra xem có nhấp vào panel không
        for panel_id, panel_rect in self.panels.items():
            # Nếu panel bị thu nhỏ hoàn toàn, kiểm tra nút hiển thị
            if panel_id in self.minimized_panels:
                minimize_rect = pygame.Rect(panel_rect.x, panel_rect.y, 30, 25)
                if minimize_rect.collidepoint(mouse_pos):
                    self.minimized_panels.remove(panel_id)
                    return
                continue
            
            # Kiểm tra xem có nhấp vào thanh tiêu đề của panel
            header_rect = pygame.Rect(panel_rect.x, panel_rect.y, panel_rect.width, 25)
            if header_rect.collidepoint(mouse_pos):
                # Kiểm tra nút thu gọn
                collapse_rect = pygame.Rect(panel_rect.x + panel_rect.width - 50, panel_rect.y, 25, 25)
                if collapse_rect.collidepoint(mouse_pos):
                    if panel_id in self.collapsed_panels:
                        self.collapsed_panels.remove(panel_id)
                    else:
                        self.collapsed_panels.add(panel_id)
                    return
                
                # Kiểm tra nút thu nhỏ
                minimize_rect = pygame.Rect(panel_rect.x + panel_rect.width - 25, panel_rect.y, 25, 25)
                if minimize_rect.collidepoint(mouse_pos):
                    self.minimized_panels.add(panel_id)
                    return
                
                # Bắt đầu kéo panel
                self.dragging_panel = panel_id
                self.drag_offset = (mouse_pos[0] - panel_rect.x, mouse_pos[1] - panel_rect.y)
                return
        
        # Xử lý tương tác với không gian làm việc
        if event.button == 1:  # Chuột trái
            if self.current_tool == "pan":
                self.dragging = True
                self.drag_start = mouse_pos
            elif self.current_tool == "select":
                self._select_at_position(mouse_pos)
            elif self.current_tool == "add_device":
                self._add_device_at_position(mouse_pos)
            elif self.current_tool == "add_segment":
                self._add_segment_at_position(mouse_pos)
            elif self.current_tool == "delete":
                self._delete_at_position(mouse_pos)
                
        elif event.button == 3:  # Chuột phải
            # Hiển thị menu ngữ cảnh
            self._show_context_menu(mouse_pos)
            
        elif event.button == 4:  # Cuộn lên
            # Zoom in
            self.zoom *= 1.1
            self._update_zoom(mouse_pos)
            
        elif event.button == 5:  # Cuộn xuống
            # Zoom out
            self.zoom /= 1.1
            self._update_zoom(mouse_pos)

    def _handle_mouse_button_up(self, event):
        """
        Handle mouse button up events.
        
        Args:
            event (pygame.event.Event): Mouse event
        """
        # Xử lý UI controls trước
        if self._handle_ui_controls(event):
            return
            
        if event.button == 1:  # Chuột trái
            self.dragging = False
            self.dragging_panel = None

    def _handle_mouse_motion(self, event):
        """
        Handle mouse motion events.
        
        Args:
            event (pygame.event.Event): Mouse event
        """
        mouse_pos = event.pos
        mouse_rel = event.rel
        
        # Xử lý UI controls (hover states, dragging sliders)
        if self._handle_ui_controls(event):
            return
        
        if self.dragging_panel:
            # Kéo panel
            panel_rect = self.panels[self.dragging_panel]
            new_x = mouse_pos[0] - self.drag_offset[0]
            new_y = mouse_pos[1] - self.drag_offset[1]
            
            # Giới hạn trong cửa sổ
            new_x = max(0, min(self.width - panel_rect.width, new_x))
            new_y = max(0, min(self.height - panel_rect.height, new_y))
            
            panel_rect.x = new_x
            panel_rect.y = new_y
            
        elif self.dragging and self.current_tool == "pan":
            # Di chuyển khung nhìn
            self.pan_x += mouse_rel[0]
            self.pan_y += mouse_rel[1]
            
        elif self.current_tool == "edit" and self.selected_device:
            # Di chuyển thiết bị đã chọn
            device_info = self.layout_settings.devices[self.selected_device]
            device_info["position"] = (
                device_info["position"][0] + mouse_rel[0] / self.zoom,
                device_info["position"][1] + mouse_rel[1] / self.zoom
            )
            
            # Cập nhật vị trí LED
            self._generate_positions()
    def _handle_ui_controls(self, event):
        """
        Handle interaction with UI controls like buttons, dropdowns, sliders.
        
        Args:
            event (pygame.event.Event): Mouse event
            
        Returns:
            bool: True if event was handled
        """
        mouse_pos = event.pos
        
        # Xử lý click chuột
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Kiểm tra tương tác với các dropdown
            for dropdown_id, dropdown in self.ui_dropdowns.items():
                dropdown_rect = dropdown["rect"]
                
                # Kiểm tra click vào dropdown
                if dropdown_rect.collidepoint(mouse_pos):
                    dropdown["open"] = not dropdown["open"]
                    # Đóng tất cả dropdown khác
                    for other_id, other_dropdown in self.ui_dropdowns.items():
                        if other_id != dropdown_id:
                            other_dropdown["open"] = False
                    return True
                    
                # Nếu dropdown đang mở, kiểm tra click vào các option
                if dropdown["open"]:
                    option_height = dropdown_rect.height
                    options = dropdown["options"]
                    list_height = min(len(options) * option_height, 5 * option_height)
                    list_rect = pygame.Rect(dropdown_rect.x, dropdown_rect.bottom, dropdown_rect.width, list_height)
                    
                    if list_rect.collidepoint(mouse_pos):
                        # Tính option index dựa trên vị trí chuột
                        option_idx = int((mouse_pos[1] - list_rect.y) // option_height)
                        if 0 <= option_idx < len(options) and option_idx < 5:  # Giới hạn 5 options hiển thị
                            # Cập nhật option đã chọn
                            dropdown["selected_index"] = option_idx
                            dropdown["open"] = False
                            
                            # Nếu đây là dropdown hiệu ứng, cập nhật UI
                            if dropdown_id.startswith("effect_dropdown_"):
                                segment_id = dropdown_id.split("_")[-1]
                                self._update_selected_effect(segment_id, dropdown["selected_index"])
                                
                            return True
                    else:
                        # Click ngoài dropdown list nhưng dropdown đang mở
                        dropdown["open"] = False
                        return True
            
            # Kiểm tra tương tác với các nút
            for button_id, button in self.ui_buttons.items():
                button_rect = button["rect"]
                
                if button_rect.collidepoint(mouse_pos):
                    button["active"] = True
                    
                    # Nếu đây là nút áp dụng hiệu ứng
                    if button_id.startswith("apply_effect_"):
                        segment_id = button_id.split("_")[-1]
                        self._apply_effect_to_segment(segment_id)
                        
                    return True
            
            # Kiểm tra tương tác với các slider
            for slider_id, slider in self.ui_sliders.items():
                slider_rect = slider["rect"]
                
                # Tính vị trí handle của slider
                handle_pos = slider_rect.x + ((slider["value"] - slider["min_value"]) / 
                                            (slider["max_value"] - slider["min_value"])) * slider_rect.width
                handle_rect = pygame.Rect(handle_pos - 5, slider_rect.y - 5, 10, 20)
                
                if slider_rect.collidepoint(mouse_pos) or handle_rect.collidepoint(mouse_pos):
                    slider["dragging"] = True
                    # Cập nhật giá trị ngay lập tức
                    self._update_slider_value(slider_id, mouse_pos[0])
                    return True
        
        # Xử lý thả chuột
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            # Kiểm tra context menu
            if hasattr(self, 'context_menu') and self.context_menu:
                menu_rect = self.context_menu["rect"]
                options = self.context_menu["options"]
                
                if menu_rect.collidepoint(mouse_pos):
                    option_height = 25
                    option_idx = int((mouse_pos[1] - menu_rect.y - 5) // option_height)
                    
                    if 0 <= option_idx < len(options):
                        # Thực hiện callback của option
                        option_text, option_callback = options[option_idx]
                        option_callback()
                        
                        # Đóng menu
                        self.context_menu = None
                        return True
                else:
                    # Click ngoài menu
                    self.context_menu = None
            
            # Reset trạng thái active của các nút
            for button_id, button in self.ui_buttons.items():
                was_active = button["active"]
                button["active"] = False
                
                # Nếu nút vừa được click (was_active) và mouse vẫn trên nút khi thả
                if was_active and button["rect"].collidepoint(mouse_pos):
                    # Thực hiện callback của nút - đã xử lý ở phần MOUSEBUTTONDOWN
                    pass
                
            # Reset trạng thái dragging của các slider
            for slider_id, slider in self.ui_sliders.items():
                slider["dragging"] = False
        
        # Xử lý di chuyển chuột
        elif event.type == pygame.MOUSEMOTION:
            handled = False
            
            # Cập nhật hover trạng thái cho các nút
            for button_id, button in self.ui_buttons.items():
                old_hover = button.get("hover", False)
                new_hover = button["rect"].collidepoint(mouse_pos)
                
                if old_hover != new_hover:
                    button["hover"] = new_hover
                    handled = True
                
            # Cập nhật hover index cho các dropdown đang mở
            for dropdown_id, dropdown in self.ui_dropdowns.items():
                if dropdown["open"]:
                    dropdown_rect = dropdown["rect"]
                    option_height = dropdown_rect.height
                    options = dropdown["options"]
                    list_height = min(len(options) * option_height, 5 * option_height)
                    list_rect = pygame.Rect(dropdown_rect.x, dropdown_rect.bottom, dropdown_rect.width, list_height)
                    
                    old_hover_index = dropdown["hover_index"]
                    new_hover_index = -1
                    
                    if list_rect.collidepoint(mouse_pos):
                        option_idx = int((mouse_pos[1] - list_rect.y) // option_height)
                        if 0 <= option_idx < len(options) and option_idx < 5:
                            new_hover_index = option_idx
                    
                    if old_hover_index != new_hover_index:
                        dropdown["hover_index"] = new_hover_index
                        handled = True
            
            # Cập nhật giá trị cho slider đang được kéo
            for slider_id, slider in self.ui_sliders.items():
                if slider["dragging"]:
                    self._update_slider_value(slider_id, mouse_pos[0])
                    handled = True
            
            # Cập nhật hover index cho context menu
            if hasattr(self, 'context_menu') and self.context_menu:
                menu_rect = self.context_menu["rect"]
                
                old_hover_index = self.context_menu.get("hover_index", -1)
                new_hover_index = -1
                
                if menu_rect.collidepoint(mouse_pos):
                    option_height = 25
                    option_idx = int((mouse_pos[1] - menu_rect.y - 5) // option_height)
                    
                    if 0 <= option_idx < len(self.context_menu["options"]):
                        new_hover_index = option_idx
                
                if old_hover_index != new_hover_index:
                    self.context_menu["hover_index"] = new_hover_index
                    handled = True
                    
            return handled
            
        return False
        
    def _update_slider_value(self, slider_id, x_pos):
        """
        Update slider value based on x position.
        
        Args:
            slider_id (str): Slider ID
            x_pos (int): X position
        """
        slider = self.ui_sliders[slider_id]
        slider_rect = slider["rect"]
        
        # Giới hạn x_pos trong phạm vi slider
        x_pos = max(slider_rect.left, min(slider_rect.right, x_pos))
        
        # Tính giá trị mới
        pos_ratio = (x_pos - slider_rect.x) / slider_rect.width
        value = slider["min_value"] + pos_ratio * (slider["max_value"] - slider["min_value"])
        
        # Cập nhật giá trị
        slider["value"] = value
        
        # Nếu là slider tốc độ, áp dụng cho hiệu ứng đã chọn
        if slider_id.startswith("speed_slider_"):
            segment_id = slider_id.split("_")[-1]
            dropdown_id = f"effect_dropdown_{segment_id}"
            
            if dropdown_id in self.ui_dropdowns:
                dropdown = self.ui_dropdowns[dropdown_id]
                if dropdown["selected_index"] > 0:  # Nếu không phải "None"
                    effect_id = list(self.effect_manager.effects.keys())[dropdown["selected_index"] - 1]
                    if effect_id in self.effect_manager.effects:
                        effect = self.effect_manager.effects[effect_id]
                        # Cập nhật move_speed cho tất cả segment trong hiệu ứng
                        for segment in effect.segments.values():
                            segment.update_param("move_speed", value)
                            
                        # Cập nhật status text
                        self.status_text = f"Speed: {value:.1f} (Press Apply to save)"

    def _select_at_position(self, position):
        """
        Select device, segment, or LED at the given position.
        
        Args:
            position (Tuple[int, int]): Screen position
        """
        # Chuyển đổi vị trí màn hình sang vị trí thế giới
        world_pos = (
            (position[0] - self.pan_x) / self.zoom,
            (position[1] - self.pan_y) / self.zoom
        )
        
        # Tìm LED gần nhất
        min_distance = float('inf')
        nearest_device = None
        nearest_led_idx = None
        
        for device_id, led_positions in self.device_positions.items():
            for led_idx, led_pos in enumerate(led_positions):
                distance = math.sqrt((world_pos[0] - led_pos[0])**2 + (world_pos[1] - led_pos[1])**2)
                if distance < min_distance and distance < 10 / self.zoom:
                    min_distance = distance
                    nearest_device = device_id
                    nearest_led_idx = led_idx
        
        # Tìm segment chứa LED đã chọn
        nearest_segment = None
        if nearest_device and nearest_led_idx is not None:
            for segment_id, segment_info in self.layout_settings.segments.items():
                if segment_info["device_id"] == nearest_device:
                    if segment_info["start"] <= nearest_led_idx <= segment_info["end"]:
                        nearest_segment = segment_id
                        break
        
        # Cập nhật lựa chọn
        self.selected_device = nearest_device
        self.selected_segment = nearest_segment
        self.selected_led = nearest_led_idx
        
        logger.debug(f"Selected: Device={nearest_device}, Segment={nearest_segment}, LED={nearest_led_idx}")
    
    def _add_device_at_position(self, position):
        """
        Add a new device at the given position.
        
        Args:
            position (Tuple[int, int]): Screen position
        """
        # Chuyển đổi vị trí màn hình sang vị trí thế giới
        world_pos = (
            (position[0] - self.pan_x) / self.zoom,
            (position[1] - self.pan_y) / self.zoom
        )
        
        # Tạo ID thiết bị mới
        device_id = f"dev{len(self.layout_settings.devices) + 1}"
        
        # Tạo màu ngẫu nhiên cho thiết bị mới
        color = (
            np.random.randint(100, 255),
            np.random.randint(100, 255),
            np.random.randint(100, 255)
        )
        
        # Thêm thiết bị mới
        self.layout_settings.add_device(device_id, f"ESP32-{device_id}", 100, world_pos, 0, color)
        
        # Tạo segment mặc định
        segment_id = f"seg{len(self.layout_settings.segments) + 1}"
        self.layout_settings.add_segment(segment_id, device_id, 0, 99, world_pos, 0)
        
        # Cập nhật vị trí LED
        self._generate_positions()
        
        # Chọn thiết bị mới
        self.selected_device = device_id
        self.selected_segment = segment_id
        self.selected_led = None
        
        logger.info(f"Added device {device_id} at {world_pos}")
    
    def _add_segment_at_position(self, position):
        """
        Add a new segment to selected device at the given position.
        
        Args:
            position (Tuple[int, int]): Screen position
        """
        if not self.selected_device:
            logger.warning("No device selected")
            return
            
        # Chuyển đổi vị trí màn hình sang vị trí thế giới
        world_pos = (
            (position[0] - self.pan_x) / self.zoom,
            (position[1] - self.pan_y) / self.zoom
        )
        
        # Kiểm tra thiết bị đã chọn
        if self.selected_device not in self.layout_settings.devices:
            logger.warning(f"Selected device {self.selected_device} not found")
            return
            
        device_info = self.layout_settings.devices[self.selected_device]
        
        # Tìm vị trí LED cuối cùng đã sử dụng
        last_led = -1
        for segment_id, segment_info in self.layout_settings.segments.items():
            if segment_info["device_id"] == self.selected_device:
                last_led = max(last_led, segment_info["end"])
        
        # Kiểm tra xem còn LED nào chưa sử dụng không
        if last_led >= device_info["led_count"] - 1:
            logger.warning(f"No more LEDs available in device {self.selected_device}")
            return
            
        # Tính toán vị trí mới cho segment
        device_pos = device_info["position"]
        rotation = device_info["rotation"]
        start_led = last_led + 1
        end_led = min(start_led + 49, device_info["led_count"] - 1)
        
        # Tạo ID segment mới
        segment_id = f"seg{len(self.layout_settings.segments) + 1}"
        
        # Thêm segment mới
        self.layout_settings.add_segment(segment_id, self.selected_device, start_led, end_led, world_pos, rotation)
        
        # Cập nhật vị trí LED
        self._generate_positions()
        
        # Chọn segment mới
        self.selected_segment = segment_id
        
        logger.info(f"Added segment {segment_id} to device {self.selected_device} at {world_pos}")
    
    def _delete_at_position(self, position):
        """
        Delete device or segment at the given position.
        
        Args:
            position (Tuple[int, int]): Screen position
        """
        # Chọn đối tượng tại vị trí
        self._select_at_position(position)
        
        if self.selected_segment:
            # Xóa segment đã chọn
            self.layout_settings.remove_segment(self.selected_segment)
            logger.info(f"Deleted segment {self.selected_segment}")
            self.selected_segment = None
            
        elif self.selected_device:
            # Xóa thiết bị đã chọn
            self.layout_settings.remove_device(self.selected_device)
            logger.info(f"Deleted device {self.selected_device}")
            self.selected_device = None
            self.selected_led = None
            
        # Cập nhật vị trí LED
        self._generate_positions()
    
    def _update(self):
        """
        Update preview state.
        """
        # Cập nhật hiệu ứng
        self.effect_manager.update_all()
        
        # Cập nhật màu LED
        self.update_led_colors()
        
        # Tính toán hiệu suất
        current_time = time.time()
        dt = current_time - self.last_frame_time
        self.last_frame_time = current_time
        
        self.render_times.append(dt * 1000)
        self.fps_history.append(self.clock.get_fps())
        
        if len(self.render_times) > 60:
            self.render_times.pop(0)
        if len(self.fps_history) > 60:
            self.fps_history.pop(0)

    def _draw_context_menu(self):
        """
        Draw context menu if active.
        """
        if not hasattr(self, 'context_menu') or not self.context_menu:
            return
            
        menu_rect = self.context_menu["rect"]
        options = self.context_menu["options"]
        hover_index = self.context_menu.get("hover_index", -1)
        
        # Vẽ nền menu
        pygame.draw.rect(self.screen, (50, 50, 60), menu_rect)
        pygame.draw.rect(self.screen, (100, 100, 120), menu_rect, 1)
        
        # Vẽ các option
        option_height = 25
        for i, (option_text, _) in enumerate(options):
            option_rect = pygame.Rect(
                menu_rect.x, menu_rect.y + 5 + i * option_height, 
                menu_rect.width, option_height
            )
            
            # Highlight option khi hover
            if i == hover_index:
                pygame.draw.rect(self.screen, (70, 70, 90), option_rect)
            
            # Vẽ text
            text_surface = self.font.render(option_text, True, (220, 220, 220))
            self.screen.blit(text_surface, (option_rect.x + 10, option_rect.y + 5))

    def _render(self):
        """
        Render the preview.
        """
        self.screen.fill(self.background_color)
        
        # Vẽ lưới nếu được bật
        if self.show_grid:
            self._draw_grid()
            
        # Vẽ tất cả LED
        self._draw_leds()
        
        # Vẽ thanh công cụ
        self._draw_tools()
        
        # Vẽ các panel UI
        self._draw_panels()
        
        # Vẽ context menu nếu có
        self._draw_context_menu()
        
        # Vẽ thông tin trạng thái
        if self.show_stats:
            self._draw_stats()
        
        # Vẽ thanh trạng thái
        status_rect = pygame.Rect(0, self.height - self.status_bar_height, self.width, self.status_bar_height)
        pygame.draw.rect(self.screen, (40, 40, 50), status_rect)
        pygame.draw.line(self.screen, (100, 100, 120), (0, self.height - self.status_bar_height), 
                        (self.width, self.height - self.status_bar_height), 1)
        
        # Vẽ text trạng thái
        if self.status_text:
            status_surface = self.font.render(self.status_text, True, (220, 220, 220))
            self.screen.blit(status_surface, (10, self.height - self.status_bar_height + 5))
        
        # Vẽ hiện tại tool
        tool_text = f"Tool: {self.current_tool.replace('_', ' ').title()}"
        tool_surface = self.font.render(tool_text, True, (220, 220, 220))
        self.screen.blit(tool_surface, (self.width - tool_surface.get_width() - 10, 
                                    self.height - self.status_bar_height + 5))
                
        pygame.display.flip()

    def _draw_grid(self):
        """
        Draw grid lines.
        """
        # Tính toán khoảng cách lưới dựa trên zoom
        grid_spacing = self.grid_size * self.zoom
        
        # Tính toán lưới đầu tiên hiển thị
        start_x = self.pan_x % grid_spacing
        start_y = self.pan_y % grid_spacing
        
        # Vẽ các đường dọc
        for x in range(int(start_x), self.width + 1, int(grid_spacing)):
            pygame.draw.line(self.screen, (40, 40, 50), (x, 0), (x, self.height), 1)
            
        # Vẽ các đường ngang
        for y in range(int(start_y), self.height + 1, int(grid_spacing)):
            pygame.draw.line(self.screen, (40, 40, 50), (0, y), (self.width, y), 1)
            
    def _draw_leds(self):
        """
        Draw all LEDs based on layout.
        """
        # Vẽ tất cả LEDs dựa trên vị trí và màu sắc
        for device_id, positions in self.device_positions.items():
            colors = self.led_colors.get(device_id, [(0, 0, 0)] * len(positions))
            device_info = self.layout_settings.devices.get(device_id)
            
            if not device_info:
                continue
                
            # Vẽ đường kết nối giữa các LED
            screen_positions = []
            for pos in positions:
                screen_x = pos[0] * self.zoom + self.pan_x
                screen_y = pos[1] * self.zoom + self.pan_y
                screen_positions.append((screen_x, screen_y))
                
            if len(screen_positions) > 1:
                pygame.draw.lines(self.screen, (60, 60, 70), False, screen_positions, 1)
            
            # Vẽ hộp thiết bị nếu được bật
            if self.layout_settings.show_device_boxes:
                # Xác định hình chữ nhật bao quanh tất cả LED của thiết bị
                min_x = min(p[0] for p in screen_positions) - self.led_size
                min_y = min(p[1] for p in screen_positions) - self.led_size
                max_x = max(p[0] for p in screen_positions) + self.led_size
                max_y = max(p[1] for p in screen_positions) + self.led_size
                
                device_rect = pygame.Rect(min_x, min_y, max_x - min_x, max_y - min_y)
                device_color = device_info.get("color", (200, 200, 200))
                
                # Vẽ hộp thiết bị với màu nhạt
                border_color = (device_color[0] // 2, device_color[1] // 2, device_color[2] // 2)
                pygame.draw.rect(self.screen, border_color, device_rect, 1)
                
                # Vẽ nhãn thiết bị nếu được bật
                if self.layout_settings.show_labels:
                    device_name = device_info.get("name", f"Device {device_id}")
                    name_surface = self.font.render(device_name, True, device_color)
                    self.screen.blit(name_surface, (min_x, min_y - 25))
            
            # Vẽ từng segment
            for segment_id, segment_info in self.layout_settings.segments.items():
                if segment_info["device_id"] != device_id:
                    continue
                
                start = segment_info["start"]
                end = segment_info["end"]
                
                if start < 0 or end >= len(positions) or start > end:
                    continue
                
                # Lấy vị trí màn hình cho segment
                segment_positions = screen_positions[start:end+1]
                
                # Vẽ hộp segment nếu được bật
                if self.layout_settings.show_segment_boxes:
                    min_x = min(p[0] for p in segment_positions) - self.led_size
                    min_y = min(p[1] for p in segment_positions) - self.led_size
                    max_x = max(p[0] for p in segment_positions) + self.led_size
                    max_y = max(p[1] for p in segment_positions) + self.led_size
                    
                    segment_rect = pygame.Rect(min_x, min_y, max_x - min_x, max_y - min_y)
                    
                    # Highlight segment đã chọn
                    if segment_id == self.selected_segment:
                        pygame.draw.rect(self.screen, (100, 100, 200, 100), segment_rect)
                        pygame.draw.rect(self.screen, (100, 100, 200), segment_rect, 2)
                    else:
                        pygame.draw.rect(self.screen, (80, 80, 100), segment_rect, 1)
                    
                    # Vẽ nhãn segment nếu được bật
                    if self.layout_settings.show_labels:
                        segment_name = f"Segment {segment_id}"
                        name_surface = self.font.render(segment_name, True, (180, 180, 200))
                        self.screen.blit(name_surface, (min_x, max_y + 5))
            
            # Vẽ các LED
            for i, (pos, color) in enumerate(zip(positions, colors)):
                screen_x = pos[0] * self.zoom + self.pan_x
                screen_y = pos[1] * self.zoom + self.pan_y
                
                # Tính kích thước LED dựa trên zoom
                led_size = max(1, self.led_size * self.zoom)
                
                # Highlight LED đã chọn
                if device_id == self.selected_device and i == self.selected_led:
                    highlight_rect = pygame.Rect(
                        screen_x - led_size - 2, 
                        screen_y - led_size - 2,
                        led_size * 2 + 4,
                        led_size * 2 + 4
                    )
                    pygame.draw.rect(self.screen, (255, 255, 0), highlight_rect, 2)
                
                # Vẽ LED với màu thích hợp
                pygame.draw.circle(self.screen, color, (int(screen_x), int(screen_y)), int(led_size))
                
                # Vẽ số thứ tự LED nếu được bật và zoom đủ lớn
                if self.layout_settings.show_labels and self.zoom > 0.5 and i % 10 == 0:
                    led_label = self.font.render(str(i), True, (150, 150, 150))
                    self.screen.blit(led_label, (screen_x + led_size + 2, screen_y - 10))
    
    def _draw_tools(self):
        """
        Draw tools panel.
        """
        # Vẽ hộp công cụ
        tools_rect = self.panels["tools"]
        pygame.draw.rect(self.screen, (40, 40, 50), tools_rect)
        pygame.draw.rect(self.screen, (100, 100, 120), tools_rect, 1)
        
        # Vẽ tiêu đề
        title_surface = self.font.render("Tools", True, (220, 220, 220))
        self.screen.blit(title_surface, (tools_rect.x + 5, tools_rect.y + 5))
        
        # Vẽ các nút công cụ
        y_offset = tools_rect.y + 30
        for tool in self.tools:
            tool_rect = pygame.Rect(tools_rect.x + 10, y_offset, 30, 30)
            
            # Highlight công cụ hiện tại
            if tool == self.current_tool:
                pygame.draw.rect(self.screen, (100, 100, 150), tool_rect)
            else:
                pygame.draw.rect(self.screen, (60, 60, 80), tool_rect)
                
            pygame.draw.rect(self.screen, (100, 100, 120), tool_rect, 1)
            
            # Vẽ biểu tượng công cụ
            if tool == "pan":
                pygame.draw.line(self.screen, (220, 220, 220), 
                                (tool_rect.x + 5, tool_rect.y + 15),
                                (tool_rect.x + 25, tool_rect.y + 15), 2)
                pygame.draw.line(self.screen, (220, 220, 220), 
                                (tool_rect.x + 15, tool_rect.y + 5),
                                (tool_rect.x + 15, tool_rect.y + 25), 2)
            elif tool == "select":
                pygame.draw.polygon(self.screen, (220, 220, 220), [
                    (tool_rect.x + 5, tool_rect.y + 5),
                    (tool_rect.x + 15, tool_rect.y + 25),
                    (tool_rect.x + 25, tool_rect.y + 15)
                ])
            elif tool == "add_device":
                pygame.draw.rect(self.screen, (220, 220, 220), 
                                (tool_rect.x + 5, tool_rect.y + 5, 20, 20), 1)
                pygame.draw.line(self.screen, (220, 220, 220), 
                                (tool_rect.x + 15, tool_rect.y + 8),
                                (tool_rect.x + 15, tool_rect.y + 22), 2)
                pygame.draw.line(self.screen, (220, 220, 220), 
                                (tool_rect.x + 8, tool_rect.y + 15),
                                (tool_rect.x + 22, tool_rect.y + 15), 2)
            elif tool == "add_segment":
                pygame.draw.line(self.screen, (220, 220, 220), 
                                (tool_rect.x + 5, tool_rect.y + 15),
                                (tool_rect.x + 25, tool_rect.y + 15), 2)
                for i in range(5):
                    x = tool_rect.x + 5 + i * 5
                    pygame.draw.circle(self.screen, (220, 220, 220), (x, tool_rect.y + 15), 2)
            elif tool == "edit":
                pygame.draw.line(self.screen, (220, 220, 220), 
                                (tool_rect.x + 5, tool_rect.y + 25),
                                (tool_rect.x + 15, tool_rect.y + 5), 2)
                pygame.draw.line(self.screen, (220, 220, 220), 
                                (tool_rect.x + 15, tool_rect.y + 5),
                                (tool_rect.x + 25, tool_rect.y + 15), 2)
            elif tool == "delete":
                pygame.draw.line(self.screen, (220, 220, 220), 
                                (tool_rect.x + 5, tool_rect.y + 5),
                                (tool_rect.x + 25, tool_rect.y + 25), 2)
                pygame.draw.line(self.screen, (220, 220, 220), 
                                (tool_rect.x + 5, tool_rect.y + 25),
                                (tool_rect.x + 25, tool_rect.y + 5), 2)
            
            # Cập nhật vị trí nút công cụ
            self.tool_buttons[tool] = tool_rect
            
            # Vẽ text tooltip khi hover
            mouse_pos = pygame.mouse.get_pos()
            if tool_rect.collidepoint(mouse_pos):
                tooltip_text = tool.replace("_", " ").title()
                tooltip = self.font.render(tooltip_text, True, (220, 220, 220))
                tooltip_rect = tooltip.get_rect(midleft=(tool_rect.right + 5, tool_rect.centery))
                
                # Vẽ nền cho tooltip
                bg_rect = tooltip_rect.inflate(10, 5)
                pygame.draw.rect(self.screen, (40, 40, 50), bg_rect)
                pygame.draw.rect(self.screen, (100, 100, 120), bg_rect, 1)
                
                self.screen.blit(tooltip, tooltip_rect)
            
            y_offset += 40
    
    def _draw_panels(self):

        status_rect = pygame.Rect(0, self.height - self.status_bar_height, self.width, self.status_bar_height)
        pygame.draw.rect(self.screen, (40, 40, 50), status_rect)
        pygame.draw.line(self.screen, (100, 100, 120), (0, self.height - self.status_bar_height), 
                        (self.width, self.height - self.status_bar_height), 1)
        
        if self.status_text:
            status_surface = self.font.render(self.status_text, True, (220, 220, 220))
            self.screen.blit(status_surface, (10, self.height - self.status_bar_height + 5))
        
        for panel_id, panel_rect in self.panels.items():
            if panel_id == "tools":
                continue 

            if panel_id in self.minimized_panels:
                minimize_rect = pygame.Rect(panel_rect.x, panel_rect.y, 30, 25)
                pygame.draw.rect(self.screen, (60, 60, 80), minimize_rect)
                pygame.draw.rect(self.screen, (100, 100, 120), minimize_rect, 1)
                
                pygame.draw.line(self.screen, (220, 220, 220), 
                            (minimize_rect.centerx - 5, minimize_rect.centery),
                            (minimize_rect.centerx + 5, minimize_rect.centery), 2)
                pygame.draw.line(self.screen, (220, 220, 220), 
                            (minimize_rect.centerx, minimize_rect.centery - 5),
                            (minimize_rect.centerx, minimize_rect.centery + 5), 2)
                
                continue

            is_collapsed = panel_id in self.collapsed_panels

            header_rect = pygame.Rect(panel_rect.x, panel_rect.y, panel_rect.width, 25)
            pygame.draw.rect(self.screen, (60, 60, 80), header_rect)
            pygame.draw.rect(self.screen, (100, 100, 120), header_rect, 1)

            if panel_id == "properties":
                title = "Properties"
            elif panel_id == "devices":
                title = "Devices"
            elif panel_id == "effects":
                title = "Effects"
            else:
                title = panel_id.title()
                
            title_surface = self.font.render(title, True, (220, 220, 220))
            self.screen.blit(title_surface, (header_rect.x + 5, header_rect.y + 5))

            collapse_rect = pygame.Rect(header_rect.right - 50, header_rect.y, 25, 25)
            pygame.draw.rect(self.screen, (80, 80, 100), collapse_rect)
            
            if is_collapsed:
                pygame.draw.line(self.screen, (220, 220, 220), 
                            (collapse_rect.centerx - 5, collapse_rect.centery),
                            (collapse_rect.centerx + 5, collapse_rect.centery), 2)
                pygame.draw.line(self.screen, (220, 220, 220), 
                            (collapse_rect.centerx, collapse_rect.centery - 5),
                            (collapse_rect.centerx, collapse_rect.centery + 5), 2)
            else:
                pygame.draw.line(self.screen, (220, 220, 220), 
                            (collapse_rect.centerx - 5, collapse_rect.centery),
                            (collapse_rect.centerx + 5, collapse_rect.centery), 2)
                    
            minimize_rect = pygame.Rect(header_rect.right - 25, header_rect.y, 25, 25)
            pygame.draw.rect(self.screen, (80, 80, 100), minimize_rect)

            pygame.draw.rect(self.screen, (220, 220, 220), 
                        (minimize_rect.centerx - 4, minimize_rect.centery - 4, 8, 8), 1)

            if not is_collapsed:

                content_rect = pygame.Rect(panel_rect.x, panel_rect.y + 25, 
                                        panel_rect.width, panel_rect.height - 25)
                pygame.draw.rect(self.screen, (40, 40, 50, 200), content_rect)
                pygame.draw.rect(self.screen, (100, 100, 120), content_rect, 1)

                if panel_id == "properties":
                    self._draw_properties_panel(content_rect)
                elif panel_id == "devices":
                    self._draw_devices_panel(content_rect)
                elif panel_id == "effects":
                    self._draw_effects_panel(content_rect)
                    
    def _draw_properties_panel(self, rect):
        """
        Draw properties panel content with improved effect selection.
        
        Args:
            rect (pygame.Rect): Panel rectangle
        """
        y_offset = rect.y + 10
        button_height = 25
        spacing = 5
        
        # Hiển thị thông tin về đối tượng đã chọn
        if self.selected_device:
            device_info = self.layout_settings.devices.get(self.selected_device)
            if device_info:
                # Tiêu đề
                title = f"Device: {device_info.get('name', self.selected_device)}"
                title_surface = self.font.render(title, True, (220, 220, 220))
                self.screen.blit(title_surface, (rect.x + 10, y_offset))
                y_offset += 25
                
                # Thông tin thiết bị
                props = [
                    f"ID: {self.selected_device}",
                    f"LED Count: {device_info.get('led_count', 0)}",
                    f"Position: ({device_info.get('position', (0, 0))[0]:.1f}, {device_info.get('position', (0, 0))[1]:.1f})",
                    f"Rotation: {device_info.get('rotation', 0):.1f}°",
                    f"Segments: {len(device_info.get('segments', []))}",
                ]
                
                for prop in props:
                    prop_surface = self.font.render(prop, True, (200, 200, 200))
                    self.screen.blit(prop_surface, (rect.x + 20, y_offset))
                    y_offset += 20
                    
                y_offset += 10  # Thêm khoảng cách
            
        if self.selected_segment:
            segment_info = self.layout_settings.segments.get(self.selected_segment)
            if segment_info:
                # Tiêu đề
                title = f"Segment: {self.selected_segment}"
                title_surface = self.font.render(title, True, (220, 220, 220))
                self.screen.blit(title_surface, (rect.x + 10, y_offset))
                y_offset += 25
                
                # Thông tin segment
                props = [
                    f"Device: {segment_info.get('device_id', '')}",
                    f"Range: {segment_info.get('start', 0)} - {segment_info.get('end', 0)}",
                    f"Length: {segment_info.get('end', 0) - segment_info.get('start', 0) + 1} LEDs",
                    f"Position: ({segment_info.get('position', (0, 0))[0]:.1f}, {segment_info.get('position', (0, 0))[1]:.1f})",
                    f"Rotation: {segment_info.get('rotation', 0):.1f}°",
                ]
                
                for prop in props:
                    prop_surface = self.font.render(prop, True, (200, 200, 200))
                    self.screen.blit(prop_surface, (rect.x + 20, y_offset))
                    y_offset += 20
                
                y_offset += 10  # Thêm khoảng cách
                
                # --- Hiệu ứng hiện tại ---
                effect_title = self.font.render("Current Effect:", True, (220, 220, 220))
                self.screen.blit(effect_title, (rect.x + 10, y_offset))
                y_offset += 25
                
                # Lấy hiệu ứng hiện tại (nếu có)
                current_effect = None
                effect_name = "None"
                if self.device_manager and self.selected_segment in self.device_manager.segments:
                    segment = self.device_manager.segments[self.selected_segment]
                    if segment.effect_id is not None and segment.effect_id in self.effect_manager.effects:
                        current_effect = segment.effect_id
                        effect_name = f"Effect {current_effect}"
                
                # Hiển thị hiệu ứng hiện tại
                effect_rect = pygame.Rect(rect.x + 20, y_offset, rect.width - 40, button_height)
                pygame.draw.rect(self.screen, (60, 60, 80), effect_rect)
                pygame.draw.rect(self.screen, (100, 100, 120), effect_rect, 1)
                
                current_effect_text = self.font.render(effect_name, True, (200, 200, 200))
                self.screen.blit(current_effect_text, (effect_rect.x + 5, effect_rect.y + 5))
                
                y_offset += button_height + spacing
                
                # --- Dropdown chọn hiệu ứng mới ---
                dropdown_label = self.font.render("Select Effect:", True, (220, 220, 220))
                self.screen.blit(dropdown_label, (rect.x + 10, y_offset))
                y_offset += 20
                
                # Vẽ dropdown để chọn hiệu ứng
                dropdown_rect = pygame.Rect(rect.x + 20, y_offset, rect.width - 40, button_height)
                
                # Tạo key cho dropdown hiệu ứng nếu chưa có
                dropdown_key = f"effect_dropdown_{self.selected_segment}"
                if dropdown_key not in self.ui_dropdowns:
                    # Tạo danh sách hiệu ứng có sẵn
                    effect_options = ["None"] + [f"Effect {i}" for i in self.effect_manager.effects.keys()]
                    selected_idx = 0
                    if current_effect is not None:
                        if current_effect in self.effect_manager.effects:
                            selected_idx = list(self.effect_manager.effects.keys()).index(current_effect) + 1
                            
                    self.ui_dropdowns[dropdown_key] = {
                        "rect": dropdown_rect,
                        "options": effect_options,
                        "selected_index": selected_idx, 
                        "open": False,
                        "hover_index": -1
                    }
                
                # Lấy thông tin dropdown
                dropdown = self.ui_dropdowns[dropdown_key]
                dropdown["rect"] = dropdown_rect  # Cập nhật vị trí (có thể đã thay đổi do kéo panel)
                
                # Vẽ dropdown
                pygame.draw.rect(self.screen, (60, 60, 80), dropdown_rect)
                pygame.draw.rect(self.screen, (100, 100, 120), dropdown_rect, 1)
                
                selected_option = dropdown["options"][dropdown["selected_index"]]
                selected_text = self.font.render(selected_option, True, (200, 200, 200))
                self.screen.blit(selected_text, (dropdown_rect.x + 5, dropdown_rect.y + 5))
                
                # Vẽ mũi tên dropdown
                arrow_points = [
                    (dropdown_rect.right - 15, dropdown_rect.centery - 3),
                    (dropdown_rect.right - 5, dropdown_rect.centery - 3),
                    (dropdown_rect.right - 10, dropdown_rect.centery + 3)
                ]
                pygame.draw.polygon(self.screen, (200, 200, 200), arrow_points)
                
                # Nếu dropdown đang mở, hiển thị các tùy chọn
                if dropdown["open"]:
                    options = dropdown["options"]
                    option_height = button_height
                    
                    # Vẽ nền cho dropdown list
                    list_height = min(len(options) * option_height, 5 * option_height)
                    list_rect = pygame.Rect(dropdown_rect.x, dropdown_rect.bottom, dropdown_rect.width, list_height)
                    pygame.draw.rect(self.screen, (50, 50, 60), list_rect)
                    pygame.draw.rect(self.screen, (100, 100, 120), list_rect, 1)
                    
                    # Vẽ các tùy chọn
                    for i, option in enumerate(options[:5]):  # Giới hạn hiển thị 5 tùy chọn
                        option_rect = pygame.Rect(
                            list_rect.x, list_rect.y + i * option_height, 
                            list_rect.width, option_height
                        )
                        
                        if i == dropdown["hover_index"]:
                            pygame.draw.rect(self.screen, (70, 70, 90), option_rect)
                        
                        option_text = self.font.render(option, True, (200, 200, 200))
                        self.screen.blit(option_text, (option_rect.x + 5, option_rect.y + 5))
                
                y_offset += button_height + spacing
                
                # --- Nút Apply Effect ---
                apply_button_rect = pygame.Rect(rect.x + 20, y_offset, rect.width - 40, button_height)
                
                # Tạo key cho nút apply nếu chưa có
                apply_button_key = f"apply_effect_{self.selected_segment}"
                if apply_button_key not in self.ui_buttons:
                    self.ui_buttons[apply_button_key] = {
                        "rect": apply_button_rect,
                        "text": "Apply Effect",
                        "active": False,
                        "hover": False
                    }
                
                # Lấy thông tin nút
                button = self.ui_buttons[apply_button_key]
                button["rect"] = apply_button_rect  # Cập nhật vị trí
                
                # Vẽ nút Apply
                if button["active"]:
                    pygame.draw.rect(self.screen, (70, 130, 70), apply_button_rect)
                elif button["hover"]:
                    pygame.draw.rect(self.screen, (70, 110, 70), apply_button_rect)
                else:
                    pygame.draw.rect(self.screen, (60, 100, 60), apply_button_rect)
                    
                pygame.draw.rect(self.screen, (100, 150, 100), apply_button_rect, 1)
                
                apply_text = self.font.render(button["text"], True, (220, 220, 220))
                text_rect = apply_text.get_rect(center=apply_button_rect.center)
                self.screen.blit(apply_text, text_rect)
                
                y_offset += button_height + spacing
                
                # Thêm thông tin về các tham số hiệu ứng
                effect_id = None
                if dropdown["selected_index"] > 0:  # Nếu không phải "None"
                    effect_id = list(self.effect_manager.effects.keys())[dropdown["selected_index"] - 1]
                    
                if effect_id is not None and effect_id in self.effect_manager.effects:
                    effect = self.effect_manager.effects[effect_id]
                    
                    param_title = self.font.render("Effect Parameters:", True, (220, 220, 220))
                    self.screen.blit(param_title, (rect.x + 10, y_offset))
                    y_offset += 25
                    
                    # Hiển thị các tham số của hiệu ứng
                    if hasattr(effect, 'segments') and effect.segments:
                        segment = next(iter(effect.segments.values()))
                        
                        # Hiển thị slider để điều chỉnh tốc độ nếu có
                        if hasattr(segment, 'move_speed'):
                            speed_label = self.font.render(f"Speed: {segment.move_speed:.1f}", True, (200, 200, 200))
                            self.screen.blit(speed_label, (rect.x + 20, y_offset))
                            y_offset += 20
                            
                            speed_slider_rect = pygame.Rect(rect.x + 20, y_offset, rect.width - 40, 10)
                            speed_slider_key = f"speed_slider_{self.selected_segment}"
                            
                            if speed_slider_key not in self.ui_sliders:
                                self.ui_sliders[speed_slider_key] = {
                                    "rect": speed_slider_rect,
                                    "min_value": -50.0,
                                    "max_value": 50.0,
                                    "value": segment.move_speed,
                                    "dragging": False
                                }
                            
                            slider = self.ui_sliders[speed_slider_key]
                            slider["rect"] = speed_slider_rect  # Cập nhật vị trí
                            
                            # Vẽ slider
                            pygame.draw.rect(self.screen, (40, 40, 50), speed_slider_rect)
                            
                            # Tính vị trí handle
                            range_value = slider["max_value"] - slider["min_value"]
                            pos_ratio = (slider["value"] - slider["min_value"]) / range_value
                            handle_pos = speed_slider_rect.x + pos_ratio * speed_slider_rect.width
                            
                            # Vẽ bar đã điền
                            filled_rect = pygame.Rect(
                                speed_slider_rect.x, speed_slider_rect.y,
                                handle_pos - speed_slider_rect.x, speed_slider_rect.height
                            )
                            pygame.draw.rect(self.screen, (60, 100, 150), filled_rect)
                            
                            # Vẽ handle
                            handle_rect = pygame.Rect(handle_pos - 5, speed_slider_rect.y - 5, 10, 20)
                            pygame.draw.rect(self.screen, (100, 140, 200), handle_rect)
                            
                            y_offset += 25

    def _draw_devices_panel(self, rect):
        """
        Draw devices panel content.
        
        Args:
            rect (pygame.Rect): Panel rectangle
        """
        y_offset = rect.y + 10
        
        # Tiêu đề
        title = f"Devices: {len(self.layout_settings.devices)}"
        title_surface = self.font.render(title, True, (220, 220, 220))
        self.screen.blit(title_surface, (rect.x + 10, y_offset))
        y_offset += 25
        
        # Danh sách thiết bị
        for device_id, device_info in self.layout_settings.devices.items():
            device_rect = pygame.Rect(rect.x + 5, y_offset, rect.width - 10, 25)
            
            # Highlight thiết bị đã chọn
            if device_id == self.selected_device:
                pygame.draw.rect(self.screen, (80, 80, 120), device_rect)
            
            # Vẽ tên thiết bị
            device_name = device_info.get("name", f"Device {device_id}")
            device_color = device_info.get("color", (200, 200, 200))
            
            name_surface = self.font.render(device_name, True, device_color)
            self.screen.blit(name_surface, (device_rect.x + 5, device_rect.y + 5))
            
            # Vẽ thông tin LED
            led_count = device_info.get("led_count", 0)
            led_info = f"{led_count} LEDs"
            led_surface = self.font.render(led_info, True, (180, 180, 180))
            self.screen.blit(led_surface, (device_rect.right - led_surface.get_width() - 5, device_rect.y + 5))
            
            y_offset += 30
    
    def _draw_effects_panel(self, rect):
        """
        Draw effects panel content.
        
        Args:
            rect (pygame.Rect): Panel rectangle
        """
        y_offset = rect.y + 10
        
        # Tiêu đề
        effects = self.effect_manager.effects
        active_effects = self.effect_manager.active_effect_ids
        
        title = f"Effects: {len(active_effects)}/{len(effects)}"
        title_surface = self.font.render(title, True, (220, 220, 220))
        self.screen.blit(title_surface, (rect.x + 10, y_offset))
        y_offset += 25
        
        # Danh sách hiệu ứng
        for effect_id, effect in effects.items():
            effect_rect = pygame.Rect(rect.x + 5, y_offset, rect.width - 10, 25)
            
            # Vẽ nền
            if effect_id in active_effects:
                pygame.draw.rect(self.screen, (60, 80, 60), effect_rect)
            else:
                pygame.draw.rect(self.screen, (60, 60, 60), effect_rect)
            
            # Vẽ tên hiệu ứng
            effect_name = f"Effect {effect_id}"
            effect_surface = self.font.render(effect_name, True, (200, 200, 200))
            self.screen.blit(effect_surface, (effect_rect.x + 5, effect_rect.y + 5))
            
            # Vẽ thông tin hiệu ứng
            segments_count = len(effect.segments)
            segment_info = f"{segments_count} segments"
            segment_surface = self.font.render(segment_info, True, (180, 180, 180))
            self.screen.blit(segment_surface, (effect_rect.right - segment_surface.get_width() - 5, effect_rect.y + 5))
            
            y_offset += 30
    
    def _draw_stats(self):
        """
        Draw performance statistics.
        """
        if not self.fps_history:
            return
            
        avg_fps = sum(self.fps_history) / len(self.fps_history)
        current_fps = self.fps_history[-1]
        
        if self.render_times:
            avg_render_time = sum(self.render_times) / len(self.render_times)
            max_render_time = max(self.render_times)
        else:
            avg_render_time = 0
            max_render_time = 0
            
        # Chuẩn bị các thống kê
        stats = [
            f"FPS: {current_fps:.1f} ({avg_fps:.1f} avg)",
            f"Render: {avg_render_time:.1f}ms (Max: {max_render_time:.1f}ms)",
            f"Zoom: {self.zoom:.2f}x",
            f"Devices: {len(self.layout_settings.devices)}",
            f"Segments: {len(self.layout_settings.segments)}",
        ]
        
        # Vẽ nền
        stats_width = 200
        stats_height = len(stats) * 20 + 10
        stats_rect = pygame.Rect(5, 5, stats_width, stats_height)
        
        pygame.draw.rect(self.screen, (0, 0, 0, 128), stats_rect)
        
        # Vẽ các dòng thống kê
        for i, stat in enumerate(stats):
            stat_surface = self.font.render(stat, True, (220, 220, 220))
            self.screen.blit(stat_surface, (10, 10 + i * 20))
    
    def _draw_selection_info(self):
        """
        Draw information about the current selection.
        """
        # Thông tin được hiển thị trong panel Properties
        pass
    
    def save_layout(self, filename: str):
        """
        Save the current layout to a file.
        
        Args:
            filename (str): Filename to save to
        """
        self.layout_settings.save_to_file(filename)
        
    def load_layout(self, filename: str):
        """
        Load a layout from a file.
        
        Args:
            filename (str): Filename to load from
        """
        if self.layout_settings.load_from_file(filename):
            self._generate_positions()
            
    def set_device_manager(self, device_manager: DeviceManager):
        """
        Set the device manager.
        
        Args:
            device_manager (DeviceManager): Device manager
        """
        self.device_manager = device_manager
        
    def set_effect_manager(self, effect_manager: EffectManager):
        """
        Set the effect manager.
        
        Args:
            effect_manager (EffectManager): Effect manager
        """
        self.effect_manager = effect_manager