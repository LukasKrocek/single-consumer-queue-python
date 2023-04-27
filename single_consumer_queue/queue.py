import abc
import asyncio
import collections
from collections.abc import AsyncGenerator, Sized
from heapq import heappop, heappush
from typing import Deque, Generic, TypeVar

T = TypeVar("T")


class AbstractSingleConsumerQueue(Generic[T]):
    _queue: Sized

    def __init__(self) -> None:
        self._waiter: asyncio.Future[None] | None = None
        self._consuming_lock = asyncio.Lock()
        self._init()

    @abc.abstractmethod
    def _init(self) -> None:
        pass

    @abc.abstractmethod
    def _get(self) -> T:
        pass

    @abc.abstractmethod
    def _put(self, item: T) -> None:
        pass

    def empty(self) -> bool:
        return len(self._queue) == 0

    def _raise_if_locked(self) -> None:
        if self._consuming_lock.locked():
            raise RuntimeError("Only one consumer is allowed")

    async def start_consuming(self, max_consecutive_yields: int | None = None) -> AsyncGenerator[T, None]:
        """
        max_consecutive_yields:
            prevents blocking of other tasks by yielding control to the event loop after max_consecutive_yields
            The maximum number of consecutive yields before calling asyncio.sleep(0) to yield control to the event loop
            None will not yield control as long as there are items in the queue
        """
        self._raise_if_locked()
        consecutive_yield_counter = 0
        async with self._consuming_lock:
            while True:
                if self._queue:
                    yield self._get()
                    consecutive_yield_counter += 1
                    if max_consecutive_yields is not None and consecutive_yield_counter >= max_consecutive_yields:
                        consecutive_yield_counter = 0
                        await asyncio.sleep(0)
                else:
                    self._waiter = asyncio.Future()
                    consecutive_yield_counter = 0
                    await self._waiter
                    self._waiter = None

    def put_nowait(self, item: T) -> None:
        self._put(item)
        if self._waiter and not self._waiter.done():
            self._waiter.set_result(None)

    def get_nowait(self, ignore_lock: bool = False) -> T:
        """use ignore_lock = True when you know that consuming task is already cancelling"""
        if not ignore_lock:
            self._raise_if_locked()
        return self._get()

    async def get(self) -> T:
        """
        get is slow and should not be used in a loop, as it needs to acquire lock every time it's called
        use start_consuming generator instead if you want to consume items in a loop
        """
        self._raise_if_locked()
        async with self._consuming_lock:
            if self._queue:
                return self._get()
            self._waiter = asyncio.Future()
            await self._waiter
            self._waiter = None
            return self._get()


class SingleConsumerQueue(AbstractSingleConsumerQueue[T]):
    def _init(self) -> None:
        self._queue: Deque[T] = collections.deque()

    def _get(self) -> T:
        return self._queue.popleft()

    def _put(self, item: T) -> None:
        self._queue.append(item)


class SingleConsumerPriorityQueue(AbstractSingleConsumerQueue[T]):
    def _init(self) -> None:
        self._queue: list[T] = []

    def _put(self, item: T) -> None:
        heappush(self._queue, item)

    def _get(self) -> T:
        return heappop(self._queue)
