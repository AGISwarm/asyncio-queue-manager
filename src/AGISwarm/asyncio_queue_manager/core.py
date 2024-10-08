"""Main.py"""

import asyncio
import logging
import traceback
from collections.abc import AsyncGenerator, Callable
from enum import Enum
from functools import wraps
from typing import Any, Dict, List, Optional, Protocol, TypedDict, cast

import ulid

from .thread_safe_sorted_list import ThreadSafeSortedList


class TaskStatus(str, Enum):
    """Task status"""

    STARTING = "starting"
    WAITING = "waiting"
    RUNNING = "running"
    FINISHED = "finished"
    ABORTED = "aborted"
    ERROR = "error"
    WARNING = "warning"


class TaskResponse(TypedDict):
    """Task response"""

    task_id: str
    status: TaskStatus
    content: Optional[str | Dict[str, Any]]


# pylint: disable=too-few-public-methods
class QueuedTask(Protocol):
    """Queued generator protocol"""

    task_id: str

    def __call__(self, *args, **kwargs) -> AsyncGenerator[Dict, None]: ...


class AsyncIOQueueManager:
    """
    Class to manage the queue of generation requests

    Args:
        max_concurrent_tasks (int, optional):
            Maximum number of concurrent tasks. Defaults to 1.
        sleep_time (float, optional):
            Time to sleep between checks. Defaults to 0.01.
    """

    def __init__(
        self,
        max_concurrent_tasks: int = 1,
        sleep_time: float = .0,
    ):
        self.queue = ThreadSafeSortedList()
        self.abort_map: Dict[str, asyncio.Event] = {}
        self.max_concurrent_tasks = max_concurrent_tasks
        self.sleep_time = sleep_time

    # pylint: disable=too-many-arguments
    def queued_task(
        self,
        func: Callable,
        task_id: Optional[str] = None,
        pass_task_id: bool = False,
        warnings: Optional[List[str]] = None,
        raise_on_error: bool = False,
        print_error_tracebacks: bool = True,
    ):
        """Decorator for generation requests"""

        if task_id is None:
            task_id = self.make_task_id()

        @wraps(func)
        async def wrapper(*args, **kwargs):
            self.queue.add(task_id)
            yield self._starting_response(task_id)
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
                for warning in warnings or []:
                    yield self._warning_response(task_id, warning)
                if pass_task_id:
                    kwargs["task_id"] = task_id
                output = func(*args, **kwargs)
                if isinstance(output, AsyncGenerator):
                    async for response in output:
                        await asyncio.sleep(self.sleep_time)
                        yield self._running_response(task_id, response)
                        if self.abort_map[task_id].is_set():
                            yield self._abort_response(task_id)
                            return
                else:
                    yield self._running_response(task_id, output)
                yield self._finished_response(task_id)
            except asyncio.CancelledError:
                yield self._abort_response(task_id)
            except Exception as e:  # pylint: disable=broad-except
                if raise_on_error:
                    raise e
                if print_error_tracebacks:
                    traceback.print_exc()
                logging.error("Error in queued task", exc_info=e)
                yield self._error_response(task_id, str(e))
            finally:
                self.queue.remove(task_id)
                self.abort_map.pop(task_id)

        generator: QueuedTask = cast(QueuedTask, wrapper)
        generator.task_id = task_id

        return generator

    async def abort_task(self, task_id: str) -> None:
        """Abort task"""
        if task_id not in self.abort_map:
            self.abort_map[task_id] = asyncio.Event()
        self.abort_map[task_id].set()

    def make_task_id(self):
        """Reserve a task ID"""
        task_id = str(len(self.queue)) + ulid.new().str
        if task_id not in self.abort_map:
            self.abort_map[task_id] = asyncio.Event()
        return task_id

    def _waiting_response(self, task_id: str):
        """Waiting response"""
        index = self.queue.index(task_id)
        return TaskResponse(
            {
                "task_id": task_id,
                "status": TaskStatus.WAITING,
                "content": {
                    "queue_pos": index,
                    "queue_len": len(self.queue),
                },
            }
        )

    def _abort_response(self, task_id: str):
        """Abort response"""
        return TaskResponse(
            {"task_id": task_id, "status": TaskStatus.ABORTED, "content": None}
        )

    def _error_response(self, task_id: str, error: str):
        """Error response"""
        return TaskResponse(
            {"task_id": task_id, "status": TaskStatus.ERROR, "content": error}
        )

    def _finished_response(self, task_id: str):
        """Finished response"""
        return TaskResponse(
            {"task_id": task_id, "status": TaskStatus.FINISHED, "content": None}
        )

    def _running_response(self, task_id: str, content: str | Dict[str, Any]):
        """Running response"""
        return TaskResponse(
            {"task_id": task_id, "status": TaskStatus.RUNNING, "content": content}
        )

    def _starting_response(self, task_id: str):
        """Starting response"""
        return TaskResponse(
            {"task_id": task_id, "status": TaskStatus.STARTING, "content": None}
        )

    def _warning_response(self, task_id: str, warning: str):
        """Warning response"""
        return TaskResponse(
            {"task_id": task_id, "status": TaskStatus.WARNING, "content": warning}
        )
