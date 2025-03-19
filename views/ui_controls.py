import pygame
from typing import List, Dict, Tuple, Any, Callable, Optional
import logging

from models.light_effect import LightEffect

logger = logging.getLogger(__name__)

BUTTON_COLORS = {
    "normal": (60, 60, 80),
    "hover": (80, 80, 100),
    "active": (100, 100, 140),
    "disabled": (40, 40, 50)
}

SLIDER_COLORS = {
    "track": (40, 40, 50),
    "handle": (100, 100, 160),
    "handle_hover": (120, 120, 180),
    "handle_active": (140, 140, 200),
    "disabled": (30, 30, 40)
}

TEXT_COLORS = {
    "normal": (220, 220, 220),
    "disabled": (150, 150, 150),
    "highlight": (255, 255, 255)
}


class Button:
    """
    A clickable button with configurable appearance and behavior.
    """
    
    def __init__(self, rect: Tuple[int, int, int, int], text: str, 
                 callback: Callable[[], None], disabled: bool = False):
        """
        Initialize a button.
        
        Args:
            rect (Tuple[int, int, int, int]): Button rectangle (x, y, width, height)
            text (str): Button text
            callback (Callable): Function to call when clicked
            disabled (bool): Whether the button is disabled
        """
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.disabled = disabled
        self.state = "normal" 
        self.font = pygame.font.Font(None, 24)

        
    def draw(self, surface: pygame.Surface):
        """
        Draw the button on a surface.
        
        Args:
            surface (pygame.Surface): Surface to draw on
        """
        if self.disabled:
            bg_color = BUTTON_COLORS["disabled"]
            text_color = TEXT_COLORS["disabled"]
        else:
            bg_color = BUTTON_COLORS[self.state]
            text_color = TEXT_COLORS["normal"]

        pygame.draw.rect(surface, bg_color, self.rect, border_radius=5)
        
        pygame.draw.rect(surface, (100, 100, 120), self.rect, width=1, border_radius=5)
        
        text_surface = self.font.render(self.text, True, text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)
        
    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle a pygame event.
        
        Args:
            event (pygame.event.Event): Event to handle
            
        Returns:
            bool: True if event was handled
        """
        if self.disabled:
            return False
            
        if event.type == pygame.MOUSEMOTION:
            if self.rect.collidepoint(event.pos):
                if self.state != "active":
                    self.state = "hover"
            else:
                if self.state != "active":
                    self.state = "normal"
                    
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.rect.collidepoint(event.pos):
                self.state = "active"
                return True
                
        elif event.type == pygame.MOUSEBUTTONUP:
            was_active = self.state == "active"
            self.state = "hover" if self.rect.collidepoint(event.pos) else "normal"
            
            if was_active and self.rect.collidepoint(event.pos):
                try:
                    self.callback()
                except Exception as e:
                    logger.error(f"Error in button callback: {e}")
                return True
                
        return False
        
    def set_disabled(self, disabled: bool):
        """
        Set whether the button is disabled.
        
        Args:
            disabled (bool): Whether the button is disabled
        """
        self.disabled = disabled
        if disabled:
            self.state = "normal"


class Slider:
    """
    A draggable slider for adjusting numeric values.
    """
    
    def __init__(self, rect: Tuple[int, int, int, int], min_value: float, max_value: float,
                 initial_value: float, callback: Callable[[float], None], 
                 disabled: bool = False, step: float = None, format_func: Callable[[float], str] = None):
        """
        Initialize a slider.
        
        Args:
            rect (Tuple[int, int, int, int]): Slider rectangle (x, y, width, height)
            min_value (float): Minimum value
            max_value (float): Maximum value
            initial_value (float): Initial value
            callback (Callable): Function to call when value changes
            disabled (bool): Whether the slider is disabled
            step (float): Step size (or None for continuous)
            format_func (Callable): Function to format value as string
        """
        self.rect = pygame.Rect(rect)
        self.min_value = min_value
        self.max_value = max_value
        self.value = min(max(initial_value, min_value), max_value)
        self.callback = callback
        self.disabled = disabled
        self.step = step
        self.format_func = format_func or (lambda v: f"{v:.1f}")
        self.dragging = False
        self.hover = False
        self.font = pygame.font.Font(None, 20)
        
    def draw(self, surface: pygame.Surface):
        """
        Draw the slider on a surface.
        
        Args:
            surface (pygame.Surface): Surface to draw on
        """
        track_rect = pygame.Rect(self.rect.x, self.rect.y + self.rect.height // 2 - 2,
                               self.rect.width, 4)
        
        position_ratio = (self.value - self.min_value) / (self.max_value - self.min_value)
        handle_pos = self.rect.x + int(position_ratio * self.rect.width)
        handle_rect = pygame.Rect(handle_pos - 6, self.rect.y, 12, self.rect.height)
        
        if self.disabled:
            track_color = SLIDER_COLORS["disabled"]
            handle_color = SLIDER_COLORS["disabled"]
            text_color = TEXT_COLORS["disabled"]
        else:
            track_color = SLIDER_COLORS["track"]
            if self.dragging:
                handle_color = SLIDER_COLORS["handle_active"]
            elif self.hover:
                handle_color = SLIDER_COLORS["handle_hover"]
            else:
                handle_color = SLIDER_COLORS["handle"]
            text_color = TEXT_COLORS["normal"]
            
        pygame.draw.rect(surface, track_color, track_rect, border_radius=2)
        
        filled_rect = pygame.Rect(track_rect.x, track_rect.y, 
                                handle_pos - track_rect.x, track_rect.height)
        pygame.draw.rect(surface, handle_color, filled_rect, border_radius=2)
        
        pygame.draw.rect(surface, handle_color, handle_rect, border_radius=4)
        
        value_text = self.format_func(self.value)
        text_surface = self.font.render(value_text, True, text_color)
        text_rect = text_surface.get_rect(midtop=(self.rect.centerx, self.rect.bottom + 2))
        surface.blit(text_surface, text_rect)
        
    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle a pygame event.
        
        Args:
            event (pygame.event.Event): Event to handle
            
        Returns:
            bool: True if event was handled
        """
        if self.disabled:
            return False
            
        position_ratio = (self.value - self.min_value) / (self.max_value - self.min_value)
        handle_pos = self.rect.x + int(position_ratio * self.rect.width)
        handle_rect = pygame.Rect(handle_pos - 6, self.rect.y, 12, self.rect.height)
        
        if event.type == pygame.MOUSEMOTION:
            self.hover = handle_rect.collidepoint(event.pos) or self.rect.collidepoint(event.pos)
            
            if self.dragging:
                self._update_value_from_pos(event.pos[0])
                return True
                
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if handle_rect.collidepoint(event.pos):
                self.dragging = True
                return True
            elif self.rect.collidepoint(event.pos):
                self._update_value_from_pos(event.pos[0])
                self.dragging = True
                return True
                
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False
                return True
                
        return False
        
    def _update_value_from_pos(self, x_pos: int):
        """
        Update value based on x position.
        
        Args:
            x_pos (int): X coordinate
        """
        x_pos = max(self.rect.left, min(self.rect.right, x_pos))
        position_ratio = (x_pos - self.rect.left) / self.rect.width
        
        new_value = self.min_value + position_ratio * (self.max_value - self.min_value)
        
        if self.step is not None:
            new_value = round(new_value / self.step) * self.step
            
        new_value = max(self.min_value, min(self.max_value, new_value))
        
        if new_value != self.value:
            self.value = new_value
            try:
                self.callback(self.value)
            except Exception as e:
                logger.error(f"Error in slider callback: {e}")
                
    def set_value(self, value: float, trigger_callback: bool = True):
        """
        Set the slider value.
        
        Args:
            value (float): New value
            trigger_callback (bool): Whether to trigger the callback
        """
        value = max(self.min_value, min(self.max_value, value))
        
        if self.step is not None:
            value = round(value / self.step) * self.step
            
        if value != self.value:
            self.value = value
            if trigger_callback:
                try:
                    self.callback(self.value)
                except Exception as e:
                    logger.error(f"Error in slider callback: {e}")
                    
    def set_disabled(self, disabled: bool):
        """
        Set whether the slider is disabled.
        
        Args:
            disabled (bool): Whether the slider is disabled
        """
        self.disabled = disabled
        if disabled:
            self.dragging = False
            self.hover = False


class ToggleButton(Button):
    """
    A button that toggles between on and off states.
    """
    
    def __init__(self, rect: Tuple[int, int, int, int], text: str, 
                 callback: Callable[[bool], None], initial_state: bool = False,
                 disabled: bool = False):
        """
        Initialize a toggle button.
        
        Args:
            rect (Tuple[int, int, int, int]): Button rectangle (x, y, width, height)
            text (str): Button text
            callback (Callable): Function to call when toggled
            initial_state (bool): Initial state (True for on, False for off)
            disabled (bool): Whether the button is disabled
        """
        super().__init__(rect, text, lambda: None, disabled)
        self.toggle_state = initial_state
        self.toggle_callback = callback
        
    def draw(self, surface: pygame.Surface):
        """
        Draw the toggle button on a surface.
        
        Args:
            surface (pygame.Surface): Surface to draw on
        """
        # Determine colors based on state and disabled
        if self.disabled:
            bg_color = BUTTON_COLORS["disabled"]
            text_color = TEXT_COLORS["disabled"]
        else:
            if self.toggle_state:
                bg_color = BUTTON_COLORS["active"]
            else:
                bg_color = BUTTON_COLORS[self.state]
            text_color = TEXT_COLORS["normal"]
            
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=5)
        
        border_color = (100, 200, 100) if self.toggle_state else (100, 100, 120)
        pygame.draw.rect(surface, border_color, self.rect, width=2, border_radius=5)
        
        text_surface = self.font.render(self.text, True, text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)
        
    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle a pygame event.
        
        Args:
            event (pygame.event.Event): Event to handle
            
        Returns:
            bool: True if event was handled
        """
        if self.disabled:
            return False
            
        if event.type == pygame.MOUSEMOTION:
            if self.rect.collidepoint(event.pos):
                if self.state != "active":
                    self.state = "hover"
            else:
                if self.state != "active":
                    self.state = "normal"
                    
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.rect.collidepoint(event.pos):
                self.state = "active"
                return True
                
        elif event.type == pygame.MOUSEBUTTONUP:
            was_active = self.state == "active"
            self.state = "hover" if self.rect.collidepoint(event.pos) else "normal"
            
            if was_active and self.rect.collidepoint(event.pos):
                self.toggle_state = not self.toggle_state
                try:
                    self.toggle_callback(self.toggle_state)
                except Exception as e:
                    logger.error(f"Error in toggle button callback: {e}")
                return True
                
        return False
        
    def set_state(self, state: bool, trigger_callback: bool = True):
        """
        Set the toggle state.
        
        Args:
            state (bool): New state
            trigger_callback (bool): Whether to trigger the callback
        """
        if state != self.toggle_state:
            self.toggle_state = state
            if trigger_callback:
                try:
                    self.toggle_callback(self.toggle_state)
                except Exception as e:
                    logger.error(f"Error in toggle button callback: {e}")


class DropdownList:
    """
    A dropdown list for selecting from multiple options.
    """
    
    def __init__(self, rect: Tuple[int, int, int, int], options: List[str], 
                 callback: Callable[[str], None], initial_index: int = 0,
                 disabled: bool = False):
        """
        Initialize a dropdown list.
        
        Args:
            rect (Tuple[int, int, int, int]): Dropdown rectangle (x, y, width, height)
            options (List[str]): List of options
            callback (Callable): Function to call when selection changes
            initial_index (int): Initial selected index
            disabled (bool): Whether the dropdown is disabled
        """
        self.rect = pygame.Rect(rect)
        self.options = options
        self.callback = callback
        self.selected_index = min(max(0, initial_index), len(options) - 1) if options else -1
        self.disabled = disabled
        self.open = False
        self.hover_index = -1
        self.font = pygame.font.Font(None, 24)
        
        self.option_height = self.rect.height
        self.dropdown_rect = pygame.Rect(
            self.rect.x, self.rect.y + self.rect.height,
            self.rect.width, self.option_height * min(len(options), 5)
        )
        
    def draw(self, surface: pygame.Surface):
        """
        Draw the dropdown list on a surface.
        
        Args:
            surface (pygame.Surface): Surface to draw on
        """
        if self.disabled:
            bg_color = BUTTON_COLORS["disabled"]
            text_color = TEXT_COLORS["disabled"]
        else:
            bg_color = BUTTON_COLORS["normal"]
            text_color = TEXT_COLORS["normal"]
            
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=5)
        pygame.draw.rect(surface, (100, 100, 120), self.rect, width=1, border_radius=5)
        
        if 0 <= self.selected_index < len(self.options):
            text = self.options[self.selected_index]
            text_surface = self.font.render(text, True, text_color)
            text_rect = text_surface.get_rect(midleft=(self.rect.x + 10, self.rect.centery))
            surface.blit(text_surface, text_rect)
            
        arrow_points = [
            (self.rect.right - 15, self.rect.centery - 3),
            (self.rect.right - 5, self.rect.centery - 3),
            (self.rect.right - 10, self.rect.centery + 3)
        ]
        pygame.draw.polygon(surface, text_color, arrow_points)
        
        if self.open and not self.disabled:
            pygame.draw.rect(surface, (50, 50, 60), self.dropdown_rect, border_radius=5)
            pygame.draw.rect(surface, (100, 100, 120), self.dropdown_rect, width=1, border_radius=5)
            
            visible_options = min(len(self.options), 5)
            for i in range(visible_options):
                option_rect = pygame.Rect(
                    self.dropdown_rect.x, self.dropdown_rect.y + i * self.option_height,
                    self.dropdown_rect.width, self.option_height
                )

                if i == self.hover_index:
                    pygame.draw.rect(surface, BUTTON_COLORS["hover"], option_rect)
                
                text_surface = self.font.render(self.options[i], True, TEXT_COLORS["normal"])
                text_rect = text_surface.get_rect(midleft=(option_rect.x + 10, option_rect.centery))
                surface.blit(text_surface, text_rect)
                
    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle a pygame event.
        
        Args:
            event (pygame.event.Event): Event to handle
            
        Returns:
            bool: True if event was handled
        """
        if self.disabled:
            return False
            
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.open = not self.open
                return True
                
            elif self.open and self.dropdown_rect.collidepoint(event.pos):
                rel_y = event.pos[1] - self.dropdown_rect.y
                option_index = rel_y // self.option_height
                
                if 0 <= option_index < len(self.options):
                    self.selected_index = option_index
                    self.open = False
                    try:
                        self.callback(self.options[self.selected_index])
                    except Exception as e:
                        logger.error(f"Error in dropdown callback: {e}")
                    return True
                    
            elif self.open:
                self.open = False
                return True
                
        elif event.type == pygame.MOUSEMOTION and self.open:
            if self.dropdown_rect.collidepoint(event.pos):
                rel_y = event.pos[1] - self.dropdown_rect.y
                self.hover_index = rel_y // self.option_height
                if self.hover_index >= len(self.options):
                    self.hover_index = -1
            else:
                self.hover_index = -1
                
        return False
        
    def set_selected(self, index: int, trigger_callback: bool = True):
        """
        Set the selected index.
        
        Args:
            index (int): Index to select
            trigger_callback (bool): Whether to trigger the callback
        """
        if 0 <= index < len(self.options) and index != self.selected_index:
            self.selected_index = index
            if trigger_callback:
                try:
                    self.callback(self.options[self.selected_index])
                except Exception as e:
                    logger.error(f"Error in dropdown callback: {e}")
                    
    def set_disabled(self, disabled: bool):
        """
        Set whether the dropdown is disabled.
        
        Args:
            disabled (bool): Whether the dropdown is disabled
        """
        self.disabled = disabled
        if disabled:
            self.open = False


class ControlPanel:
    """
    A panel containing multiple UI controls.
    """
    
    def __init__(self, rect: Tuple[int, int, int, int], title: str = "Controls"):
        """
        Initialize a control panel.
        
        Args:
            rect (Tuple[int, int, int, int]): Panel rectangle (x, y, width, height)
            title (str): Panel title
        """
        self.rect = pygame.Rect(rect)
        self.title = title
        self.controls = []
        self.font = pygame.font.Font(None, 28)
        self.visible = True
        
    def add_control(self, control):
        """
        Add a control to the panel.
        
        Args:
            control: UI control to add
        """
        self.controls.append(control)
        
    def draw(self, surface: pygame.Surface):
        """
        Draw the control panel on a surface.
        
        Args:
            surface (pygame.Surface): Surface to draw on
        """
        if not self.visible:
            return
        
        pygame.draw.rect(surface, (30, 30, 40, 200), self.rect, border_radius=8)
        pygame.draw.rect(surface, (80, 80, 100), self.rect, width=2, border_radius=8)
        
        title_surface = self.font.render(self.title, True, TEXT_COLORS["normal"])
        title_rect = title_surface.get_rect(midtop=(self.rect.centerx, self.rect.y + 10))
        surface.blit(title_surface, title_rect)
        
        
        for control in self.controls:
            control.draw(surface)
            
    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle a pygame event.
        
        Args:
            event (pygame.event.Event): Event to handle
            
        Returns:
            bool: True if event was handled
        """
        if not self.visible:
            return False
            
            
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
            if not self.rect.collidepoint(event.pos):
                
                for control in self.controls:
                    if isinstance(control, DropdownList) and control.open:
                        control.open = False
                        return True
                return False
                
        for control in self.controls:
            if control.handle_event(event):
                return True
                
        return False
        
    def set_visible(self, visible: bool):
        """
        Set whether the panel is visible.
        
        Args:
            visible (bool): Whether the panel is visible
        """
        self.visible = visible


def create_control_panel(x: int, y: int, width: int, height: int, 
                        effects: Dict[int, LightEffect], selected_effect: int) -> ControlPanel:
    """
    Create a control panel for managing effects.
    
    Args:
        x (int): X coordinate
        y (int): Y coordinate
        width (int): Width
        height (int): Height
        effects (Dict[int, LightEffect]): Dictionary of effects by ID
        selected_effect (int): Selected effect ID
        
    Returns:
        ControlPanel: Control panel
    """
    panel = ControlPanel((x, y, width, height), "Effect Controls")
    
    effect = effects.get(selected_effect)
    if not effect:
        return panel

    y_offset = 40

    effect_options = [f"Effect {i}" for i in effects.keys()]
    
    def on_effect_selected(option: str):
        effect_id = int(option.split()[1])
        # TODO: Handle effect selection
    
    effect_index = 0
    for i, key in enumerate(effects.keys()):
        if key == selected_effect:
            effect_index = i
            break
            
    dropdown = DropdownList(
        (x + 10, y + y_offset, width - 20, 30),
        effect_options,
        on_effect_selected,
        effect_index
    )
    panel.add_control(dropdown)
    y_offset += 40
    
    if hasattr(effect, 'segments'):
        segments = effect.segments

        for segment_id, segment in segments.items():
            segment_title = f"Segment {segment_id}"

            def on_speed_change(value: float, sid=segment_id):
                effect.update_segment_param(sid, "move_speed", value)
            
            speed_slider = Slider(
                (x + 10, y + y_offset, width - 20, 20),
                -50.0, 50.0, segment.move_speed,
                on_speed_change,
                format_func=lambda v: f"Speed: {v:.1f}"
            )
            panel.add_control(speed_slider)
            y_offset += 30

            def on_color_toggle(state: bool, sid=segment_id):
                if state:
                    effect.update_segment_param(sid, "color", [0xFF0000, 0x00FF00, 0x0000FF, 0xFF00FF])
                else:
                    effect.update_segment_param(sid, "color", [0x00FF00, 0x0000FF, 0xFF00FF, 0xFF0000])
            
            color_toggle = ToggleButton(
                (x + 10, y + y_offset, width - 20, 30),
                "Change Colors",
                on_color_toggle
            )
            panel.add_control(color_toggle)
            y_offset += 40
            
            def on_reflect_toggle(state: bool, sid=segment_id):
                effect.update_segment_param(sid, "is_edge_reflect", state)
            
            reflect_toggle = ToggleButton(
                (x + 10, y + y_offset, width - 20, 30),
                "Edge Reflection",
                on_reflect_toggle,
                segment.is_edge_reflect
            )
            panel.add_control(reflect_toggle)
            y_offset += 40
    
    return panel