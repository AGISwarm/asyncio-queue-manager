"""Main.py"""

import asyncio
import logging
from enum import Enum
from functools import wraps
from typing import Callable, Dict

import ulid
from sortedcontainers import SortedSet


class RequestStatus(Enum):
    """Request status"""

    WAITING = "waiting"
    RUNNING = "running"
    FINISHED = "finished"
    ABORTED = "abort"


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

    def abort_task(self, request_ulid: str):
        """Abort request"""
        if request_ulid in self.abort_map:
            self.abort_map[request_ulid].set()

    def enqueue_task(self, func: Callable):
        """Decorator for generation requests"""

        def waiting_response(request_ulid: str):
            """Waiting response"""
            index = self.queue.index(request_ulid)
            return {
                "request_id": request_ulid,
                "status": RequestStatus.WAITING,
                "queue_pos": index,
                "queue_len": len(self.queue),
            }

        def abort_response(request_ulid: str):
            """Abort response"""
            return {"request_id": request_ulid, "status": RequestStatus.ABORTED}

        def finished_response(request_ulid: str):
            """Finished response"""
            return {"request_id": request_ulid, "status": RequestStatus.FINISHED}

        @wraps(func)
        async def wrapper(*args, **kwargs):
            request_ulid = str(len(self.queue)) + ulid.new().str
            self.queue.add(request_ulid)
            self.abort_map[request_ulid] = asyncio.Event()
            try:
                while (
                    self.queue[0] != request_ulid
                    and len(self.queue) > self.max_concurrent_requests
                ):
                    await asyncio.sleep(self.sleep_time)
                    if self.abort_map[request_ulid].is_set():
                        yield abort_response(request_ulid)
                        return
                    yield waiting_response(request_ulid)
                async for response in func(*args, **kwargs):
                    if self.abort_map[request_ulid].is_set():
                        yield abort_response(request_ulid)
                        return
                    yield response
                yield finished_response(request_ulid)
            except asyncio.CancelledError as e:
                logging.error(e)
            finally:
                self.queue.remove(request_ulid)
                self.abort_map[request_ulid].clear()
                self.abort_map.pop(request_ulid)

        return wrapper
