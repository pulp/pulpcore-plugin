import asyncio
import logging

from django.db.models import Q

from pulpcore.plugin.models import Artifact, ContentArtifact, ProgressBar, RemoteArtifact

from .api import Stage

log = logging.getLogger(__name__)


class QueryExistingArtifacts(Stage):
    """
    A Stages API stage that replaces :attr:`DeclarativeContent.content` objects with already-saved
    :class:`~pulpcore.plugin.models.Artifact` objects.

    This stage expects :class:`~pulpcore.plugin.stages.DeclarativeContent` units from `self._in_q`
    and inspects their associated :class:`~pulpcore.plugin.stages.DeclarativeArtifact` objects. Each
    :class:`~pulpcore.plugin.stages.DeclarativeArtifact` object stores one
    :class:`~pulpcore.plugin.models.Artifact`.

    This stage inspects any unsaved :class:`~pulpcore.plugin.models.Artifact` objects and searches
    using their metadata for existing saved :class:`~pulpcore.plugin.models.Artifact` objects inside
    Pulp with the same digest value(s). Any existing :class:`~pulpcore.plugin.models.Artifact`
    objects found will replace their unsaved counterpart in the
    :class:`~pulpcore.plugin.stages.DeclarativeArtifact` object.

    Each :class:`~pulpcore.plugin.stages.DeclarativeContent` is sent to `self._out_q` after all of
    its :class:`~pulpcore.plugin.stages.DeclarativeArtifact` objects have been handled.

    This stage drains all available items from `self._in_q` and batches everything into one large
    call to the db for efficiency.
    """

    async def run(self):
        """
        The coroutine for this stage.

        Returns:
            The coroutine for this stage.
        """
        async for batch in self.batches():
            all_artifacts_q = Q(pk=None)
            for d_content in batch:
                for d_artifact in d_content.d_artifacts:
                    one_artifact_q = d_artifact.artifact.q()
                    if one_artifact_q:
                        all_artifacts_q |= one_artifact_q

            for artifact in Artifact.objects.filter(all_artifacts_q):
                for d_content in batch:
                    for d_artifact in d_content.d_artifacts:
                        for digest_name in artifact.DIGEST_FIELDS:
                            digest_value = getattr(d_artifact.artifact, digest_name)
                            if digest_value and digest_value == getattr(artifact, digest_name):
                                d_artifact.artifact = artifact
                                break
            for d_content in batch:
                await self.put(d_content)


class ArtifactDownloader(Stage):
    """
    A Stages API stage to download :class:`~pulpcore.plugin.models.Artifact` files, but don't save
    the :class:`~pulpcore.plugin.models.Artifact` in the db.

    This stage downloads the file for any :class:`~pulpcore.plugin.models.Artifact` objects missing
    files and creates a new :class:`~pulpcore.plugin.models.Artifact` object from the downloaded
    file and its digest data. The new :class:`~pulpcore.plugin.models.Artifact` is not saved but
    added to the :class:`~pulpcore.plugin.stages.DeclarativeArtifact` object, replacing the likely
    incomplete :class:`~pulpcore.plugin.models.Artifact`.

    Each :class:`~pulpcore.plugin.stages.DeclarativeContent` is sent to `self._out_q` after all of
    its :class:`~pulpcore.plugin.stages.DeclarativeArtifact` objects have been handled.

    This stage creates a ProgressBar named 'Downloading Artifacts' that counts the number of
    downloads completed. Since it's a stream the total count isn't known until it's finished.

    This stage drains all available items from `self._in_q` and starts as many downloaders as
    possible (up to `download_concurrency` set on a Remote)

    Args:
        max_concurrent_content (int): The maximum number of
            :class:`~pulpcore.plugin.stages.DeclarativeContent` instances to handle simultaneously.
            Default is 200.
        args: unused positional arguments passed along to :class:`~pulpcore.plugin.stages.Stage`.
        kwargs: unused keyword arguments passed along to :class:`~pulpcore.plugin.stages.Stage`.
    """

    def __init__(self, max_concurrent_content=200, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_concurrent_content = max_concurrent_content

    async def run(self):
        """
        The coroutine for this stage.

        Returns:
            The coroutine for this stage.
        """
        def _add_to_pending(coro):
            nonlocal pending
            task = asyncio.ensure_future(coro)
            pending.add(task)
            return task

        #: (set): The set of unfinished tasks.  Contains the content
        #    handler tasks and may contain `content_get_task`.
        pending = set()

        content_iterator = self.items()

        #: (:class:`asyncio.Task`): The task that gets new content from `self._in_q`.
        #    Set to None if stage is shutdown.
        content_get_task = _add_to_pending(content_iterator.__anext__())

        with ProgressBar(message='Downloading Artifacts') as pb:
            try:
                while pending:
                    done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                    for task in done:
                        if task is content_get_task:
                            try:
                                _add_to_pending(self._handle_content_unit(task.result()))
                            except StopAsyncIteration:
                                # previous stage is finished and we retrieved all
                                # content instances: shutdown
                                content_get_task = None
                        else:
                            pb.done += task.result()  # download_count
                            pb.save()

                    if content_get_task and content_get_task not in pending:  # not yet shutdown
                        if len(pending) < self.max_concurrent_content:
                            content_get_task = _add_to_pending(content_iterator.__anext__())
            except asyncio.CancelledError:
                # asyncio.wait does not cancel its tasks when cancelled, we need to do this
                for future in pending:
                    future.cancel()
                raise

    async def _handle_content_unit(self, d_content):
        """Handle one content unit.

        Returns:
            The number of downloads
        """
        downloaders_for_content = [
            d_artifact.download() for d_artifact in d_content.d_artifacts
            if d_artifact.artifact.pk is None
        ]
        if downloaders_for_content:
            await asyncio.gather(*downloaders_for_content)
        await self.put(d_content)
        return len(downloaders_for_content)


class ArtifactSaver(Stage):
    """
    A Stages API stage that saves any unsaved :attr:`DeclarativeArtifact.artifact` objects.

    This stage expects :class:`~pulpcore.plugin.stages.DeclarativeContent` units from `self._in_q`
    and inspects their associated :class:`~pulpcore.plugin.stages.DeclarativeArtifact` objects. Each
    :class:`~pulpcore.plugin.stages.DeclarativeArtifact` object stores one
    :class:`~pulpcore.plugin.models.Artifact`.

    Any unsaved :class:`~pulpcore.plugin.models.Artifact` objects are saved. Each
    :class:`~pulpcore.plugin.stages.DeclarativeContent` is sent to `self._out_q` after all of its
    :class:`~pulpcore.plugin.stages.DeclarativeArtifact` objects have been handled.

    This stage drains all available items from `self._in_q` and batches everything into one large
    call to the db for efficiency.
    """

    async def run(self):
        """
        The coroutine for this stage.

        Returns:
            The coroutine for this stage.
        """
        async for batch in self.batches():
            da_to_save = []
            for d_content in batch:
                for d_artifact in d_content.d_artifacts:
                    if d_artifact.artifact.pk is None:
                        d_artifact.artifact.file = str(d_artifact.artifact.file)
                        da_to_save.append(d_artifact)

            if da_to_save:
                for d_artifact, artifact in zip(da_to_save, Artifact.objects.bulk_get_or_create(
                        d_artifact.artifact for d_artifact in da_to_save)):
                    d_artifact.artifact = artifact

            for d_content in batch:
                await self.put(d_content)


class RemoteArtifactSaver(Stage):
    """
    A Stage that saves :class:`~pulpcore.plugin.models.RemoteArtifact` objects

    An :class:`~pulpcore.plugin.models.RemoteArtifact` object is saved for each
    :class:`~pulpcore.plugin.stages.DeclarativeArtifact`.
    """

    async def run(self):
        """
        The coroutine for this stage.

        Returns:
            The coroutine for this stage.
        """
        async for batch in self.batches():
            RemoteArtifact.objects.bulk_get_or_create(self._needed_remote_artifacts(batch))
            for d_content in batch:
                await self.put(d_content)

    @staticmethod
    def _declared_remote_artifacts(batch):
        """
        Build a generator of "declared" :class:`~pulpcore.plugin.models.RemoteArtifact` to
        be created for the batch.

        Each RemoteArtifact corresponds to a :class:`~pulpcore.plugin.stages.DeclarativeArtifact`
        associated with a :class:`~pulpcore.plugin.stages.DeclarativeContent` in the batch.

        Args:
            batch (list): List of :class:`~pulpcore.plugin.stages.DeclarativeContent`.

        Returns:
            Iterable: Of :class:`~pulpcore.plugin.models.RemoteArtifact`.
        """
        artifact_mapping = {}
        for d_content in batch:
            for d_artifact in d_content.d_artifacts:
                key = (
                    d_content.content.pk,
                    d_artifact.relative_path
                )
                artifact_mapping[key] = d_artifact
        for content_artifact in ContentArtifact.objects.filter(
                content__in=(dc.content for dc in batch)):
            key = (
                content_artifact.content.pk,
                content_artifact.relative_path
            )
            d_artifact = artifact_mapping[key]
            remote_artifact = RemoteArtifact(
                url=d_artifact.url,
                size=d_artifact.artifact.size,
                md5=d_artifact.artifact.md5,
                sha1=d_artifact.artifact.sha1,
                sha224=d_artifact.artifact.sha224,
                sha256=d_artifact.artifact.sha256,
                sha384=d_artifact.artifact.sha384,
                sha512=d_artifact.artifact.sha512,
                content_artifact=content_artifact,
                remote=d_artifact.remote
            )
            yield remote_artifact

    def _needed_remote_artifacts(self, batch):
        """
        Build a generator of only :class:`~pulpcore.plugin.models.RemoteArtifact` that need
        to be created for the batch.

        Args:
            batch (list): List of :class:`~pulpcore.plugin.stages.DeclarativeContent`.

        Returns:
            Iterable: Of :class:`~pulpcore.plugin.models.RemoteArtifact`.
        """
        q = Q(pk=None)
        existing = set()
        for d_content in batch:
            for content_artifact in ContentArtifact.objects.filter(content=d_content.content):
                q |= Q(
                    content_artifact=content_artifact,
                    remote__in=(a.remote for a in d_content.d_artifacts)
                )
        for remote_artifact in RemoteArtifact.objects.filter(q):
            key = (
                remote_artifact.remote.pk,
                remote_artifact.content_artifact.pk
            )
            existing.add(key)
        for remote_artifact in self._declared_remote_artifacts(batch):
            key = (
                remote_artifact.remote.pk,
                remote_artifact.content_artifact.pk
            )
            if key in existing:
                continue
            yield remote_artifact
