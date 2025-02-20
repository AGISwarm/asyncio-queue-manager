"""__init__.py
"""

from importlib.metadata import version

from .core import AsyncIOQueueManager, TaskStatus

__version__ = version("AGISwarm.asyncio_queue_manager")
