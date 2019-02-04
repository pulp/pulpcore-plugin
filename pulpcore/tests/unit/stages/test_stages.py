import asyncio

import asynctest

from pulpcore.plugin.stages import Stage, EndStage


class TestStage(asynctest.TestCase):

    def setUp(self):
        self.in_q = asyncio.Queue()
        self.stage = Stage()
        self.stage._connect(self.in_q, None)

    async def test_none_only(self):
        self.in_q.put_nowait(None)
        batch_it = self.stage.batches(minsize=1)
        with self.assertRaises(StopAsyncIteration):
            await batch_it.__anext__()

    async def test_single_batch_and_none(self):
        self.in_q.put_nowait(1)
        self.in_q.put_nowait(2)
        self.in_q.put_nowait(None)
        batch_it = self.stage.batches(minsize=1)
        self.assertEqual([1, 2], await batch_it.__anext__())
        with self.assertRaises(StopAsyncIteration):
            await batch_it.__anext__()

    async def test_batch_and_single_none(self):
        self.in_q.put_nowait(1)
        self.in_q.put_nowait(2)
        batch_it = self.stage.batches(minsize=1)
        self.assertEqual([1, 2], await batch_it.__anext__())
        self.in_q.put_nowait(None)
        with self.assertRaises(StopAsyncIteration):
            await batch_it.__anext__()

    async def test_two_batches(self):
        self.in_q.put_nowait(1)
        self.in_q.put_nowait(2)
        batch_it = self.stage.batches(minsize=1)
        self.assertEqual([1, 2], await batch_it.__anext__())
        self.in_q.put_nowait(3)
        self.in_q.put_nowait(4)
        self.in_q.put_nowait(None)
        self.assertEqual([3, 4], await batch_it.__anext__())
        with self.assertRaises(StopAsyncIteration):
            await batch_it.__anext__()


class TestMultipleStages(asynctest.TestCase):

    class FirstStage(Stage):
        def __init__(self, num, minsize, test_case, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.num = num
            self.minsize = minsize
            self.test_case = test_case

        async def run(self):
            for i in range(self.num):
                await asyncio.sleep(0)  # Force reschedule
                await self.put(i)

    class MiddleStage(Stage):
        def __init__(self, num, minsize, test_case, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.num = num
            self.minsize = minsize
            self.test_case = test_case

        async def run(self):
            async for batch in self.batches(self.minsize):
                self.test_case.assertTrue(batch)
                self.test_case.assertGreaterEqual(len(batch), min(self.minsize, self.num))
                self.num -= len(batch)
                for b in batch:
                    await self.put(b)
            self.test_case.assertEqual(self.num, 0)

    class LastStage(Stage):
        def __init__(self, num, minsize, test_case, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.num = num
            self.minsize = minsize
            self.test_case = test_case

        async def run(self):
            async for batch in self.batches(self.minsize):
                self.test_case.assertTrue(batch)
                self.test_case.assertGreaterEqual(len(batch), min(self.minsize, self.num))
                self.num -= len(batch)
            self.test_case.assertEqual(self.num, 0)

    async def test_batch_queue_and_min_sizes(self):
        """Test batches iterator in a small stages setting with various sizes"""
        for num in range(10):
            for minsize in range(1, 5):
                for qsize in range(1, num + 1):
                    queues = [asyncio.Queue(maxsize=qsize) for i in range(3)]
                    first_stage = self.FirstStage(num, minsize, self)
                    middle_stage = self.MiddleStage(num, minsize, self)
                    last_stage = self.LastStage(num, minsize, self)
                    end_stage = EndStage()
                    first_stage._connect(None, queues[0])
                    middle_stage._connect(queues[0], queues[1])
                    last_stage._connect(queues[1], queues[2])
                    end_stage._connect(queues[2], None)
                    await asyncio.gather(
                        last_stage(),
                        middle_stage(),
                        first_stage(),
                        end_stage(),
                    )
