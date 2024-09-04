"""Main.py"""

import asyncio
import logging
from enum import Enum
from functools import wraps
from typing import AsyncGenerator, Callable, Dict, Protocol, cast

import ulid

from .thread_safe_sorted_list import ThreadSafeSortedList as SortedSet


class RequestStatus(str, Enum):
    """Request status"""

    WAITING = "waiting"
    RUNNING = "running"
    FINISHED = "finished"
    ABORTED = "aborted"
    ERROR = "error"


# pylint: disable=too-few-public-methods
class QueuedFunction(Protocol):
    """Queued function protocol"""

    request_id: str

    def __call__(self, *args, **kwargs): ...


class QueuedGenerator(Protocol):
    """Queued generator protocol"""

    request_id: str

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
        max_concurrent_requests: int = 1,
        sleep_time: float = 0.01,
    ):
        self.queue = SortedSet()
        self.abort_map: Dict[str, asyncio.Event] = {}
        self.max_concurrent_requests = max_concurrent_requests
        self.sleep_time = sleep_time

    async def abort_task(self, request_id: str) -> None:
        """Abort request"""
        if request_id in self.abort_map:
            self.abort_map[request_id].set()

    def queued_coroutine(self, func: Callable):
        """Decorator for coroutine functions to be queued"""

        request_id = str(len(self.queue)) + ulid.new().str

        @wraps(func)
        async def wrapper(*args, **kwargs):
            self.queue.add(request_id)
            self.abort_map[request_id] = asyncio.Event()
            try:
                while (
                    self.queue[0] != request_id
                    and len(self.queue) > self.max_concurrent_requests
                ):
                    await asyncio.sleep(self.sleep_time)
                    if self.abort_map[request_id].is_set():
                        return None
                return await func(request_id=request_id, *args, **kwargs)
            except asyncio.CancelledError as e:
                logging.error(e)
            finally:
                self.queue.remove(request_id)
                self.abort_map.pop(request_id)

        coroutine: QueuedFunction = cast(QueuedFunction, wrapper)
        coroutine.request_id = request_id

        return coroutine

    def queued_generator(self, func: Callable):
        """Decorator for generation requests"""

        request_id = str(len(self.queue)) + ulid.new().str
        self.abort_map[request_id] = asyncio.Event()

        def __waiting_response():
            """Waiting response"""
            index = self.queue.index(request_id)
            return {
                "request_id": request_id,
                "status": RequestStatus.WAITING,
                "queue_pos": index,
                "queue_len": len(self.queue),
            }

        def __abort_response():
            """Abort response"""
            return {"request_id": request_id, "status": RequestStatus.ABORTED}

        def __finished_response():
            """Finished response"""
            return {"request_id": request_id, "status": RequestStatus.FINISHED}

        @wraps(func)
        async def wrapper(*args, **kwargs):
            self.queue.add(request_id)
            try:
                while (
                    self.queue[0] != request_id
                    and len(self.queue) > self.max_concurrent_requests
                ):
                    await asyncio.sleep(self.sleep_time)
                    if self.abort_map[request_id].is_set():
                        yield __abort_response()
                        return
                    yield __waiting_response()
                async for response in func(*args, **kwargs):
                    yield response
                    if self.abort_map[request_id].is_set():
                        yield __abort_response()
                        return
                yield __finished_response()
            except asyncio.CancelledError as e:
                logging.error(e)
            finally:
                self.queue.remove(request_id)
                self.abort_map.pop(request_id)

        generator: QueuedGenerator = cast(QueuedGenerator, wrapper)
        generator.request_id = request_id

        return generator
