"""Main.py"""

import asyncio
import logging
from enum import Enum
from functools import wraps
from typing import AsyncGenerator, Callable, Dict, Optional, Protocol, cast

import ulid

from .thread_safe_sorted_list import ThreadSafeSortedList as SortedSet


class TaskStatus(str, Enum):
    """Request status"""

    STARTING = "starting"
    WAITING = "waiting"
    RUNNING = "running"
    FINISHED = "finished"
    ABORTED = "aborted"
    ERROR = "error"


# pylint: disable=too-few-public-methods
class QueuedTask(Protocol):
    """Queued generator protocol"""

    task_id: str

    def __call__(self, *args, **kwargs) -> AsyncGenerator[Dict, None]: ...


class AsyncIOQueueManager:
    """
    Class to manage the queue of generation requests

    Args:
        abort_response (Optional[Dict], optional):
            Response when request is aborted. Defaults to None.
        max_concurrent_requests (int, optional):
            Maximum number of concurrent requests. Defaults to 1.
    """

    def __init__(
        self,
        max_concurrent_tasks: int = 1,
        sleep_time: float = 0.01,
    ):
        self.queue = SortedSet()
        self.abort_map: Dict[str, asyncio.Event] = {}
        self.max_concurrent_tasks = max_concurrent_tasks
        self.sleep_time = sleep_time

    def _waiting_response(self, task_id: str):
        """Waiting response"""
        index = self.queue.index(task_id)
        return {
            "task_id": task_id,
            "status": TaskStatus.WAITING,
            "queue_pos": index,
            "queue_len": len(self.queue),
        }

    def _abort_response(self, task_id: str):
        """Abort response"""
        return {"task_id": task_id, "status": TaskStatus.ABORTED}

    async def abort_task(self, task_id: str) -> None:
        """Abort request"""
        if task_id not in self.abort_map:
            self.abort_map[task_id] = asyncio.Event()
        self.abort_map[task_id].set()

    def make_request_id(self):
        """Reserve a request ID"""
        task_id = str(len(self.queue)) + ulid.new().str
        if task_id not in self.abort_map:
            self.abort_map[task_id] = asyncio.Event()
        return task_id

    def queued_task(self, func: Callable, task_id: Optional[str] = None):
        """Decorator for coroutine functions to be queued"""

        if task_id is None:
            task_id = self.make_request_id()

        @wraps(func)
        async def wrapper(*args, **kwargs):
            self.queue.add(task_id)
            try:
                while (
                    self.queue[0] != task_id
                    and len(self.queue) > self.max_concurrent_tasks
                ):
                    await asyncio.sleep(self.sleep_time)
                    if self.abort_map[task_id].is_set():
                        yield self._abort_response(task_id)
                        return
                    yield self._waiting_response(task_id)
                yield func(*args, **kwargs)
            except asyncio.CancelledError:
                yield self._abort_response(task_id)
            except Exception as e:  # pylint: disable=broad-except
                logging.error(e)
                yield {"task_id": task_id, "status": TaskStatus.ERROR}
            finally:
                self.queue.remove(task_id)
                self.abort_map.pop(task_id)

        coroutine: QueuedTask = cast(QueuedTask, wrapper)
        coroutine.task_id = task_id

        return coroutine

    def queued_generator(self, func: Callable, task_id: Optional[str] = None):
        """Decorator for generation requests"""

        if task_id is None:
            task_id = self.make_request_id()

        @wraps(func)
        async def wrapper(*args, **kwargs):
            self.queue.add(task_id)
            try:
                while (
                    self.queue[0] != task_id
                    and len(self.queue) > self.max_concurrent_tasks
                ):
                    await asyncio.sleep(self.sleep_time)
                    if self.abort_map[task_id].is_set():
                        yield self._abort_response(task_id)
                        return
                    yield self._waiting_response(task_id)
                async for response in func(*args, **kwargs):
                    yield response
                    if self.abort_map[task_id].is_set():
                        yield self._abort_response(task_id)
                        return
            except asyncio.CancelledError as e:
                logging.error(e)
                yield self._abort_response(task_id)
            except Exception as e:  # pylint: disable=broad-except
                logging.error(e)
                yield {"task_id": task_id, "status": TaskStatus.ERROR}
            finally:
                self.queue.remove(task_id)
                self.abort_map.pop(task_id)

        generator: QueuedTask = cast(QueuedTask, wrapper)
        generator.task_id = task_id

        return generator
