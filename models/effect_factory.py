"""
Factory for creating light effects with predefined templates.
"""
from typing import Dict, List, Any, Optional
import logging

from models.light_effect import LightEffect
from models.light_segment import LightSegment

logger = logging.getLogger(__name__)


class EffectTemplate:
    """
    Template for creating light effects.
    """
    
    def __init__(self, template_id: str, name: str, description: str = ""):
        """
        Initialize an effect template.
        
        Args:
            template_id (str): Unique identifier for this template
            name (str): Display name of the template
            description (str): Description of the template
        """
        self.template_id = template_id
        self.name = name
        self.description = description
        self.parameters: Dict[str, Dict[str, Any]] = {}
        
    def add_parameter(self, name: str, default_value: Any, min_value: Any = None, 
                      max_value: Any = None, description: str = ""):
        """
        Add a parameter to the template.
        
        Args:
            name (str): Parameter name
            default_value (Any): Default value
            min_value (Any): Minimum value (for numeric parameters)
            max_value (Any): Maximum value (for numeric parameters)
            description (str): Parameter description
        """
        self.parameters[name] = {
            "default": default_value,
            "min": min_value,
            "max": max_value,
            "description": description
        }
        
    def create_effect(self, effect_id: int, led_count: int, fps: int, parameters: Dict[str, Any] = None) -> LightEffect:
        """
        Create a light effect from this template.
        
        Args:
            effect_id (int): Unique identifier for the effect
            led_count (int): Number of LEDs
            fps (int): Frames per second
            parameters (Dict[str, Any]): Parameter values (uses defaults if not provided)
            
        Returns:
            LightEffect: The created light effect
        """
        raise NotImplementedError("Subclasses must implement create_effect()")
        
    def get_info(self) -> Dict[str, Any]:
        """
        Get template information.
        
        Returns:
            Dict[str, Any]: Template information
        """
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class RainbowEffectTemplate(EffectTemplate):
    """
    Template for creating rainbow effects.
    """
    
    def __init__(self):
        """
        Initialize the rainbow effect template.
        """
        super().__init__(
            template_id="rainbow",
            name="Rainbow",
            description="Smooth rainbow color transition across all LEDs"
        )
        
        self.add_parameter(
            name="speed",
            default_value=10.0,
            min_value=0.1,
            max_value=100.0,
            description="Movement speed in LEDs per second"
        )
        self.add_parameter(
            name="saturation",
            default_value=1.0,
            min_value=0.0,
            max_value=1.0,
            description="Color saturation (0.0-1.0)"
        )
        self.add_parameter(
            name="brightness",
            default_value=1.0,
            min_value=0.0,
            max_value=1.0,
            description="Brightness (0.0-1.0)"
        )
        self.add_parameter(
            name="is_edge_reflect",
            default_value=True,
            description="Whether to reflect at edges"
        )
        
    def create_effect(self, effect_id: int, led_count: int, fps: int,
                     parameters: Dict[str, Any] = None) -> LightEffect:
        """
        Create a rainbow effect.
        
        Args:
            effect_id (int): Unique identifier for the effect
            led_count (int): Number of LEDs
            fps (int): Frames per second
            parameters (Dict[str, Any]): Parameter values
            
        Returns:
            LightEffect: The created rainbow effect
        """
        params = {}
        for name, param_info in self.parameters.items():
            if parameters and name in parameters:
                params[name] = parameters[name]
            else:
                params[name] = param_info["default"]
                
        effect = LightEffect(effect_id, led_count, fps)

        segment = LightSegment(
            segment_ID=1,
            color=[0xFF0000, 0xFFFF00, 0x00FF00, 0x0000FF],  
            transparency=[0.0, 0.0, 0.0, 0.0],
            length=[led_count // 3, led_count // 3, led_count // 3], 
            move_speed=params["speed"],
            move_range=[0, led_count - 1],
            initial_position=0,
            is_edge_reflect=params["is_edge_reflect"],
            dimmer_time=[0, 0, 0, 0, 0]
        )
        
        effect.add_segment(1, segment)
        
        return effect


class PulseEffectTemplate(EffectTemplate):
    """
    Template for creating pulsing light effects.
    """
    
    def __init__(self):
        """
        Initialize the pulse effect template.
        """
        super().__init__(
            template_id="pulse",
            name="Pulse",
            description="Pulsing light effect with configurable colors and timing"
        )
        
        self.add_parameter(
            name="color",
            default_value=0x00FF00, 
            description="Base color"
        )
        self.add_parameter(
            name="pulse_speed",
            default_value=1.0,
            min_value=0.1,
            max_value=10.0,
            description="Pulses per second"
        )
        self.add_parameter(
            name="min_brightness",
            default_value=0.2,
            min_value=0.0,
            max_value=1.0,
            description="Minimum brightness (0.0-1.0)"
        )
        
    def create_effect(self, effect_id: int, led_count: int, fps: int,
                     parameters: Dict[str, Any] = None) -> LightEffect:
        """
        Create a pulse effect.
        
        Args:
            effect_id (int): Unique identifier for the effect
            led_count (int): Number of LEDs
            fps (int): Frames per second
            parameters (Dict[str, Any]): Parameter values
            
        Returns:
            LightEffect: The created pulse effect
        """
        params = {}
        for name, param_info in self.parameters.items():
            if parameters and name in parameters:
                params[name] = parameters[name]
            else:
                params[name] = param_info["default"]
                
        pulse_duration_ms = int(1000 / params["pulse_speed"])
        fade_time = pulse_duration_ms // 2
        
        effect = LightEffect(effect_id, led_count, fps)
        
        segment = LightSegment(
            segment_ID=1,
            color=[params["color"], params["color"], params["color"], params["color"]],
            transparency=[0.0, 0.0, 0.0, 0.0], 
            length=[led_count, 0, 0],  
            move_speed=0.0, 
            move_range=[0, led_count - 1],
            initial_position=0,
            is_edge_reflect=False,
            dimmer_time=[0, fade_time, 0, fade_time, 0]  
        )
        
        effect.add_segment(1, segment)
        
        return effect


class ChaseEffectTemplate(EffectTemplate):
    """
    Template for creating chase light effects.
    """
    
    def __init__(self):
        """
        Initialize the chase effect template.
        """
        super().__init__(
            template_id="chase",
            name="Chase",
            description="Moving light chaser effect with multiple segments"
        )
        
        self.add_parameter(
            name="segment_count",
            default_value=3,
            min_value=1,
            max_value=10,
            description="Number of light segments"
        )
        self.add_parameter(
            name="segment_length",
            default_value=5,
            min_value=1,
            max_value=100,
            description="Length of each segment in LEDs"
        )
        self.add_parameter(
            name="gap_length",
            default_value=15,
            min_value=0,
            max_value=100,
            description="Gap between segments in LEDs"
        )
        self.add_parameter(
            name="speed",
            default_value=20.0,
            min_value=0.1,
            max_value=100.0,
            description="Movement speed in LEDs per second"
        )
        self.add_parameter(
            name="color",
            default_value=0x0000FF,  
            description="Segment color"
        )
        
    def create_effect(self, effect_id: int, led_count: int, fps: int,
                     parameters: Dict[str, Any] = None) -> LightEffect:
        """
        Create a chase effect.
        
        Args:
            effect_id (int): Unique identifier for the effect
            led_count (int): Number of LEDs
            fps (int): Frames per second
            parameters (Dict[str, Any]): Parameter values
            
        Returns:
            LightEffect: The created chase effect
        """
        params = {}
        for name, param_info in self.parameters.items():
            if parameters and name in parameters:
                params[name] = parameters[name]
            else:
                params[name] = param_info["default"]

        effect = LightEffect(effect_id, led_count, fps)
        
        pattern_length = (params["segment_length"] + params["gap_length"]) * params["segment_count"]
        
        for i in range(params["segment_count"]):

            initial_position = i * (params["segment_length"] + params["gap_length"])
            
            segment = LightSegment(
                segment_ID=i + 1,
                color=[params["color"], params["color"], params["color"], params["color"]],
                transparency=[0.0, 0.0, 0.0, 0.0], 
                length=[params["segment_length"], 0, 0], 
                move_speed=params["speed"],
                move_range=[0, led_count - 1],
                initial_position=initial_position % led_count,
                is_edge_reflect=False,  
                dimmer_time=[0, 0, 0, 0, 0] 
            )

            effect.add_segment(i + 1, segment)
        
        return effect


class EffectFactory:
    """
    Factory for creating light effects from templates.
    """
    
    def __init__(self):
        """
        Initialize the effect factory.
        """
        self.templates: Dict[str, EffectTemplate] = {}
        
        # Register built-in templates
        self.register_template(RainbowEffectTemplate())
        self.register_template(PulseEffectTemplate())
        self.register_template(ChaseEffectTemplate())
        
    def register_template(self, template: EffectTemplate):
        """
        Register an effect template.
        
        Args:
            template (EffectTemplate): The template to register
        """
        self.templates[template.template_id] = template
        logger.debug(f"Registered effect template: {template.template_id}")
        
    def unregister_template(self, template_id: str) -> bool:
        """
        Unregister an effect template.
        
        Args:
            template_id (str): ID of the template to unregister
            
        Returns:
            bool: True if unregistered, False if not found
        """
        if template_id in self.templates:
            del self.templates[template_id]
            logger.debug(f"Unregistered effect template: {template_id}")
            return True
        return False
        
    def get_template(self, template_id: str) -> Optional[EffectTemplate]:
        """
        Get an effect template by ID.
        
        Args:
            template_id (str): Template ID
            
        Returns:
            Optional[EffectTemplate]: The template if found, None otherwise
        """
        return self.templates.get(template_id)
        
    def create_effect(self, template_id: str, effect_id: int, led_count: int, fps: int,
                     parameters: Dict[str, Any] = None) -> Optional[LightEffect]:
        """
        Create a light effect from a template.
        
        Args:
            template_id (str): Template ID
            effect_id (int): Unique identifier for the effect
            led_count (int): Number of LEDs
            fps (int): Frames per second
            parameters (Dict[str, Any]): Parameter values
            
        Returns:
            Optional[LightEffect]: The created effect if template found, None otherwise
        """
        template = self.get_template(template_id)
        if template:
            logger.debug(f"Creating effect {effect_id} from template {template_id}")
            return template.create_effect(effect_id, led_count, fps, parameters)
        else:
            logger.warning(f"Template not found: {template_id}")
            return None
            
    def get_all_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all registered templates.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of template information by ID
        """
        result = {}
        for template_id, template in self.templates.items():
            result[template_id] = template.get_info()
        return result