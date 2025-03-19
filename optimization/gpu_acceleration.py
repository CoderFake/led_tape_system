import numpy as np
import logging
from typing import List, Dict, Tuple, Optional, Any, Union
import threading
import time

try:
    import numba
    from numba import cuda
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False

try:
    import pyopencl as cl
    OPENCL_AVAILABLE = True
except ImportError:
    OPENCL_AVAILABLE = False

logger = logging.getLogger(__name__)


class GPUAccelerator:
    """
    Base class for GPU acceleration.
    """
    
    def __init__(self):
        """
        Initialize the GPU accelerator.
        """
        self.enabled = False
        self.device_info = "No GPU acceleration available"
        
    def is_available(self) -> bool:
        """
        Check if GPU acceleration is available.
        
        Returns:
            bool: True if available, False otherwise
        """
        return self.enabled
        
    def get_device_info(self) -> str:
        """
        Get information about the GPU device.
        
        Returns:
            str: Device information
        """
        return self.device_info
        
    def accelerate_led_calculation(self, positions: np.ndarray, colors: np.ndarray, 
                                 transparencies: np.ndarray) -> np.ndarray:
        """
        Accelerate LED calculation using GPU.
        
        Args:
            positions (np.ndarray): LED positions (N, 2) array
            colors (np.ndarray): RGB colors (M, 3) array
            transparencies (np.ndarray): Transparency values (M,) array
            
        Returns:
            np.ndarray: Calculated LED colors (N, 3) array
        """
        result = np.zeros((positions.shape[0], 3), dtype=np.uint8)
        return result


class CudaAccelerator(GPUAccelerator):
    """
    GPU acceleration using CUDA via Numba.
    """
    
    def __init__(self):
        """
        Initialize the CUDA accelerator.
        """
        super().__init__()
        
        if not NUMBA_AVAILABLE:
            logger.warning("Numba/CUDA not available, CUDA acceleration disabled")
            return
            
        try:
            if not cuda.is_available():
                logger.warning("CUDA device not available")
                return
                
            device = cuda.get_current_device()
            self.device_info = f"CUDA Device: {device.name} (Compute {device.compute_capability[0]}.{device.compute_capability[1]})"
            
            self._init_cuda_functions()
            
            self.enabled = True
            logger.info(f"CUDA acceleration enabled: {self.device_info}")
            
        except Exception as e:
            logger.error(f"Error initializing CUDA: {e}")
            
    def _init_cuda_functions(self):
        """
        Initialize CUDA functions.
        """
        if not self.enabled:
            return
            
        @cuda.jit
        def calculate_led_colors_kernel(positions, colors, transparencies, result):
            """
            CUDA kernel for calculating LED colors.
            
            Args:
                positions (np.ndarray): LED positions (N, 2) array
                colors (np.ndarray): RGB colors (M, 3) array
                transparencies (np.ndarray): Transparency values (M,) array
                result (np.ndarray): Output array for LED colors (N, 3)
            """
            i = cuda.grid(1)
            
            if i >= positions.shape[0]:
                return
                
            r, g, b = 0.0, 0.0, 0.0
            total_opacity = 0.0
            
            for j in range(colors.shape[0]):
                dx = positions[i, 0] - positions[j, 0]
                dy = positions[i, 1] - positions[j, 1]
                distance_sq = dx * dx + dy * dy
                
                falloff = 1.0 / (1.0 + distance_sq)
                
                opacity = (1.0 - transparencies[j]) * falloff
              
                r += colors[j, 0] * opacity
                g += colors[j, 1] * opacity
                b += colors[j, 2] * opacity
                
                total_opacity += opacity

            if total_opacity > 0.0:
                r /= total_opacity
                g /= total_opacity
                b /= total_opacity

            result[i, 0] = min(255, max(0, int(r)))
            result[i, 1] = min(255, max(0, int(g)))
            result[i, 2] = min(255, max(0, int(b)))
            
        self.calculate_led_colors_kernel = calculate_led_colors_kernel
        
    def accelerate_led_calculation(self, positions: np.ndarray, colors: np.ndarray, 
                                 transparencies: np.ndarray) -> np.ndarray:
        """
        Accelerate LED calculation using CUDA.
        
        Args:
            positions (np.ndarray): LED positions (N, 2) array
            colors (np.ndarray): RGB colors (M, 3) array
            transparencies (np.ndarray): Transparency values (M,) array
            
        Returns:
            np.ndarray: Calculated LED colors (N, 3) array
        """
        if not self.enabled:
            return super().accelerate_led_calculation(positions, colors, transparencies)
            
        try:
            d_positions = cuda.to_device(positions)
            d_colors = cuda.to_device(colors)
            d_transparencies = cuda.to_device(transparencies)
            
            result = np.zeros((positions.shape[0], 3), dtype=np.uint8)
            d_result = cuda.to_device(result)
            
            threads_per_block = 256
            blocks_per_grid = (positions.shape[0] + threads_per_block - 1) // threads_per_block

            self.calculate_led_colors_kernel[blocks_per_grid, threads_per_block](
                d_positions, d_colors, d_transparencies, d_result
            )
            
            d_result.copy_to_host(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in CUDA acceleration: {e}")
            return super().accelerate_led_calculation(positions, colors, transparencies)


class OpenCLAccelerator(GPUAccelerator):
    """
    GPU acceleration using OpenCL.
    """
    
    def __init__(self):
        """
        Initialize the OpenCL accelerator.
        """
        super().__init__()
        
        if not OPENCL_AVAILABLE:
            logger.warning("PyOpenCL not available, OpenCL acceleration disabled")
            return
            
        try:
            platforms = cl.get_platforms()
            if not platforms:
                logger.warning("No OpenCL platforms found")
                return

            devices = []
            for platform in platforms:
                try:
                    devices.extend(platform.get_devices(device_type=cl.device_type.GPU))
                except:
                    pass
                    
            if not devices:
                logger.warning("No OpenCL GPU devices found")
                return
                
            self.device = devices[0]
            self.device_info = f"OpenCL Device: {self.device.name} ({self.device.version})"
            
            self.context = cl.Context([self.device])
            self.queue = cl.CommandQueue(self.context)

            self._compile_program()
            
            self.enabled = True
            logger.info(f"OpenCL acceleration enabled: {self.device_info}")
            
        except Exception as e:
            logger.error(f"Error initializing OpenCL: {e}")
            
    def _compile_program(self):
        """
        Compile OpenCL program.
        """
        if not self.enabled:
            return

        kernel_src = """
        __kernel void calculate_led_colors(
            __global const float2 *positions,
            __global const uchar3 *colors,
            __global const float *transparencies,
            __global uchar3 *result,
            const int num_positions,
            const int num_colors
        ) {
            // Get global ID
            int i = get_global_id(0);
            
            // Check bounds
            if (i >= num_positions) {
                return;
            }
            
            // Initialize result
            float3 color_sum = (float3)(0.0f, 0.0f, 0.0f);
            float total_opacity = 0.0f;
            
            // Process each color
            for (int j = 0; j < num_colors; j++) {
                // Calculate distance
                float dx = positions[i].x - positions[j].x;
                float dy = positions[i].y - positions[j].y;
                float distance_sq = dx * dx + dy * dy;
                
                // Apply falloff based on distance
                float falloff = 1.0f / (1.0f + distance_sq);
                
                // Calculate opacity
                float opacity = (1.0f - transparencies[j]) * falloff;
                
                // Accumulate colors with opacity
                color_sum.x += colors[j].x * opacity;
                color_sum.y += colors[j].y * opacity;
                color_sum.z += colors[j].z * opacity;
                
                total_opacity += opacity;
            }
            
            // Normalize by total opacity
            if (total_opacity > 0.0f) {
                color_sum.x /= total_opacity;
                color_sum.y /= total_opacity;
                color_sum.z /= total_opacity;
            }
            
            // Store result
            result[i].x = (uchar)clamp(color_sum.x, 0.0f, 255.0f);
            result[i].y = (uchar)clamp(color_sum.y, 0.0f, 255.0f);
            result[i].z = (uchar)clamp(color_sum.z, 0.0f, 255.0f);
        }
        """
        
        try:
            self.program = cl.Program(self.context, kernel_src).build()
            self.kernel = self.program.calculate_led_colors
            
        except Exception as e:
            logger.error(f"Error compiling OpenCL program: {e}")
            self.enabled = False
            
    def accelerate_led_calculation(self, positions: np.ndarray, colors: np.ndarray, 
                                 transparencies: np.ndarray) -> np.ndarray:
        """
        Accelerate LED calculation using OpenCL.
        
        Args:
            positions (np.ndarray): LED positions (N, 2) array
            colors (np.ndarray): RGB colors (M, 3) array
            transparencies (np.ndarray): Transparency values (M,) array
            
        Returns:
            np.ndarray: Calculated LED colors (N, 3) array
        """
        if not self.enabled:
            return super().accelerate_led_calculation(positions, colors, transparencies)
            
        try:
            positions_f = positions.astype(np.float32)
            colors_u = colors.astype(np.uint8)
            transparencies_f = transparencies.astype(np.float32)

            positions_buf = cl.Buffer(self.context, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=positions_f)
            colors_buf = cl.Buffer(self.context, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=colors_u)
            transparencies_buf = cl.Buffer(self.context, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=transparencies_f)

            result = np.zeros((positions.shape[0], 3), dtype=np.uint8)
            result_buf = cl.Buffer(self.context, cl.mem_flags.WRITE_ONLY, result.nbytes)

            self.kernel.set_args(
                positions_buf, colors_buf, transparencies_buf, result_buf,
                np.int32(positions.shape[0]), np.int32(colors.shape[0])
            )

            global_size = (positions.shape[0],)
            local_size = None 
            
            cl.enqueue_nd_range_kernel(self.queue, self.kernel, global_size, local_size)

            cl.enqueue_copy(self.queue, result, result_buf)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in OpenCL acceleration: {e}")
            return super().accelerate_led_calculation(positions, colors, transparencies)


def get_accelerator() -> GPUAccelerator:
    """
    Get the best available GPU accelerator.
    
    Returns:
        GPUAccelerator: GPU accelerator instance
    """
    if NUMBA_AVAILABLE:
        accelerator = CudaAccelerator()
        if accelerator.is_available():
            return accelerator

    if OPENCL_AVAILABLE:
        accelerator = OpenCLAccelerator()
        if accelerator.is_available():
            return accelerator
            
    logger.warning("No GPU acceleration available, using CPU implementation")
    return GPUAccelerator()