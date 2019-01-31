from django.db.models import Q

from pulpcore.plugin.models import Content, ProgressBar

from .api import Stage


class ContentUnitAssociation(Stage):
    """
    A Stages API stage that associates content units with `new_version`.

    This stage stores all content unit primary keys in memory before running. This is done to
    compute the units already associated but not received from `in_q`. These units are passed via
    `out_q` to the next stage as a :class:`django.db.models.query.QuerySet`.

    This stage creates a ProgressBar named 'Associating Content' that counts the number of units
    associated. Since it's a stream the total count isn't known until it's finished.

    Args:
        new_version (:class:`~pulpcore.plugin.models.RepositoryVersion`): The repo version this
            stage associates content with.
        args: unused positional arguments passed along to :class:`~pulpcore.plugin.stages.Stage`.
        kwargs: unused keyword arguments passed along to :class:`~pulpcore.plugin.stages.Stage`.
    """

    def __init__(self, new_version, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.new_version = new_version

    async def __call__(self, in_q, out_q):
        """
        The coroutine for this stage.

        Args:
            in_q (:class:`asyncio.Queue`): Each item is a
                :class:`~pulpcore.plugin.stages.DeclarativeContent` with saved `content` that needs
                to be associated.
            out_q (:class:`asyncio.Queue`): Each item is a :class:`django.db.models.query.QuerySet`
                of :class:`~pulpcore.plugin.models.Content` class that are already associated but
                not included in the stream of items from `in_q`.

        Returns:
            The coroutine for this stage.
        """
        with ProgressBar(message='Associating Content') as pb:
            to_delete = set(self.new_version.content.values_list('pk', flat=True))
            async for batch in self.batches(in_q):
                to_add = set()
                for declarative_content in batch:
                    try:
                        to_delete.remove(declarative_content.content.pk)
                    except KeyError:
                        to_add.add(declarative_content.content.pk)

                if to_add:
                    self.new_version.add_content(Content.objects.filter(pk__in=to_add))
                    pb.done = pb.done + len(to_add)
                    pb.save()

            if to_delete:
                await out_q.put(Content.objects.filter(pk__in=to_delete))
            await out_q.put(None)


class ContentUnitUnassociation(Stage):
    """
    A Stages API stage that unassociates content units from `new_version`.

    This stage creates a ProgressBar named 'Un-Associating Content' that counts the number of units
    un-associated. Since it's a stream the total count isn't known until it's finished.

    Args:
        new_version (:class:`~pulpcore.plugin.models.RepositoryVersion`): The repo version this
            stage unassociates content from.
        args: unused positional arguments passed along to :class:`~pulpcore.plugin.stages.Stage`.
        kwargs: unused keyword arguments passed along to :class:`~pulpcore.plugin.stages.Stage`.
    """

    def __init__(self, new_version, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.new_version = new_version

    async def __call__(self, in_q, out_q):
        """
        The coroutine for this stage.

        Args:
            in_q (:class:`asyncio.Queue`): Each item is a
                :class:`django.db.models.query.QuerySet` of
                :class:`~pulpcore.plugin.models.Content` subclass that are already associated
                but not included in the stream of items from `in_q`. One
                :class:`django.db.models.query.QuerySet` is put for each
                :class:`~pulpcore.plugin.models.Content` type.
            out_q (:class:`asyncio.Queue`): Each item is a
                :class:`django.db.models.query.QuerySet` of
                :class:`~pulpcore.plugin.models.Content` subclass that were unassociated. One
                :class:`django.db.models.query.QuerySet` is put for each
                :class:`~pulpcore.plugin.models.Content` type.

        Returns:
            The coroutine for this stage.
        """
        with ProgressBar(message='Un-Associating Content') as pb:
            while True:
                queryset_to_unassociate = await in_q.get()
                if queryset_to_unassociate is None:
                    break

                self.new_version.remove_content(queryset_to_unassociate)
                pb.done = pb.done + queryset_to_unassociate.count()
                pb.save()

                await out_q.put(queryset_to_unassociate)
            await out_q.put(None)


class RemoveDuplicates(Stage):
    """
    Stage allows plugins to remove content that would break repository uniqueness constraints.

    This stage is expected to be added by the DeclarativeVersion. See that class for example usage.

    """

    def __init__(self, new_version, model, field_names):
        """
        Args:
            new_version (:class:`~pulpcore.plugin.models.RepositoryVersion`): The repo version this
                stage unassociates content from.
            model (:class:`pulpcore.plugin.models.Content`): Subclass of a Content model to
                indicate which content type to operate on.
            field_names (list): List of field names to ensure uniqueness within a repository
                version.
        """
        self.new_version = new_version
        self.model = model
        self.field_names = field_names

    async def __call__(self, in_q, out_q):
        """
        The coroutine for this stage.

        Args:
            in_q (:class:`asyncio.Queue`): The queue to receive
                :class:`~pulpcore.plugin.stages.DeclarativeContent` objects from.
            out_q (:class:`asyncio.Queue`): The queue to put
                :class:`~pulpcore.plugin.stages.DeclarativeContent` into.

        Returns:
            The coroutine for this stage.
        """
        rm_q = Q()
        async for batch in self.batches(in_q):
            for declarative_content in batch:
                if isinstance(declarative_content.content, self.model):
                    unit_q_dict = {field: getattr(declarative_content.content, field)
                                   for field in self.field_names}
                    # Don't remove *this* object if it is already in the repository version.
                    not_this = ~Q(pk=declarative_content.content.pk)
                    dupe = Q(**unit_q_dict)
                    rm_q |= Q(dupe & not_this)
            queryset_to_unassociate = self.model.objects.filter(rm_q)
            self.new_version.remove_content(queryset_to_unassociate)

            for declarative_content in batch:
                await out_q.put(declarative_content)
        await out_q.put(None)
