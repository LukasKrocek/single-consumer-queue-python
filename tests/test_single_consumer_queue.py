# pylint:disable=protected-access
import asyncio
import timeit
from asyncio import PriorityQueue
from time import perf_counter

import pytest

from single_consumer_queue.queue import SingleConsumerPriorityQueue


@pytest.mark.asyncio
async def test_put_and_get() -> None:
    queue = SingleConsumerPriorityQueue[int]()
    queue.put_nowait(1)
    assert queue._queue == [1]

    gen = queue.start_consuming()
    result = await anext(gen)
    assert result == 1
    assert len(queue._queue) == 0

    waiting_task = asyncio.create_task(asyncio.wait_for(anext(gen), timeout=0.01))
    await asyncio.sleep(0.001)
    assert queue._waiter is not None and not queue._waiter.done()
    with pytest.raises(asyncio.TimeoutError):
        await waiting_task
    assert queue._waiter is not None and queue._waiter.cancelled()


@pytest.mark.asyncio
async def test_put_sets_future_result_when_future_exists() -> None:
    my_q = SingleConsumerPriorityQueue[int]()
    my_q._waiter = asyncio.Future()
    assert not my_q._waiter.done()
    my_q.put_nowait(1)
    assert my_q._waiter.done()

    assert my_q._queue == [1]
    assert my_q._waiter.result() is None


@pytest.mark.asyncio
async def test_put_when_future_is_cancelled() -> None:
    future = asyncio.Future[None]()
    future.cancel()
    my_q = SingleConsumerPriorityQueue[int]()
    my_q._waiter = future
    my_q.put_nowait(1)
    assert my_q._queue == [1]
    assert my_q._waiter is future


@pytest.mark.asyncio
async def test_get_creates_future_and_waits() -> None:
    queue = SingleConsumerPriorityQueue[int]()
    gen = queue.start_consuming()
    queue_get_task = asyncio.create_task(asyncio.wait_for(anext(gen), timeout=0.01))
    await asyncio.sleep(0.001)
    assert not queue_get_task.done()
    assert queue._waiter is not None and not queue._waiter.done()

    queue.put_nowait(1)
    result = await queue_get_task
    assert result == 1
    assert len(queue._queue) == 0
    assert queue._waiter is None


@pytest.mark.asyncio
async def test_second_waiter_raises_error() -> None:
    async def consume(q: SingleConsumerPriorityQueue[int]) -> None:
        async for _ in q.start_consuming():
            pass

    queue = SingleConsumerPriorityQueue[int]()
    get_task = asyncio.create_task(consume(queue))
    await asyncio.sleep(0)
    with pytest.raises(RuntimeError):
        await queue.get()

    with pytest.raises(RuntimeError):
        queue.get_nowait()

    with pytest.raises(RuntimeError):
        async for _ in queue.start_consuming():
            pass

    get_task.cancel()


@pytest.mark.asyncio
@pytest.mark.skip
async def test_perf() -> None:
    my_q = SingleConsumerPriorityQueue[int]()
    t1 = perf_counter()
    my_q.put_nowait(1)
    async for i in my_q.start_consuming():
        my_q.put_nowait(i + 1)
        if i > 1_000_000:
            break
    single_consumer_priority_queue_time = perf_counter() - t1
    # Custom Queue time 0.45637712499592453
    print(f"Custom Queue time {single_consumer_priority_queue_time}")

    q = PriorityQueue[int]()
    t1 = perf_counter()
    for _ in range(1_000_000):
        q.put_nowait(1)
        await q.get()
    built_in_priority_queue_time = perf_counter() - t1
    # Built-in Queue time 1.11714420899807
    print(f"Built-in Queue time {built_in_priority_queue_time}")

    # single consumer priority is roughly 3 times faster than built-in priority queue, in this test for python 3.10
    assert single_consumer_priority_queue_time < built_in_priority_queue_time / 2


@pytest.mark.asyncio
@pytest.mark.skip
async def test_perf_2() -> None:
    async def custom_queue_consumer(q: SingleConsumerPriorityQueue[int]) -> None:
        counter = 0
        async for _ in q.start_consuming():
            counter += 1
            if counter == 999_999:
                return

    async def built_in_queue_consumer(q: PriorityQueue[int]) -> None:
        counter = 1_000_000
        for _ in range(counter):
            await q.get()
        return

    single_queue = SingleConsumerPriorityQueue[int]()
    task = asyncio.create_task(custom_queue_consumer(single_queue))
    t1 = perf_counter()
    putting_time = timeit.timeit("single_queue.put_nowait(1)", globals={**globals(), **locals()})
    await task
    single_consumer_priority_queue_time = perf_counter() - t1
    # Custom Queue put no wait 1m times: 0.2097, putting + getting 1m items 0.6893
    print(
        f"Custom Queue put no wait 1m times: {putting_time:.4f}, "
        f"putting + getting 1m items {single_consumer_priority_queue_time:.4f}"
    )

    queue = PriorityQueue[int]()
    task2 = asyncio.create_task(built_in_queue_consumer(queue))
    t1 = perf_counter()
    putting_time = timeit.timeit("queue.put_nowait(1)", globals={**globals(), **locals()})
    await task2
    built_in_priority_queue_time = perf_counter() - t1
    # Built-in Queue put no wait 1m times: 0.5601, putting + getting 1m items 1.3322
    print(
        f"Built-in Queue put no wait 1m times: {putting_time:.4f}, "
        f"putting + getting 1m items {built_in_priority_queue_time:.4f}"
    )

    # single consumer priority is roughly 2 times faster than built-in priority queue, in this test for python 3.10
    assert single_consumer_priority_queue_time < built_in_priority_queue_time * 2 / 3
