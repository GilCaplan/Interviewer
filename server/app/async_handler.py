# Async and parallel processing for scalability
import asyncio
import threading
import concurrent.futures
from datetime import datetime, timedelta
from queue import Queue, Empty
import time
import logging
from typing import Dict, List, Any, Callable

class AsyncTaskManager:
    """Manages asynchronous and parallel task execution for scalability"""
    
    def __init__(self, max_workers=10):
        self.max_workers = max_workers
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.task_queue = Queue()
        self.active_tasks = {}
        self.completed_tasks = {}
        self.task_counter = 0
        self.worker_thread = None
        self.is_running = False
        
    def start_worker(self):
        """Start the background worker thread"""
        if not self.is_running:
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            logging.info(f"AsyncTaskManager started with {self.max_workers} workers")
    
    def stop_worker(self):
        """Stop the background worker thread"""
        self.is_running = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
        self.thread_pool.shutdown(wait=True)
        logging.info("AsyncTaskManager stopped")
    
    def _worker_loop(self):
        """Main worker loop for processing queued tasks"""
        while self.is_running:
            try:
                # Process queued tasks
                task = self.task_queue.get(timeout=1)
                if task:
                    task_id = task['id']
                    self.active_tasks[task_id] = task
                    
                    # Submit to thread pool
                    future = self.thread_pool.submit(self._execute_task, task)
                    task['future'] = future
                    
            except Empty:
                continue
            except Exception as e:
                logging.error(f"Worker loop error: {e}")
    
    def _execute_task(self, task):
        """Execute a single task"""
        task_id = task['id']
        try:
            start_time = time.time()
            result = task['function'](*task['args'], **task['kwargs'])
            execution_time = time.time() - start_time
            
            # Store result
            self.completed_tasks[task_id] = {
                'result': result,
                'status': 'completed',
                'execution_time': execution_time,
                'completed_at': datetime.utcnow()
            }
            
            # Remove from active tasks
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
                
            return result
            
        except Exception as e:
            # Store error
            self.completed_tasks[task_id] = {
                'error': str(e),
                'status': 'failed',
                'completed_at': datetime.utcnow()
            }
            
            # Remove from active tasks
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
                
            logging.error(f"Task {task_id} failed: {e}")
            return None
    
    def submit_task(self, function: Callable, *args, **kwargs) -> str:
        """Submit a task for async execution"""
        self.task_counter += 1
        task_id = f"task_{self.task_counter}_{int(time.time())}"
        
        task = {
            'id': task_id,
            'function': function,
            'args': args,
            'kwargs': kwargs,
            'submitted_at': datetime.utcnow(),
            'status': 'queued'
        }
        
        self.task_queue.put(task)
        return task_id
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a submitted task"""
        if task_id in self.completed_tasks:
            return self.completed_tasks[task_id]
        elif task_id in self.active_tasks:
            return {'status': 'running', 'started_at': self.active_tasks[task_id]['submitted_at']}
        else:
            return {'status': 'not_found'}
    
    def wait_for_task(self, task_id: str, timeout: int = 30) -> Any:
        """Wait for a task to complete and return result"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_task_status(task_id)
            
            if status['status'] == 'completed':
                return status['result']
            elif status['status'] == 'failed':
                raise Exception(f"Task failed: {status.get('error', 'Unknown error')}")
            
            time.sleep(0.1)
        
        raise TimeoutError(f"Task {task_id} did not complete within {timeout} seconds")
    
    def execute_parallel(self, tasks: List[Dict[str, Any]], max_concurrent: int = None) -> List[Any]:
        """Execute multiple tasks in parallel and return results"""
        if max_concurrent is None:
            max_concurrent = min(len(tasks), self.max_workers)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = []
            
            for task in tasks:
                future = executor.submit(
                    task['function'],
                    *task.get('args', []),
                    **task.get('kwargs', {})
                )
                futures.append(future)
            
            # Wait for all tasks to complete
            results = []
            for future in concurrent.futures.as_completed(futures, timeout=60):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logging.error(f"Parallel task failed: {e}")
                    results.append(None)
            
            return results
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            'active_tasks': len(self.active_tasks),
            'completed_tasks': len(self.completed_tasks),
            'queue_size': self.task_queue.qsize(),
            'max_workers': self.max_workers,
            'is_running': self.is_running,
            'total_tasks_processed': self.task_counter
        }

# Global task manager instance
task_manager = AsyncTaskManager(max_workers=10)

# Utility functions for common async operations
def async_database_operation(operation_func, *args, **kwargs):
    """Execute database operation asynchronously"""
    task_id = task_manager.submit_task(operation_func, *args, **kwargs)
    return task_id

def async_llm_request(llm_func, *args, **kwargs):
    """Execute LLM request asynchronously"""
    task_id = task_manager.submit_task(llm_func, *args, **kwargs)
    return task_id

def parallel_session_operations(session_operations: List[Dict]):
    """Execute multiple session operations in parallel"""
    return task_manager.execute_parallel(session_operations, max_concurrent=5)

def parallel_question_processing(question_operations: List[Dict]):
    """Process multiple questions in parallel"""
    return task_manager.execute_parallel(question_operations, max_concurrent=8)

# Decorator for async execution
def make_async(func):
    """Decorator to make a function execute asynchronously"""
    def wrapper(*args, **kwargs):
        return task_manager.submit_task(func, *args, **kwargs)
    return wrapper

# Context manager for batch operations
class BatchOperationContext:
    """Context manager for executing operations in batches"""
    
    def __init__(self, batch_size=10, max_concurrent=5):
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.operations = []
    
    def add_operation(self, function, *args, **kwargs):
        """Add an operation to the batch"""
        self.operations.append({
            'function': function,
            'args': args,
            'kwargs': kwargs
        })
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Execute all operations in batches
        results = []
        for i in range(0, len(self.operations), self.batch_size):
            batch = self.operations[i:i + self.batch_size]
            batch_results = task_manager.execute_parallel(batch, self.max_concurrent)
            results.extend(batch_results)
        
        return results

# Initialize the task manager
def init_async_manager():
    """Initialize the async task manager"""
    task_manager.start_worker()
    logging.info("Async task manager initialized")

def shutdown_async_manager():
    """Shutdown the async task manager"""
    task_manager.stop_worker()
    logging.info("Async task manager shutdown")