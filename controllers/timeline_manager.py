import time
import threading
import json
import logging
from typing import Dict, List, Tuple, Any, Optional, Set, Callable

from models.light_effect import LightEffect
from controllers.effect_manager import EffectManager

logger = logging.getLogger(__name__)


class TimelineEvent:
    """
    Event in a timeline.
    """
    
    def __init__(self, event_id: str, event_type: str, start_time: float, duration: float,
                 data: Dict[str, Any] = None):
        """
        Initialize a timeline event.
        
        Args:
            event_id (str): Unique event identifier
            event_type (str): Type of event (e.g., "effect_start", "effect_stop", "fade", "crossfade")
            start_time (float): Start time in seconds from timeline start
            duration (float): Duration in seconds
            data (Dict[str, Any]): Event-specific data
        """
        self.event_id = event_id
        self.event_type = event_type
        self.start_time = start_time
        self.duration = duration
        self.data = data or {}
        
        self.executed = False
        self.completed = False
        self.start_timestamp = None
        self.end_timestamp = None
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Returns:
            Dict[str, Any]: Event information as dictionary
        """
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "start_time": self.start_time,
            "duration": self.duration,
            "data": self.data
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TimelineEvent':
        """
        Create from dictionary.
        
        Args:
            data (Dict[str, Any]): Event information dictionary
            
        Returns:
            TimelineEvent: Event object
        """
        return cls(
            event_id=data.get("event_id", ""),
            event_type=data.get("event_type", ""),
            start_time=data.get("start_time", 0.0),
            duration=data.get("duration", 0.0),
            data=data.get("data", {})
        )


class Timeline:
    """
    A timeline of scheduled events.
    """
    
    def __init__(self, timeline_id: str, name: str = "", loop: bool = False):
        """
        Initialize a timeline.
        
        Args:
            timeline_id (str): Unique timeline identifier
            name (str): Timeline name
            loop (bool): Whether to loop the timeline
        """
        self.timeline_id = timeline_id
        self.name = name
        self.loop = loop
        
        self.events: Dict[str, TimelineEvent] = {}
        self.duration = 0.0
        
    def add_event(self, event: TimelineEvent) -> bool:
        """
        Add an event to the timeline.
        
        Args:
            event (TimelineEvent): Event to add
            
        Returns:
            bool: True if added successfully
        """
        if event.event_id in self.events:
            logger.warning(f"Event {event.event_id} already exists in timeline {self.timeline_id}")
            return False
            
        self.events[event.event_id] = event
        
        # Update timeline duration
        self.duration = max(self.duration, event.start_time + event.duration)
        
        return True
        
    def remove_event(self, event_id: str) -> bool:
        """
        Remove an event from the timeline.
        
        Args:
            event_id (str): Event ID
            
        Returns:
            bool: True if removed successfully
        """
        if event_id not in self.events:
            logger.warning(f"Event {event_id} not found in timeline {self.timeline_id}")
            return False
            
        del self.events[event_id]
        
        # Recalculate timeline duration
        if self.events:
            self.duration = max(event.start_time + event.duration for event in self.events.values())
        else:
            self.duration = 0.0
            
        return True
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Returns:
            Dict[str, Any]: Timeline information as dictionary
        """
        return {
            "timeline_id": self.timeline_id,
            "name": self.name,
            "loop": self.loop,
            "duration": self.duration,
            "events": {event_id: event.to_dict() for event_id, event in self.events.items()}
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Timeline':
        """
        Create from dictionary.
        
        Args:
            data (Dict[str, Any]): Timeline information dictionary
            
        Returns:
            Timeline: Timeline object
        """
        timeline = cls(
            timeline_id=data.get("timeline_id", ""),
            name=data.get("name", ""),
            loop=data.get("loop", False)
        )
        
        for event_id, event_data in data.get("events", {}).items():
            event = TimelineEvent.from_dict(event_data)
            timeline.events[event_id] = event
            
        timeline.duration = data.get("duration", 0.0)
        
        return timeline


class TimelineManager:
    """
    Manages multiple timelines.
    """
    
    def __init__(self, effect_manager: EffectManager):
        """
        Initialize the timeline manager.
        
        Args:
            effect_manager (EffectManager): Effect manager for controlling effects
        """
        self.effect_manager = effect_manager
        
        self.timelines: Dict[str, Timeline] = {}
        self.active_timelines: Dict[str, Dict[str, Any]] = {}
        
        self.lock = threading.RLock()
        self.running = False
        self.thread = None
        
        # Callbacks
        self.on_timeline_started = None
        self.on_timeline_completed = None
        self.on_event_started = None
        self.on_event_completed = None
        
    def add_timeline(self, timeline: Timeline) -> bool:
        """
        Add a timeline.
        
        Args:
            timeline (Timeline): Timeline to add
            
        Returns:
            bool: True if added successfully
        """
        with self.lock:
            if timeline.timeline_id in self.timelines:
                logger.warning(f"Timeline {timeline.timeline_id} already exists")
                return False
                
            self.timelines[timeline.timeline_id] = timeline
            logger.info(f"Added timeline {timeline.timeline_id}")
            return True
            
    def remove_timeline(self, timeline_id: str) -> bool:
        """
        Remove a timeline.
        
        Args:
            timeline_id (str): Timeline ID
            
        Returns:
            bool: True if removed successfully
        """
        with self.lock:
            if timeline_id not in self.timelines:
                logger.warning(f"Timeline {timeline_id} not found")
                return False
                
            # Stop the timeline if it's running
            if timeline_id in self.active_timelines:
                self.stop_timeline(timeline_id)
                
            del self.timelines[timeline_id]
            logger.info(f"Removed timeline {timeline_id}")
            return True
            
    def start_timeline(self, timeline_id: str) -> bool:
        """
        Start playing a timeline.
        
        Args:
            timeline_id (str): Timeline ID
            
        Returns:
            bool: True if started successfully
        """
        with self.lock:
            if timeline_id not in self.timelines:
                logger.warning(f"Timeline {timeline_id} not found")
                return False
                
            if timeline_id in self.active_timelines:
                logger.warning(f"Timeline {timeline_id} already running")
                return False
                
            timeline = self.timelines[timeline_id]
            
            # Reset event states
            for event in timeline.events.values():
                event.executed = False
                event.completed = False
                event.start_timestamp = None
                event.end_timestamp = None
                
            # Add to active timelines
            self.active_timelines[timeline_id] = {
                "start_time": time.time(),
                "elapsed": 0.0,
                "cycle_count": 0
            }
            
            if not self.running:
                self.start()
                
            logger.info(f"Started timeline {timeline_id}")
            
            # Call callback
            if self.on_timeline_started:
                self.on_timeline_started(timeline_id)
                
            return True
            
    def stop_timeline(self, timeline_id: str) -> bool:
        """
        Stop playing a timeline.
        
        Args:
            timeline_id (str): Timeline ID
            
        Returns:
            bool: True if stopped successfully
        """
        with self.lock:
            if timeline_id not in self.active_timelines:
                logger.warning(f"Timeline {timeline_id} not running")
                return False
                
            # Stop all active effects from this timeline
            active_effects = set()
            timeline = self.timelines[timeline_id]
            
            for event in timeline.events.values():
                if event.event_type == "effect_start" and event.executed and not event.completed:
                    effect_id = event.data.get("effect_id")
                    if effect_id is not None:
                        active_effects.add(effect_id)
                        
            for effect_id in active_effects:
                self.effect_manager.deactivate_effect(effect_id)
                
            # Remove from active timelines
            del self.active_timelines[timeline_id]
            
            logger.info(f"Stopped timeline {timeline_id}")
            
            # Call callback
            if self.on_timeline_completed:
                self.on_timeline_completed(timeline_id)
                
            return True
            
    def start(self):
        """
        Start the timeline manager.
        """
        if self.running:
            return
            
        self.running = True
        
        # Start the update thread
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()
        
        logger.info("Timeline manager started")
        
    def stop(self):
        """
        Stop the timeline manager.
        """
        if not self.running:
            return
            
        self.running = False
        
        # Wait for thread to stop
        if self.thread:
            self.thread.join(timeout=1.0)
            
        # Stop all active timelines
        for timeline_id in list(self.active_timelines.keys()):
            self.stop_timeline(timeline_id)
            
        logger.info("Timeline manager stopped")
        
    def _update_loop(self):
        """
        Update loop for managing timelines.
        """
        logger.info("Started timeline update thread")
        
        while self.running:
            try:
                with self.lock:
                    current_time = time.time()
                    
                    # Process each active timeline
                    for timeline_id, timeline_state in list(self.active_timelines.items()):
                        if timeline_id not in self.timelines:
                            continue
                            
                        timeline = self.timelines[timeline_id]
                        
                        # Calculate elapsed time in timeline
                        timeline_start_time = timeline_state["start_time"]
                        elapsed = current_time - timeline_start_time
                        timeline_state["elapsed"] = elapsed
                        
                        # Check for timeline loop
                        if timeline.loop and elapsed > timeline.duration and timeline.duration > 0:
                            # Reset for next loop
                            loops_completed = int(elapsed / timeline.duration)
                            
                            if loops_completed > timeline_state["cycle_count"]:
                                # Reset event states for new loop
                                for event in timeline.events.values():
                                    event.executed = False
                                    event.completed = False
                                    event.start_timestamp = None
                                    event.end_timestamp = None
                                    
                                timeline_state["cycle_count"] = loops_completed
                                
                            # Adjust elapsed time
                            elapsed = elapsed % timeline.duration
                            
                        # Process events
                        for event_id, event in timeline.events.items():
                            # Skip already completed events
                            if event.completed:
                                continue
                                
                            # Check if it's time to start the event
                            if not event.executed and elapsed >= event.start_time:
                                event.executed = True
                                event.start_timestamp = current_time
                                
                                # Execute event
                                self._execute_event(timeline_id, event_id)
                                
                                # Call callback
                                if self.on_event_started:
                                    self.on_event_started(timeline_id, event_id)
                                    
                            # Check if event should be completed
                            elif event.executed and not event.completed:
                                event_elapsed = current_time - event.start_timestamp
                                
                                if event_elapsed >= event.duration:
                                    event.completed = True
                                    event.end_timestamp = current_time
                                    
                                    # Complete event
                                    self._complete_event(timeline_id, event_id)
                                    
                                    # Call callback
                                    if self.on_event_completed:
                                        self.on_event_completed(timeline_id, event_id)
                                        
                        # Check if timeline is complete (all events completed)
                        if not timeline.loop:
                            all_completed = all(event.completed for event in timeline.events.values())
                            
                            if all_completed:
                                logger.info(f"Timeline {timeline_id} completed")
                                
                                # Stop the timeline
                                self.stop_timeline(timeline_id)
                
                # Sleep a short time
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error in timeline update thread: {e}")
                time.sleep(0.1)
                
        logger.info("Stopped timeline update thread")
        
    def _execute_event(self, timeline_id: str, event_id: str):
        """
        Execute a timeline event.
        
        Args:
            timeline_id (str): Timeline ID
            event_id (str): Event ID
        """
        timeline = self.timelines.get(timeline_id)
        if not timeline:
            return
            
        event = timeline.events.get(event_id)
        if not event:
            return
            
        logger.debug(f"Executing event {event_id} ({event.event_type}) in timeline {timeline_id}")
        
        # Handle event based on type
        if event.event_type == "effect_start":
            effect_id = event.data.get("effect_id")
            if effect_id is not None:
                self.effect_manager.activate_effect(effect_id)
                
        elif event.event_type == "effect_stop":
            effect_id = event.data.get("effect_id")
            if effect_id is not None:
                self.effect_manager.deactivate_effect(effect_id)
                
        elif event.event_type == "fade":
            effect_id = event.data.get("effect_id")
            target_brightness = event.data.get("target_brightness", 1.0)
            
            if effect_id is not None:
                self._start_fade(effect_id, target_brightness, event.duration)
                
        elif event.event_type == "crossfade":
            from_effect_id = event.data.get("from_effect_id")
            to_effect_id = event.data.get("to_effect_id")
            
            if from_effect_id is not None and to_effect_id is not None:
                self._start_crossfade(from_effect_id, to_effect_id, event.duration)
                
    def _complete_event(self, timeline_id: str, event_id: str):
        """
        Complete a timeline event.
        
        Args:
            timeline_id (str): Timeline ID
            event_id (str): Event ID
        """
        timeline = self.timelines.get(timeline_id)
        if not timeline:
            return
            
        event = timeline.events.get(event_id)
        if not event:
            return
            
        logger.debug(f"Completing event {event_id} ({event.event_type}) in timeline {timeline_id}")
        
        # Handle event completion based on type
        if event.event_type == "fade":
            pass  # Handled by fade thread
            
        elif event.event_type == "crossfade":
            pass  # Handled by crossfade thread
            
    def _start_fade(self, effect_id: int, target_brightness: float, duration: float):
        """
        Start fading an effect.
        
        Args:
            effect_id (int): Effect ID
            target_brightness (float): Target brightness (0.0-1.0)
            duration (float): Duration in seconds
        """
        if effect_id not in self.effect_manager.effects:
            return
            
        # Start fade in a separate thread
        thread = threading.Thread(
            target=self._fade_thread,
            args=(effect_id, target_brightness, duration),
            daemon=True
        )
        
        thread.start()
        
    def _fade_thread(self, effect_id: int, target_brightness: float, duration: float):
        """
        Thread for fading an effect.
        
        Args:
            effect_id (int): Effect ID
            target_brightness (float): Target brightness (0.0-1.0)
            duration (float): Duration in seconds
        """
        try:
            effect = self.effect_manager.effects.get(effect_id)
            if not effect:
                return
                
            start_time = time.time()
            steps = max(1, int(duration * 30))  # 30 steps per second
            
            # Get current brightness
            current_brightness = 1.0  # Default
            
            for i in range(steps + 1):
                progress = i / steps
                
                # Calculate interpolated brightness
                brightness = current_brightness + progress * (target_brightness - current_brightness)
                
                # Apply brightness to all segments
                for segment in effect.segments.values():
                    segment.update_param("brightness", brightness)
                    
                # Sleep for next step
                time.sleep(duration / steps)
                
                # Check if we've been running too long
                if time.time() - start_time > duration * 1.1:
                    break
                    
            # Ensure final brightness is set
            for segment in effect.segments.values():
                segment.update_param("brightness", target_brightness)
                
        except Exception as e:
            logger.error(f"Error in fade thread: {e}")
            
    def _start_crossfade(self, from_effect_id: int, to_effect_id: int, duration: float):
        """
        Start crossfading between effects.
        
        Args:
            from_effect_id (int): Source effect ID
            to_effect_id (int): Target effect ID
            duration (float): Duration in seconds
        """
        if from_effect_id not in self.effect_manager.effects or to_effect_id not in self.effect_manager.effects:
            return
            
        # Start crossfade in a separate thread
        thread = threading.Thread(
            target=self._crossfade_thread,
            args=(from_effect_id, to_effect_id, duration),
            daemon=True
        )
        
        thread.start()
        
    def _crossfade_thread(self, from_effect_id: int, to_effect_id: int, duration: float):
        """
        Thread for crossfading between effects.
        
        Args:
            from_effect_id (int): Source effect ID
            to_effect_id (int): Target effect ID
            duration (float): Duration in seconds
        """
        try:
            from_effect = self.effect_manager.effects.get(from_effect_id)
            to_effect = self.effect_manager.effects.get(to_effect_id)
            
            if not from_effect or not to_effect:
                return
                
            # Activate target effect if not already active
            if to_effect_id not in self.effect_manager.active_effect_ids:
                self.effect_manager.activate_effect(to_effect_id)
                
            # Set initial brightness for target effect
            for segment in to_effect.segments.values():
                segment.update_param("brightness", 0.0)
                
            start_time = time.time()
            steps = max(1, int(duration * 30))  # 30 steps per second
            
            for i in range(steps + 1):
                progress = i / steps
                
                # Calculate interpolated brightness
                from_brightness = 1.0 - progress
                to_brightness = progress
                
                # Apply brightness to all segments
                for segment in from_effect.segments.values():
                    segment.update_param("brightness", from_brightness)
                    
                for segment in to_effect.segments.values():
                    segment.update_param("brightness", to_brightness)
                    
                # Sleep for next step
                time.sleep(duration / steps)
                
                # Check if we've been running too long
                if time.time() - start_time > duration * 1.1:
                    break
                    
            # Ensure final brightness is set
            for segment in from_effect.segments.values():
                segment.update_param("brightness", 0.0)
                
            for segment in to_effect.segments.values():
                segment.update_param("brightness", 1.0)
                
            # Deactivate source effect
            self.effect_manager.deactivate_effect(from_effect_id)
            
        except Exception as e:
            logger.error(f"Error in crossfade thread: {e}")
            
    def create_timeline(self, timeline_id: str, name: str = "", loop: bool = False) -> Timeline:
        """
        Create a new timeline.
        
        Args:
            timeline_id (str): Timeline ID
            name (str): Timeline name
            loop (bool): Whether to loop the timeline
            
        Returns:
            Timeline: The created timeline
        """
        timeline = Timeline(timeline_id, name, loop)
        self.add_timeline(timeline)
        return timeline
        
    def add_effect_start_event(self, timeline_id: str, event_id: str, effect_id: int, 
                             start_time: float, duration: float = 0.0) -> bool:
        """
        Add an effect start event to a timeline.
        
        Args:
            timeline_id (str): Timeline ID
            event_id (str): Event ID
            effect_id (int): Effect ID
            start_time (float): Start time in seconds
            duration (float): Duration in seconds (0 for indefinite)
            
        Returns:
            bool: True if added successfully
        """
        with self.lock:
            if timeline_id not in self.timelines:
                logger.warning(f"Timeline {timeline_id} not found")
                return False
                
            timeline = self.timelines[timeline_id]
            
            event = TimelineEvent(
                event_id=event_id,
                event_type="effect_start",
                start_time=start_time,
                duration=duration,
                data={"effect_id": effect_id}
            )
            
            return timeline.add_event(event)
            
    def add_effect_stop_event(self, timeline_id: str, event_id: str, effect_id: int, 
                            start_time: float, duration: float = 0.0) -> bool:
        """
        Add an effect stop event to a timeline.
        
        Args:
            timeline_id (str): Timeline ID
            event_id (str): Event ID
            effect_id (int): Effect ID
            start_time (float): Start time in seconds
            duration (float): Duration in seconds (usually 0)
            
        Returns:
            bool: True if added successfully
        """
        with self.lock:
            if timeline_id not in self.timelines:
                logger.warning(f"Timeline {timeline_id} not found")
                return False
                
            timeline = self.timelines[timeline_id]
            
            event = TimelineEvent(
                event_id=event_id,
                event_type="effect_stop",
                start_time=start_time,
                duration=duration,
                data={"effect_id": effect_id}
            )
            
            return timeline.add_event(event)
            
    def add_fade_event(self, timeline_id: str, event_id: str, effect_id: int, target_brightness: float,
                     start_time: float, duration: float) -> bool:
        """
        Add a fade event to a timeline.
        
        Args:
            timeline_id (str): Timeline ID
            event_id (str): Event ID
            effect_id (int): Effect ID
            target_brightness (float): Target brightness (0.0-1.0)
            start_time (float): Start time in seconds
            duration (float): Duration in seconds
            
        Returns:
            bool: True if added successfully
        """
        with self.lock:
            if timeline_id not in self.timelines:
                logger.warning(f"Timeline {timeline_id} not found")
                return False
                
            timeline = self.timelines[timeline_id]
            
            event = TimelineEvent(
                event_id=event_id,
                event_type="fade",
                start_time=start_time,
                duration=duration,
                data={
                    "effect_id": effect_id,
                    "target_brightness": target_brightness
                }
            )
            
            return timeline.add_event(event)
            
    def add_crossfade_event(self, timeline_id: str, event_id: str, from_effect_id: int, 
                          to_effect_id: int, start_time: float, duration: float) -> bool:
        """
        Add a crossfade event to a timeline.
        
        Args:
            timeline_id (str): Timeline ID
            event_id (str): Event ID
            from_effect_id (int): Source effect ID
            to_effect_id (int): Target effect ID
            start_time (float): Start time in seconds
            duration (float): Duration in seconds
            
        Returns:
            bool: True if added successfully
        """
        with self.lock:
            if timeline_id not in self.timelines:
                logger.warning(f"Timeline {timeline_id} not found")
                return False
                
            timeline = self.timelines[timeline_id]
            
            event = TimelineEvent(
                event_id=event_id,
                event_type="crossfade",
                start_time=start_time,
                duration=duration,
                data={
                    "from_effect_id": from_effect_id,
                    "to_effect_id": to_effect_id
                }
            )
            
            return timeline.add_event(event)
            
    def save_timelines(self, filename: str) -> bool:
        """
        Save timelines to file.
        
        Args:
            filename (str): Filename
            
        Returns:
            bool: True if saved successfully
        """
        try:
            with self.lock:
                data = {
                    timeline_id: timeline.to_dict()
                    for timeline_id, timeline in self.timelines.items()
                }
                
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                    
                logger.info(f"Saved timelines to {filename}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving timelines: {e}")
            return False
            
    def load_timelines(self, filename: str) -> bool:
        """
        Load timelines from file.
        
        Args:
            filename (str): Filename
            
        Returns:
            bool: True if loaded successfully
        """
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                
            with self.lock:
                # Xóa các timeline hiện tại
                for timeline_id in list(self.active_timelines.keys()):
                    self.stop_timeline(timeline_id)
                    
                self.timelines.clear()
                
                # Tải các timeline mới
                for timeline_id, timeline_data in data.items():
                    timeline = Timeline.from_dict(timeline_data)
                    self.timelines[timeline_id] = timeline
                    
                logger.info(f"Loaded {len(self.timelines)} timelines from {filename}")
                return True
                
        except Exception as e:
            logger.error(f"Error loading timelines: {e}")
            return False
            
    def get_all_timelines(self) -> List[Dict[str, Any]]:
        """
        Get information about all timelines.
        
        Returns:
            List[Dict[str, Any]]: List of timeline information
        """
        with self.lock:
            return [
                {
                    "timeline_id": timeline.timeline_id,
                    "name": timeline.name,
                    "duration": timeline.duration,
                    "loop": timeline.loop,
                    "events": len(timeline.events),
                    "active": timeline.timeline_id in self.active_timelines,
                    "elapsed": self.active_timelines.get(timeline.timeline_id, {}).get("elapsed", 0)
                }
                for timeline in self.timelines.values()
            ]
            
    def get_timeline_info(self, timeline_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a timeline.
        
        Args:
            timeline_id (str): Timeline ID
            
        Returns:
            Optional[Dict[str, Any]]: Timeline information or None if not found
        """
        with self.lock:
            if timeline_id not in self.timelines:
                return None
                
            timeline = self.timelines[timeline_id]
            
            events = [
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "start_time": event.start_time,
                    "duration": event.duration,
                    "data": event.data,
                    "executed": event.executed,
                    "completed": event.completed
                }
                for event in timeline.events.values()
            ]

            events.sort(key=lambda e: e["start_time"])
            
            return {
                "timeline_id": timeline.timeline_id,
                "name": timeline.name,
                "duration": timeline.duration,
                "loop": timeline.loop,
                "events": events,
                "active": timeline.timeline_id in self.active_timelines,
                "elapsed": self.active_timelines.get(timeline_id, {}).get("elapsed", 0),
                "cycle_count": self.active_timelines.get(timeline_id, {}).get("cycle_count", 0)
            }
            
    def get_status(self) -> Dict[str, Any]:
        """
        Get status information.
        
        Returns:
            Dict[str, Any]: Status information
        """
        with self.lock:
            return {
                "timelines": len(self.timelines),
                "active_timelines": len(self.active_timelines),
                "running": self.running
            }