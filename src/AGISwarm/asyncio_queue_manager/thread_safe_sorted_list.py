"""
Thread safe sorted list implementation.
"""

from threading import Lock
from typing import Any, List, Optional

from sortedcontainers import SortedList


class ThreadSafeSortedList(SortedList):
    """
    Thread safe sorted list implementation.

    Args:
        iterable (Optional[List[Any]], optional):
            Initial list. Defaults to None.
    """

    def __init__(self, iterable: Optional[List[Any]] = None):
        super().__init__(iterable)
        self.lock = Lock()

    def add(self, value: Any) -> None:
        """
        Add a value to the list.

        Args:
            value (Any): Value to add.
        """
        with self.lock:
            super().add(value)

    def remove(self, value: Any) -> None:
        """
        Remove a value from the list.

        Args:
            value (Any): Value to remove.
        """
        with self.lock:
            super().remove(value)

    def pop(self, index: int = -1) -> Any:
        """
        Pop a value from the list.

        Args:
            index (int, optional): Index to pop. Defaults to -1.

        Returns:
            Any: Popped value.
        """
        with self.lock:
            return super().pop(index)

    def append(self, value):
        """
        Append a value to the list.

        Args:
            value (Any): Value to append.
        """

        with self.lock:
            super().append(value)

    def extend(self, values):
        """
        Extend the list with values.

        Args:
            values (List[Any]): Values to extend the list with.
        """

        with self.lock:
            super().extend(values)

    def insert(self, index, value):
        """
        Insert a value at an index.

        Args:
            index (int): Index to insert at.
            value (Any): Value to insert.
        """

        with self.lock:
            super().insert(index, value)

    def reverse(self):
        """
        Reverse the list.
        """

        with self.lock:
            super().reverse()

    def __getitem__(self, index: int) -> Any:
        """
        Get an item at an index.

        Args:
            index (int): Index to get.

        Returns:
            Any: Item at index.
        """

        with self.lock:
            return super().__getitem__(index)

    def __setitem__(self, index: int, value: Any) -> None:
        """
        Set an item at an index.

        Args:
            index (int): Index to set.
            value (Any): Value to set.
        """

        with self.lock:
            super().__setitem__(index, value)

    def __delitem__(self, index: int) -> None:
        """
        Delete an item at an index.

        Args:
            index (int): Index to delete.
        """

        with self.lock:
            super().__delitem__(index)

    def __iter__(self):
        """
        Get an iterator for the list.

        Returns:
            Iterator: Iterator for the list.
        """

        with self.lock:
            return super().__iter__()

    def __reversed__(self):
        """
        Get a reversed iterator for the list.

        Returns:
            Iterator: Reversed iterator for the list.
        """

        with self.lock:
            return super().__reversed__()

    def __contains__(self, value: Any) -> bool:
        """
        Check if a value is in the list.

        Args:
            value (Any): Value to check.

        Returns:
            bool: True if value is in the list, False otherwise.
        """

        with self.lock:
            return super().__contains__(value)

    def __len__(self) -> int:
        """
        Get the length of the list.

        Returns:
            int: Length of the list.
        """

        with self.lock:
            return super().__len__()

    def __str__(self) -> str:
        """
        Get a string representation of the list.

        Returns:
            str: String representation of the list.
        """

        with self.lock:
            return super().__str__()

    def __repr__(self) -> str:
        """
        Get a string representation of the list.

        Returns:
            str: String representation of the list.
        """

        with self.lock:
            return super().__repr__()
