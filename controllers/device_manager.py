import time
import threading
import socket
import json
import logging
from typing import Dict, List, Tuple, Any, Optional, Set, Callable
import queue

from models.light_effect import LightEffect
from utils.performance import PerformanceMonitor

logger = logging.getLogger(__name__)


class DeviceInfo:
    """
    Information about a connected device.
    """
    
    def __init__(self, device_id: str, name: str, ip_address: str, port: int = 8888, 
                 led_count: int = 0, segment_count: int = 0, max_fps: int = 60):
        """
        Initialize device information.
        
        Args:
            device_id (str): Unique device identifier
            name (str): Device name
            ip_address (str): IP address
            port (int): Port number
            led_count (int): Total number of LEDs
            segment_count (int): Number of segments
            max_fps (int): Maximum FPS supported
        """
        self.device_id = device_id
        self.name = name
        self.ip_address = ip_address
        self.port = port
        self.led_count = led_count
        self.segment_count = segment_count
        self.max_fps = max_fps
        
        self.connected = False
        self.last_ping = 0
        self.latency = 0
        self.segments = {}
        self.capabilities = {}
        self.error_count = 0
        self.status = "disconnected"
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Returns:
            Dict[str, Any]: Device information as dictionary
        """
        return {
            "device_id": self.device_id,
            "name": self.name,
            "ip_address": self.ip_address,
            "port": self.port,
            "led_count": self.led_count,
            "segment_count": self.segment_count,
            "max_fps": self.max_fps,
            "connected": self.connected,
            "latency": self.latency,
            "error_count": self.error_count,
            "status": self.status,
            "segments": self.segments,
            "capabilities": self.capabilities
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceInfo':
        """
        Create from dictionary.
        
        Args:
            data (Dict[str, Any]): Device information dictionary
            
        Returns:
            DeviceInfo: Device information object
        """
        device = cls(
            device_id=data.get("device_id", ""),
            name=data.get("name", ""),
            ip_address=data.get("ip_address", ""),
            port=data.get("port", 8888),
            led_count=data.get("led_count", 0),
            segment_count=data.get("segment_count", 0),
            max_fps=data.get("max_fps", 60)
        )
        
        device.connected = data.get("connected", False)
        device.latency = data.get("latency", 0)
        device.error_count = data.get("error_count", 0)
        device.status = data.get("status", "disconnected")
        device.segments = data.get("segments", {})
        device.capabilities = data.get("capabilities", {})
        
        return device


class SegmentInfo:
    """
    Information about a device segment.
    """
    
    def __init__(self, segment_id: str, device_id: str, start_index: int, end_index: int, 
                 name: str = "", color: Tuple[int, int, int] = (255, 255, 255)):
        """
        Initialize segment information.
        
        Args:
            segment_id (str): Unique segment identifier
            device_id (str): Device identifier
            start_index (int): Start LED index
            end_index (int): End LED index
            name (str): Segment name
            color (Tuple[int, int, int]): Segment color
        """
        self.segment_id = segment_id
        self.device_id = device_id
        self.start_index = start_index
        self.end_index = end_index
        self.name = name
        self.color = color
        
        self.effect_id = None
        self.brightness = 1.0
        self.active = True
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Returns:
            Dict[str, Any]: Segment information as dictionary
        """
        return {
            "segment_id": self.segment_id,
            "device_id": self.device_id,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "name": self.name,
            "color": self.color,
            "effect_id": self.effect_id,
            "brightness": self.brightness,
            "active": self.active
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SegmentInfo':
        """
        Create from dictionary.
        
        Args:
            data (Dict[str, Any]): Segment information dictionary
            
        Returns:
            SegmentInfo: Segment information object
        """
        segment = cls(
            segment_id=data.get("segment_id", ""),
            device_id=data.get("device_id", ""),
            start_index=data.get("start_index", 0),
            end_index=data.get("end_index", 0),
            name=data.get("name", ""),
            color=data.get("color", (255, 255, 255))
        )
        
        segment.effect_id = data.get("effect_id")
        segment.brightness = data.get("brightness", 1.0)
        segment.active = data.get("active", True)
        
        return segment


class DeviceManager:
    """
    Manages multiple LED devices.
    """
    
    def __init__(self):
        """
        Initialize the device manager.
        """
        self.devices: Dict[str, DeviceInfo] = {}
        self.segments: Dict[str, SegmentInfo] = {}
        self.device_queues: Dict[str, queue.Queue] = {}
        self.worker_threads: Dict[str, threading.Thread] = {}
        
        self.lock = threading.RLock()
        self.running = False
        self.discovery_thread = None
        self.monitor_thread = None
        
        self.perf_monitor = PerformanceMonitor()
        
        # Callbacks
        self.on_device_connected = None
        self.on_device_disconnected = None
        self.on_device_updated = None
        
    def add_device(self, device_id: str, name: str, ip_address: str, port: int = 8888) -> bool:
        """
        Add a device.
        
        Args:
            device_id (str): Device ID
            name (str): Device name
            ip_address (str): IP address
            port (int): Port number
            
        Returns:
            bool: True if added successfully
        """
        with self.lock:
            if device_id in self.devices:
                logger.warning(f"Device {device_id} already exists")
                return False
                
            device = DeviceInfo(device_id, name, ip_address, port)
            self.devices[device_id] = device
            
            # Tạo hàng đợi và worker thread cho thiết bị
            self.device_queues[device_id] = queue.Queue()
            
            if self.running:
                self._start_device_worker(device_id)
                
            logger.info(f"Added device {device_id} ({name}) at {ip_address}:{port}")
            return True
            
    def remove_device(self, device_id: str) -> bool:
        """
        Remove a device.
        
        Args:
            device_id (str): Device ID
            
        Returns:
            bool: True if removed successfully
        """
        with self.lock:
            if device_id not in self.devices:
                logger.warning(f"Device {device_id} not found")
                return False
                
            # Xóa các segment của thiết bị
            segments_to_remove = [seg_id for seg_id, seg in self.segments.items() if seg.device_id == device_id]
            for segment_id in segments_to_remove:
                del self.segments[segment_id]
                
            # Dừng worker thread
            if device_id in self.worker_threads and self.worker_threads[device_id].is_alive():
                # Signal để dừng thread
                self.device_queues[device_id].put(None)
                self.worker_threads[device_id].join(timeout=1.0)
                del self.worker_threads[device_id]
                
            # Xóa hàng đợi
            if device_id in self.device_queues:
                del self.device_queues[device_id]
                
            # Xóa thiết bị
            del self.devices[device_id]
            
            logger.info(f"Removed device {device_id}")
            return True
            
    def add_segment(self, segment_id: str, device_id: str, start_index: int, end_index: int, 
                  name: str = "", color: Tuple[int, int, int] = (255, 255, 255)) -> bool:
        """
        Add a segment.
        
        Args:
            segment_id (str): Segment ID
            device_id (str): Device ID
            start_index (int): Start LED index
            end_index (int): End LED index
            name (str): Segment name
            color (Tuple[int, int, int]): Segment color
            
        Returns:
            bool: True if added successfully
        """
        with self.lock:
            if segment_id in self.segments:
                logger.warning(f"Segment {segment_id} already exists")
                return False
                
            if device_id not in self.devices:
                logger.warning(f"Device {device_id} not found")
                return False
                
            device = self.devices[device_id]
            
            if start_index < 0 or end_index >= device.led_count or start_index > end_index:
                logger.warning(f"Invalid segment range: {start_index}-{end_index}")
                return False
                
            segment = SegmentInfo(segment_id, device_id, start_index, end_index, name, color)
            self.segments[segment_id] = segment
            
            # Cập nhật thông tin segment trong thiết bị
            device.segments[segment_id] = {
                "start": start_index,
                "end": end_index,
                "name": name
            }
            
            logger.info(f"Added segment {segment_id} to device {device_id}")
            return True
            
    def remove_segment(self, segment_id: str) -> bool:
        """
        Remove a segment.
        
        Args:
            segment_id (str): Segment ID
            
        Returns:
            bool: True if removed successfully
        """
        with self.lock:
            if segment_id not in self.segments:
                logger.warning(f"Segment {segment_id} not found")
                return False
                
            segment = self.segments[segment_id]
            device_id = segment.device_id
            
            # Xóa segment khỏi thiết bị
            if device_id in self.devices and segment_id in self.devices[device_id].segments:
                del self.devices[device_id].segments[segment_id]
                
            # Xóa segment
            del self.segments[segment_id]
            
            logger.info(f"Removed segment {segment_id}")
            return True
            
    def connect_device(self, device_id: str) -> bool:
        """
        Connect to a device.
        
        Args:
            device_id (str): Device ID
            
        Returns:
            bool: True if connected successfully
        """
        with self.lock:
            if device_id not in self.devices:
                logger.warning(f"Device {device_id} not found")
                return False
                
            device = self.devices[device_id]
            
            try:
                # Kết nối đến thiết bị
                start_time = time.time()
                
                # Tạo socket kết nối đến thiết bị
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2.0)
                s.connect((device.ip_address, device.port))
                
                # Gửi lệnh ping
                s.send(b'{"command":"ping"}\n')
                
                # Nhận phản hồi
                response = s.recv(1024).decode('utf-8')
                s.close()
                
                end_time = time.time()
                
                # Xử lý phản hồi
                try:
                    data = json.loads(response)
                    
                    # Cập nhật thông tin thiết bị
                    if "led_count" in data:
                        device.led_count = data["led_count"]
                    if "segment_count" in data:
                        device.segment_count = data["segment_count"]
                    if "max_fps" in data:
                        device.max_fps = data["max_fps"]
                    if "capabilities" in data:
                        device.capabilities = data["capabilities"]
                        
                except json.JSONDecodeError:
                    logger.warning(f"Invalid response from device {device_id}: {response}")
                
                # Cập nhật trạng thái thiết bị
                device.connected = True
                device.status = "connected"
                device.latency = (end_time - start_time) * 1000
                device.last_ping = time.time()
                
                logger.info(f"Connected to device {device_id}")
                
                # Gọi callback
                if self.on_device_connected:
                    self.on_device_connected(device_id)
                    
                return True
                
            except socket.error as e:
                device.connected = False
                device.status = f"error: {str(e)}"
                device.error_count += 1
                
                logger.error(f"Error connecting to device {device_id}: {e}")
                return False
                
    def disconnect_device(self, device_id: str) -> bool:
        """
        Disconnect from a device.
        
        Args:
            device_id (str): Device ID
            
        Returns:
            bool: True if disconnected successfully
        """
        with self.lock:
            if device_id not in self.devices:
                logger.warning(f"Device {device_id} not found")
                return False
                
            device = self.devices[device_id]
            
            # Cập nhật trạng thái thiết bị
            device.connected = False
            device.status = "disconnected"
            
            logger.info(f"Disconnected from device {device_id}")
            
            # Gọi callback
            if self.on_device_disconnected:
                self.on_device_disconnected(device_id)
                
            return True
            
    def update_led_data(self, device_id: str, led_data: List[List[int]]) -> bool:
        """
        Update LED data for a device.
        
        Args:
            device_id (str): Device ID
            led_data (List[List[int]]): LED data (list of RGB values)
            
        Returns:
            bool: True if updated successfully
        """
        with self.lock:
            if device_id not in self.devices:
                logger.warning(f"Device {device_id} not found")
                return False
                
            if not self.devices[device_id].connected:
                logger.debug(f"Device {device_id} not connected")
                return False
                
            # Đặt dữ liệu vào hàng đợi của thiết bị
            if device_id in self.device_queues:
                # Định dạng dữ liệu để gửi đến thiết bị
                data = {
                    "command": "update_leds",
                    "data": led_data
                }
                
                try:
                    self.device_queues[device_id].put(data, block=False)
                    return True
                except queue.Full:
                    logger.warning(f"Queue full for device {device_id}")
                    return False
            
            return False
            
    def update_segment(self, segment_id: str, effect_id: Optional[int] = None, 
                     brightness: Optional[float] = None, active: Optional[bool] = None) -> bool:
        """
        Update segment properties.
        
        Args:
            segment_id (str): Segment ID
            effect_id (Optional[int]): Effect ID
            brightness (Optional[float]): Brightness (0.0-1.0)
            active (Optional[bool]): Whether the segment is active
            
        Returns:
            bool: True if updated successfully
        """
        with self.lock:
            if segment_id not in self.segments:
                logger.warning(f"Segment {segment_id} not found")
                return False
                
            segment = self.segments[segment_id]
            
            # Cập nhật thông tin segment
            if effect_id is not None:
                segment.effect_id = effect_id
                
            if brightness is not None:
                segment.brightness = max(0.0, min(1.0, brightness))
                
            if active is not None:
                segment.active = active
                
            # Gửi thông tin cập nhật đến thiết bị
            device_id = segment.device_id
            if device_id in self.devices and self.devices[device_id].connected:
                data = {
                    "command": "update_segment",
                    "segment_id": segment_id,
                    "data": {
                        "start": segment.start_index,
                        "end": segment.end_index,
                        "effect_id": segment.effect_id,
                        "brightness": segment.brightness,
                        "active": segment.active
                    }
                }
                
                try:
                    self.device_queues[device_id].put(data, block=False)
                    return True
                except queue.Full:
                    logger.warning(f"Queue full for device {device_id}")
                    return False
            
            return True
            
    def start(self):
        """
        Start device manager.
        """
        if self.running:
            return
            
        self.running = True
        
        # Khởi động các worker threads cho từng thiết bị
        for device_id in self.devices:
            self._start_device_worker(device_id)
            
        # Khởi động thread giám sát
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        # Khởi động thread khám phá thiết bị
        self.discovery_thread = threading.Thread(target=self._discovery_loop, daemon=True)
        self.discovery_thread.start()
        
        logger.info("Device manager started")
        
    def stop(self):
        """
        Stop device manager.
        """
        if not self.running:
            return
            
        self.running = False
        
        # Dừng các worker threads
        for device_id, queue in self.device_queues.items():
            queue.put(None)
            
        for device_id, thread in self.worker_threads.items():
            if thread.is_alive():
                thread.join(timeout=1.0)
                
        # Xóa các threads
        self.worker_threads.clear()
        
        logger.info("Device manager stopped")
        
    def _start_device_worker(self, device_id: str):
        """
        Start worker thread for a device.
        
        Args:
            device_id (str): Device ID
        """
        if device_id in self.worker_threads and self.worker_threads[device_id].is_alive():
            return
            
        thread = threading.Thread(
            target=self._device_worker,
            args=(device_id,),
            daemon=True
        )
        
        self.worker_threads[device_id] = thread
        thread.start()
        
    def _device_worker(self, device_id: str):
        """
        Worker function for device communication.
        
        Args:
            device_id (str): Device ID
        """
        logger.info(f"Started worker thread for device {device_id}")
        
        device_queue = self.device_queues[device_id]
        
        while self.running:
            try:
                # Lấy dữ liệu từ hàng đợi
                data = device_queue.get(timeout=0.1)
                
                # Kiểm tra tín hiệu dừng
                if data is None:
                    break
                    
                with self.lock:
                    if device_id not in self.devices:
                        continue
                        
                    device = self.devices[device_id]
                    
                    if not device.connected:
                        continue
                        
                    # Gửi dữ liệu đến thiết bị
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.settimeout(1.0)
                        s.connect((device.ip_address, device.port))
                        
                        # Gửi dữ liệu dưới dạng JSON
                        s.send((json.dumps(data) + '\n').encode('utf-8'))
                        
                        # Không cần đợi phản hồi cho dữ liệu LED
                        s.close()
                        
                    except socket.error as e:
                        device.connected = False
                        device.status = f"error: {str(e)}"
                        device.error_count += 1
                        
                        logger.error(f"Error communicating with device {device_id}: {e}")
                        
                        # Gọi callback
                        if self.on_device_disconnected:
                            self.on_device_disconnected(device_id)
                            
            except queue.Empty:
                pass
                
        logger.info(f"Stopped worker thread for device {device_id}")
        
    def _monitor_loop(self):
        """
        Monitor thread function.
        """
        logger.info("Started device monitor thread")
        
        while self.running:
            try:
                with self.lock:
                    current_time = time.time()
                    
                    for device_id, device in self.devices.items():
                        if device.connected:
                            # Kiểm tra xem thiết bị còn hoạt động không (ping mỗi 5 giây)
                            if current_time - device.last_ping > 5.0:
                                # Ping thiết bị
                                try:
                                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                    s.settimeout(1.0)
                                    s.connect((device.ip_address, device.port))
                                    
                                    start_time = time.time()
                                    s.send(b'{"command":"ping"}\n')
                                    s.recv(1024)
                                    end_time = time.time()
                                    
                                    s.close()
                                    
                                    device.last_ping = current_time
                                    device.latency = (end_time - start_time) * 1000
                                    
                                except socket.error:
                                    device.connected = False
                                    device.status = "disconnected"
                                    device.error_count += 1
                                    
                                    logger.warning(f"Lost connection to device {device_id}")
                                    
                                    # Gọi callback
                                    if self.on_device_disconnected:
                                        self.on_device_disconnected(device_id)
                
                # Đợi một chút
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error in monitor thread: {e}")
                time.sleep(1.0)
                
        logger.info("Stopped device monitor thread")
        
    def _discovery_loop(self):
        """
        Device discovery thread function.
        """
        logger.info("Started device discovery thread")
        
        while self.running:
            try:
                # Gửi gói tin broadcast để khám phá thiết bị mới
                discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                discovery_socket.settimeout(1.0)
                
                # Gửi gói tin broadcast
                discovery_data = json.dumps({"command": "discover"}).encode('utf-8')
                discovery_socket.sendto(discovery_data, ('<broadcast>', 8889))
                
                # Đợi phản hồi
                start_time = time.time()
                while time.time() - start_time < 2.0:
                    try:
                        data, addr = discovery_socket.recvfrom(1024)
                        
                        # Xử lý phản hồi
                        try:
                            response = json.loads(data.decode('utf-8'))
                            
                            if "device_id" in response and "name" in response:
                                device_id = response["device_id"]
                                name = response["name"]
                                ip_address = addr[0]
                                port = response.get("port", 8888)
                                
                                with self.lock:
                                    # Kiểm tra xem thiết bị đã tồn tại chưa
                                    if device_id not in self.devices:
                                        logger.info(f"Discovered new device: {device_id} ({name}) at {ip_address}:{port}")
                                        
                                        # Thêm thiết bị mới
                                        self.add_device(device_id, name, ip_address, port)
                                        self.connect_device(device_id)
                                    elif not self.devices[device_id].connected:
                                        # Kết nối lại thiết bị đã mất kết nối
                                        logger.info(f"Reconnecting to device: {device_id}")
                                        self.connect_device(device_id)
                                        
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid discovery response from {addr}: {data}")
                            
                    except socket.timeout:
                        break
                        
                discovery_socket.close()
                
                # Đợi một khoảng thời gian trước khi khám phá lại
                time.sleep(30.0)
                
            except Exception as e:
                logger.error(f"Error in discovery thread: {e}")
                time.sleep(10.0)
                
        logger.info("Stopped device discovery thread")
        
    def get_device_info(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Get device information.
        
        Args:
            device_id (str): Device ID
            
        Returns:
            Optional[Dict[str, Any]]: Device information or None if not found
        """
        with self.lock:
            if device_id not in self.devices:
                return None
                
            return self.devices[device_id].to_dict()
            
    def get_segment_info(self, segment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get segment information.
        
        Args:
            segment_id (str): Segment ID
            
        Returns:
            Optional[Dict[str, Any]]: Segment information or None if not found
        """
        with self.lock:
            if segment_id not in self.segments:
                return None
                
            return self.segments[segment_id].to_dict()
            
    def get_all_devices(self) -> List[Dict[str, Any]]:
        """
        Get information about all devices.
        
        Returns:
            List[Dict[str, Any]]: List of device information
        """
        with self.lock:
            return [device.to_dict() for device in self.devices.values()]
            
    def get_all_segments(self) -> List[Dict[str, Any]]:
        """
        Get information about all segments.
        
        Returns:
            List[Dict[str, Any]]: List of segment information
        """
        with self.lock:
            return [segment.to_dict() for segment in self.segments.values()]
            
    def get_device_segments(self, device_id: str) -> List[Dict[str, Any]]:
        """
        Get information about segments for a device.
        
        Args:
            device_id (str): Device ID
            
        Returns:
            List[Dict[str, Any]]: List of segment information
        """
        with self.lock:
            return [segment.to_dict() for segment in self.segments.values() if segment.device_id == device_id]
            
    def save_config(self, filename: str) -> bool:
        """
        Save configuration to file.
        
        Args:
            filename (str): Filename
            
        Returns:
            bool: True if saved successfully
        """
        try:
            with self.lock:
                config = {
                    "devices": {device_id: device.to_dict() for device_id, device in self.devices.items()},
                    "segments": {segment_id: segment.to_dict() for segment_id, segment in self.segments.items()}
                }
                
                with open(filename, 'w') as f:
                    json.dump(config, f, indent=2)
                    
                logger.info(f"Saved configuration to {filename}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False
            
    def load_config(self, filename: str) -> bool:
        """
        Load configuration from file.
        
        Args:
            filename (str): Filename
            
        Returns:
            bool: True if loaded successfully
        """
        try:
            with open(filename, 'r') as f:
                config = json.load(f)
                
            with self.lock:
                # Xóa cấu hình hiện tại
                self.stop()
                self.devices.clear()
                self.segments.clear()
                self.device_queues.clear()
                self.worker_threads.clear()
                
                # Tải thiết bị
                for device_id, device_data in config.get("devices", {}).items():
                    device = DeviceInfo.from_dict(device_data)
                    self.devices[device_id] = device
                    self.device_queues[device_id] = queue.Queue()
                    
                # Tải segment
                for segment_id, segment_data in config.get("segments", {}).items():
                    segment = SegmentInfo.from_dict(segment_data)
                    self.segments[segment_id] = segment
                    
                # Khởi động lại device manager
                if self.running:
                    self.start()
                    
                logger.info(f"Loaded configuration from {filename}")
                return True
                
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return False
            
    def get_status(self) -> Dict[str, Any]:
        """
        Get status information.
        
        Returns:
            Dict[str, Any]: Status information
        """
        with self.lock:
            connected_count = sum(1 for device in self.devices.values() if device.connected)
            
            return {
                "devices": len(self.devices),
                "connected_devices": connected_count,
                "segments": len(self.segments),
                "running": self.running
            }