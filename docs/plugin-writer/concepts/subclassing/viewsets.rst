.. _subclassing-viewsets:

Viewsets
========

Each `Django Rest Framework Viewset <https://www.django-rest-framework.org/api-guide/viewsets/>`_
is a collection of views that provides ``create``, ``update``, ``retrieve``, ``list``, and
``delete``, which coresponds to http ``POST``, ``PATCH``, ``GET``, ``GET``, ``DELETE``,
respectively. Some base classes will not include all of the views if they are inappropriate. For
instance, the ``ContentViewset`` does not include ``update`` because Content Units are immutable in
Pulp 3 (to support Repository Versions).

Most Plugins will implement:
 * viewset(s) for plugin specific content type(s), should be subclassed from ContentViewset
 * viewset(s) for plugin specific remote(s), should be subclassed from RemoteViewset
 * viewset(s) for plugin specific publisher(s), should be subclassed from PublisherViewset


Endpoint Namespacing
--------------------

Automatically, each "Detail" class is namespaced by the ``app_label`` set in the
``PulpPluginAppConfig`` (this is set by the ``plugin_template``).

For example, a ContentViewSet for ``app_label`` "foobar" like this:

.. code-block:: python

    class PackageViewSet(ContentViewSet):
        endpoint_name = 'packages'

The above example will create set of CRUD endpoints for Packages at
``pulp/api/v3/content/foobar/packages/`` and
``pulp/api/v3/content/foobar/packages/<int>/``


Detail Routes (Extra Endpoints)
-------------------------------

In addition to the CRUD endpoints, a Viewset can also add a custom endpoint. For example:


.. code-block:: python

    class PackageViewSet(ContentViewSet):
        endpoint_name = 'packages'

        @decorators.detail_route(methods=('get',))
        def hello(self, request):
            return Response("Hey!")

The above example will create a simple nested endpoint at
``pulp/api/v3/content/foobar/packages/hello/``


.. _kick-off-tasks:

Kick off Tasks
^^^^^^^^^^^^^^

Some endpoints may need to deploy tasks to the tasking system. The following is an example of how
this is accomplished.

.. code-block:: python

        # We recommend using POST for any endpoints that kick off task.
        @detail_route(methods=('post',), serializer_class=RepositorySyncURLSerializer)
        # `pk` is a part of the URL
        def sync(self, request, pk):
            """
            Synchronizes a repository.
            The ``repository`` field has to be provided.
            """
            remote = self.get_object()
            serializer = RepositorySyncURLSerializer(data=request.data, context={'request': request})
            # This is how non-crud validation is accomplished
            serializer.is_valid(raise_exception=True)
            repository = serializer.validated_data.get('repository')
            mirror = serializer.validated_data.get('mirror', False)

            # This is how tasks are kicked off.
            result = enqueue_with_reservation(
                tasks.synchronize,
                [repository, remote],
                kwargs={
                    'remote_pk': remote.pk,
                    'repository_pk': repository.pk,
                    'mirror': mirror
                }
            )
            # Since tasks are asynchronous, we return a 202
            return OperationPostponedResponse(result, request)

See :class:`~pulpcore.plugin.tasking.enqueue_with_reservation` for more details.
