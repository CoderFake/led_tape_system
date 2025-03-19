import threading
import time
import heapq
import logging
from typing import Dict, List, Callable, Any, Tuple, Set
from enum import Enum

logger = logging.getLogger(__name__)


class Priority(Enum):
    HIGH = 0
    NORMAL = 1
    LOW = 2
    BACKGROUND = 3


class Task:
    """
    Represents a scheduled task.
    """
    
    def __init__(self, task_id: str, func: Callable, args: Tuple = None, 
                 kwargs: Dict = None, priority: Priority = Priority.NORMAL,
                 interval: float = None):
        """
        Initialize a task.
        
        Args:
            task_id (str): Unique identifier for the task
            func (Callable): Function to execute
            args (Tuple): Positional arguments for the function
            kwargs (Dict): Keyword arguments for the function
            priority (Priority): Task priority
            interval (float): Execution interval for recurring tasks (None for one-time tasks)
        """
        self.task_id = task_id
        self.func = func
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.priority = priority
        self.interval = interval
        self.next_run = time.time()
        self.last_run = None
        self.execution_count = 0
        self.total_execution_time = 0
        self.is_cancelled = False
        
    def execute(self):
        """
        Execute the task and update statistics.
        
        Returns:
            Any: The result of the function
        """
        if self.is_cancelled:
            return None
            
        start_time = time.time()
        self.last_run = start_time
        
        try:
            result = self.func(*self.args, **self.kwargs)
        except Exception as e:
            logger.error(f"Error executing task {self.task_id}: {e}")
            result = None
            
        execution_time = time.time() - start_time
        self.execution_count += 1
        self.total_execution_time += execution_time
        
        if self.interval is not None and not self.is_cancelled:
            self.next_run = time.time() + self.interval
            
        return result
        
    def cancel(self):
        """
        Cancel the task.
        """
        self.is_cancelled = True
        
    def __lt__(self, other):
        """
        Compare tasks for priority queue.
        First by next_run time, then by priority.
        """
        if self.next_run != other.next_run:
            return self.next_run < other.next_run
        return self.priority.value < other.priority.value


class Scheduler:
    """
    Scheduler for managing and executing tasks.
    """
    
    def __init__(self, max_workers: int = 4):
        """
        Initialize the scheduler.
        
        Args:
            max_workers (int): Maximum number of worker threads
        """
        self.tasks: Dict[str, Task] = {}
        self.task_queue: List[Task] = []
        self.lock = threading.RLock()
        self.running = False
        self.scheduler_thread = None
        self.worker_threads = []
        self.max_workers = max_workers
        self.worker_semaphore = threading.Semaphore(max_workers)
        self.active_tasks: Set[str] = set()
        
    def schedule(self, task_id: str, func: Callable, args: Tuple = None, 
                 kwargs: Dict = None, priority: Priority = Priority.NORMAL,
                 interval: float = None, delay: float = 0) -> str:
        """
        Schedule a task for execution.
        
        Args:
            task_id (str): Unique identifier for the task
            func (Callable): Function to execute
            args (Tuple): Positional arguments for the function
            kwargs (Dict): Keyword arguments for the function
            priority (Priority): Task priority
            interval (float): Execution interval for recurring tasks (None for one-time tasks)
            delay (float): Initial delay before first execution
            
        Returns:
            str: Task ID
        """
        with self.lock:
            if task_id in self.tasks:
                self.cancel(task_id)
                
            task = Task(task_id, func, args, kwargs, priority, interval)
            task.next_run = time.time() + delay
   
            self.tasks[task_id] = task
            heapq.heappush(self.task_queue, task)

            logger.debug(f"Scheduled task {task_id} with priority {priority.name}")
            
            return task_id
            
    def cancel(self, task_id: str) -> bool:
        """
        Cancel a scheduled task.
        
        Args:
            task_id (str): ID of the task to cancel
            
        Returns:
            bool: True if cancelled, False if not found
        """
        with self.lock:
            if task_id not in self.tasks:
                return False

            self.tasks[task_id].cancel()
            
            logger.debug(f"Cancelled task {task_id}")
            return True
            
    def cancel_all(self):
        """
        Cancel all scheduled tasks.
        """
        with self.lock:
            for task_id in list(self.tasks.keys()):
                self.cancel(task_id)
                
            logger.debug("Cancelled all tasks")
            
    def start(self):
        """
        Start the scheduler.
        """
        if self.running:
            return
            
        self.running = True

        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        logger.info(f"Started scheduler with {self.max_workers} workers")
        
    def stop(self):
        """
        Stop the scheduler.
        """
        if not self.running:
            return
            
        self.running = False
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=1.0)
            
        for thread in self.worker_threads[:]:
            if thread.is_alive():
                thread.join(timeout=0.5)
                
        self.worker_threads = []
        
        logger.info("Stopped scheduler")
        
    def _scheduler_loop(self):
        """
        Main scheduler loop.
        """
        while self.running:
            self._process_due_tasks()
            time.sleep(0.01)
            
    def _process_due_tasks(self):
        """
        Process tasks that are due for execution.
        """
        current_time = time.time()
        
        while self.running:
            with self.lock:
                if not self.task_queue:
                    break

                next_task = self.task_queue[0]

                if next_task.next_run > current_time:
                    break

                task = heapq.heappop(self.task_queue)

                if task.is_cancelled:
                    continue

                self.active_tasks.add(task.task_id)

            self._execute_in_worker(task)
            
    def _execute_in_worker(self, task: Task):
        """
        Execute a task in a worker thread.
        
        Args:
            task (Task): The task to execute
        """
        def worker():
            with self.worker_semaphore:
                task.execute()
                
                with self.lock:
                    self.active_tasks.discard(task.task_id)

                    if task.interval is not None and not task.is_cancelled:
                        heapq.heappush(self.task_queue, task)
                    else:
                        self.tasks.pop(task.task_id, None)
            

            with self.lock:
                if thread in self.worker_threads:
                    self.worker_threads.remove(thread)

        thread = threading.Thread(target=worker, daemon=True)
        
        with self.lock:
            self.worker_threads.append(thread)
            
        thread.start()
        
    def get_status(self) -> Dict[str, Any]:
        """
        Get scheduler status.
        
        Returns:
            Dict[str, Any]: Scheduler status
        """
        with self.lock:
            return {
                "queued_tasks": len(self.task_queue),
                "active_tasks": len(self.active_tasks),
                "total_tasks": len(self.tasks),
                "workers": self.max_workers,
                "worker_threads": len(self.worker_threads),
                "running": self.running
            }