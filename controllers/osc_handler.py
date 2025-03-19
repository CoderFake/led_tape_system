import re
import threading
from typing import Dict, Any, Callable
from pythonosc import dispatcher
from pythonosc import osc_server

from models.light_effect import LightEffect


class OSCHandler:
    """
    Handles OSC (Open Sound Control) messages for controlling light effects.
    """
    
    def __init__(self, light_effects: Dict[int, LightEffect], ip: str, port: int):
        """
        Initialize the OSC handler.
        
        Args:
            light_effects (Dict[int, LightEffect]): Dictionary of light effects by ID
            ip (str): IP address to listen on
            port (int): Port to listen on
        """
        self.light_effects = light_effects
        self.ip = ip
        self.port = port
        self.server = None
        self.server_thread = None
        self.running = False
        
        self.dispatcher = dispatcher.Dispatcher()
        self.dispatcher.set_default_handler(self.default_handler)

        self.dispatcher.map("/effect/*", self.osc_callback)
        
    def start(self):
        """
        Start the OSC server in a separate thread.
        """
        if self.running:
            return
            
        self.server = osc_server.ThreadingOSCUDPServer((self.ip, self.port), self.dispatcher)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        self.running = True
        print(f"OSC server listening on {self.ip}:{self.port}")
        
    def stop(self):
        """
        Stop the OSC server.
        """
        if not self.running:
            return
            
        self.server.shutdown()
        self.server_thread.join(timeout=1.0)
        self.running = False
        print("OSC server stopped")
        
    def default_handler(self, address: str, *args):
        """
        Default handler for OSC messages.
        
        Args:
            address (str): OSC address
            *args: OSC arguments
        """
        print(f"Received unhandled OSC message: {address} {args}")
        
    def osc_callback(self, address: str, *args):
        """
        Handle OSC messages for light effects.
        Format: /effect/{effect_ID}/segment/{segment_ID}/{param_name} {value}
        
        Args:
            address (str): OSC address
            *args: OSC arguments (value)
        """
        pattern = r"/effect/(\d+)(?:/segment/(\d+))?(?:/(\w+))?"
        match = re.match(pattern, address)
        
        if not match:
            print(f"Invalid OSC address format: {address}")
            return

        effect_id = int(match.group(1))
        segment_id = int(match.group(2)) if match.group(2) else None
        param_name = match.group(3) if match.group(3) else None
  
        if not args:
            print(f"No value provided for {address}")
            return
            
        value = args[0]
        
        if effect_id in self.light_effects:
            effect = self.light_effects[effect_id]
            
            if segment_id is None:
                if param_name == "clear":
                    effect.segments.clear()
                    print(f"Cleared all segments in effect {effect_id}")
                    
            elif param_name:
                if segment_id in effect.segments:
                    effect.update_segment_param(segment_id, param_name, value)
                    print(f"Updated {param_name} to {value} for segment {segment_id} in effect {effect_id}")
                else:
                    print(f"Segment {segment_id} not found in effect {effect_id}")
            
            else:
                print(f"Invalid OSC command: {address}")
        else:
            print(f"Effect {effect_id} not found")


class OSCHandlerFactory:
    """
    Factory for creating OSC handlers.
    """
    
    @staticmethod
    def create(light_effects: Dict[int, LightEffect], ip: str, port: int) -> OSCHandler:
        """
        Create an OSC handler.
        
        Args:
            light_effects (Dict[int, LightEffect]): Dictionary of light effects by ID
            ip (str): IP address to listen on
            port (int): Port to listen on
            
        Returns:
            OSCHandler: OSC handler instance
        """
        return OSCHandler(light_effects, ip, port)