# Single Consumer Queue
Single Consumer Queue is a Python library that provides an alternative to the standard asyncio.Queue for single consumer scenarios. It consists of two classes: SingleConsumerQueue and SingleConsumerPriorityQueue. Both classes implement the AbstractSingleConsumerQueue abstract base class, which provides the basic functionality of a single consumer queue.

## Why Single Consumer Queue?
In some scenarios, the standard asyncio.Queue can be slower than necessary. This is because asyncio.Queue is designed to be used with multiple consumers, which means that it has additional overhead to handle multiple concurrent accesses. If you only have one consumer, you can use SingleConsumerQueue or SingleConsumerPriorityQueue to reduce this overhead and improve performance.

## How to use Single Consumer Queue
Installation
You can install Single Consumer Queue using pip:

```pip install single-consumer-queue```

## Usage
Here's an example of how to use SingleConsumerQueue:

```
async def consumer(queue: SingleConsumerQueue | SingleConsumerPriorityQueue):
    async for item in queue.start_consuming():
        print(item)
```

SingleConsumerQueue raises exception if you try to add multiple consumers:

```
async def consumer(queue: SingleConsumerQueue | SingleConsumerPriorityQueue):
    async for item in queue.start_consuming():
        print(item)

queue = SingleConsumerQueue()
asyncio.create_task(consumer(queue))
await asyncio sleep(0.1)
await queue.get()  # raises runtime error
```

Lock is checked and acquired when consumer starts and every time that get is awaited.

Get has considerate overhead because it has to use lock every time, so it is recommended to use `start_consuming` generator when you want to consume items in the loop.
