import asyncio
from gettext import gettext as _

from django.conf import settings

from .profiler import ProfilingQueue


class Stage:
    """
    The base class for all Stages API stages.

    To make a stage, inherit from this class and implement :meth:`run` on the subclass.
    """

    def __init__(self):
        self._in_q = None
        self._out_q = None

    def _connect(self, in_q, out_q):
        self._in_q = in_q
        self._out_q = out_q

    async def __call__(self):
        """
        This coroutine makes the stage callable.

        It calls :meth:`run` and signals the next stage that its work is finished.
        """
        await self.run()
        await self._out_q.put(None)

    async def run(self):
        """
        The coroutine that is run as part of this stage.

        Returns:
            The coroutine that runs this stage.

        """
        raise NotImplementedError(_('A plugin writer must implement this method'))

    async def items(self):
        """
        Asynchronous iterator yielding items of :class:`DeclarativeContent` from `self._in_q`.

        The iterator will get instances of :class:`DeclarativeContent` one by one as they get
        available.

        Yields:
            An instance of :class:`DeclarativeContent`

        Examples:
            Used in stages to get d_content instances one by one from `self._in_q`::

                class MyStage(Stage):
                    async def run(self):
                        async for d_content in self.items():
                            # process declarative content
                            await self.put(d_content)

        """
        while True:
            content = await self._in_q.get()
            if content is None:
                break
            yield content

    async def batches(self, minsize=50):
        """
        Asynchronous iterator yielding batches of :class:`DeclarativeContent` from `self._in_q`.

        The iterator will try to get as many instances of
        :class:`DeclarativeContent` as possible without blocking, but
        at least `minsize` instances.

        Args:
            minsize (int): The minimum batch size to yield (unless it is the final batch)

        Yields:
            A list of :class:`DeclarativeContent` instances

        Examples:
            Used in stages to get large chunks of d_content instances from `self._in_q`::

                class MyStage(Stage):
                    async def run(self):
                        async for batch in self.batches():
                            for d_content in batch:
                                # process declarative content
                                await self.put(d_content)

        """
        batch = []
        shutdown = False

        def add_to_batch(content):
            nonlocal batch
            nonlocal shutdown
            if content is None:
                shutdown = True
            else:
                batch.append(content)

        while not shutdown:
            content = await self._in_q.get()
            add_to_batch(content)
            while not shutdown:
                try:
                    content = self._in_q.get_nowait()
                except asyncio.QueueEmpty:
                    break
                else:
                    add_to_batch(content)

            if batch and (len(batch) >= minsize or shutdown):
                yield batch
                batch = []

    async def put(self, item):
        """
        Coroutine to pass items to the next stage.

        Args:
            item: A handled instance of :class:`pulpcore.plugin.stages.DeclarativeContent`
        """
        await self._out_q.put(item)


async def create_pipeline(stages, maxsize=100):
    """
    A coroutine that builds a Stages API linear pipeline from the list `stages` and runs it.

    Each stage is an instance of a class derived from :class:`pulpcore.plugin.stages.Stage` that
    implements the :meth:`run` coroutine. This coroutine reads asyncromously either from the
    `items()` iterator or the `batches()` iterator and outputs the items with `put()`. Here is an
    example of the simplest stage that only passes data.

    >>> class MyStage(Stage):
    >>>     async def run(self):
    >>>         async for d_content in self.items():  # Fetch items from the previous stage
    >>>             await self.put(d_content)  # Hand them over to the next stage

    Args:
        stages (list of coroutines): A list of Stages API compatible coroutines.
        maxsize (int): The maximum amount of items a queue between two stages should hold. Optional
            and defaults to 100.

    Returns:
        A single coroutine that can be used to run, wait, or cancel the entire pipeline with.
    """
    futures = []
    in_q = None
    for i, stage in enumerate(stages):
        if i < len(stages) - 1:
            if settings.PROFILE_STAGES_API:
                out_q = ProfilingQueue.make_and_record_queue(stages[i + 1], i + 1, maxsize)
            else:
                out_q = asyncio.Queue(maxsize=maxsize)
        else:
            out_q = None
        stage._connect(in_q, out_q)
        futures.append(asyncio.ensure_future(stage()))
        in_q = out_q

    try:
        await asyncio.gather(*futures)
    except Exception:
        # One of the stages raised an exception, cancel all stages...
        pending = []
        for task in futures:
            if not task.done():
                task.cancel()
                pending.append(task)
        # ...and run until all Exceptions show up
        if pending:
            await asyncio.wait(pending, timeout=60)
        raise


class EndStage(Stage):
    """
    A Stages API stage that drains incoming items and does nothing with the items. This is
    required at the end of all pipelines.

    Without this stage, the `maxsize` of the last stage's `_out_q` could fill up and block the
    entire pipeline.
    """

    async def __call__(self):
        # We overwrite __call__ here to avoid trying to put None in `self._out_q`.
        async for _ in self.items():  # noqa
            pass
