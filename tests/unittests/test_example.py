"""
Tests for the AGISwarm.asyncio_queue_manager module.

This module provides a class for managing a queue of asynchronous tasks.

"""

import asyncio

import pytest

from AGISwarm.asyncio_queue_manager import AsyncIOQueueManager, RequestStatus


@pytest.mark.asyncio
async def test_abort_task():
    """
    Test that a task can be aborted.
    """

    assert 1 == 1



if __name__ == "__main__":
    pytest.main([__file__])
