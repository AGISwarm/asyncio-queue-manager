"""
Tests for the AGISwarm.asyncio_queue_manager module.

This module provides a class for managing a queue of asynchronous tasks.

"""

import asyncio

import pytest

from AGISwarm.asyncio_queue_manager import AsyncIOQueueManager, RequestStatus


@pytest.mark.asyncio
async def test_enqueue_and_execute():
    """
    Test that a task is enqueued and executed.
    """

    manager = AsyncIOQueueManager(max_concurrent_requests=2)
    results = []

    @manager.enqueue_task
    async def task(number):
        await asyncio.sleep(1)
        yield {"status": RequestStatus.RUNNING, "result": number}

    async def run_task(number):
        async for response in task(number):
            if response["status"] == RequestStatus.RUNNING:
                results.append(response["result"])

    await asyncio.gather(run_task(1), run_task(2), run_task(3))

    assert results == [1, 2, 3]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ["max_concurrent_requests", "num_tasks"],
    [
        (1, 2),
        (1, 3),
        (1, 4),
    ],
)
async def test_max_concurrent_requests(max_concurrent_requests, num_tasks):
    """
    Test that the queue manager respects the maximum number of concurrent requests.
    """

    manager = AsyncIOQueueManager(max_concurrent_requests=max_concurrent_requests)
    execution_order = []

    @manager.enqueue_task
    async def task(number):
        await asyncio.sleep(1)
        yield {"status": RequestStatus.RUNNING, "result": number}

    async def run_task(number):
        async for response in task(number):
            if response["status"] == RequestStatus.FINISHED:
                execution_order.append(number)

    await asyncio.gather(*[run_task(i) for i in range(num_tasks)])

    assert execution_order == list(range(num_tasks))


@pytest.mark.asyncio
async def test_abort_task():
    """
    Test that a task can be aborted.
    """

    manager = AsyncIOQueueManager(max_concurrent_requests=1)
    results = []

    @manager.enqueue_task
    async def task(number):
        await asyncio.sleep(1)
        yield {"status": RequestStatus.RUNNING, "result": number}

    async def run_task(number):
        async for response in task(number):
            results.append(response["status"])

    task1 = asyncio.create_task(run_task(1))
    task2 = asyncio.create_task(run_task(2))

    await asyncio.sleep(0.1)
    manager.abort_task(manager.queue[1])

    await task1
    await task2

    assert RequestStatus.ABORTED in results
    assert results.count(RequestStatus.RUNNING) == 1


if __name__ == "__main__":
    pytest.main([__file__])
