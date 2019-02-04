.. _lazy-support:

Lazy Support
------------

"Lazy support" refers to a plugin's ability to support downloading and creating Content but not
downloading their associated Artifacts. By convention, users expect the `Remote.policy` attribute to
determine when Artifacts will be downloaded. See the user docs for specifics on the user
expectations there.

Adding Support when using DeclarativeVersion
============================================

Plugins like `pulp-file` sync content using `DeclarativeVersion`, which takes an option called
`download_artifacts` which defaults to `True`. Lazy support can be added by specifying
`download_artifacts=False`.

`Remote.policy` can take several values. To easily translate them, consider a snippet like this one
taken from `pulp-file`.::

    download = (remote.policy == Remote.IMMEDIATE)  # Interpret policy to download Artifacts or not
    dv = DeclarativeVersion(first_stage, repository, mirror=mirror, download_artifacts=download)


Adding Support when using a Custom Stages API Pipeline
======================================================

Plugins like `pulp-rpm` that sync content using a custom pipeline can enable lazy support by
excluding the `QueryExistingArtifacts`, `ArtifactDownloader` and `ArtifactSaver` stages. Without
these stages included, no Artifact downloading will occur. Content unit saving will occur, which
will correctly create the lazy content units.

`Remote.policy` can take several values. To easily maintain the pipeline consider a snippet like
this one inspired by `pulp-rpm`::

    download = (remote.policy == Remote.IMMEDIATE)  # Interpret policy to download Artifacts or not
    stages = [first_stage]
    if download:
        stages.extend([QueryExistingArtifacts(), ArtifactDownloader(), ArtifactSaver()])
    stages.extend(the_rest_of_the_pipeline)  # This adds the Content and Association Stages


What if the Custom Pipeline Needs Artifact Downloading?
=======================================================

For example, `pulp-docker` uses a custom Stages API Pipeline, and relies on Artifact downloading to
download metadata that is saved and stored as a Content unit. This metadata defines more Content
units to be created without downloading their corresponding Artifacts. The lazy support for this
type needs to download Artifacts for those content types, but not others.

.. warning::
   TODO:  https://pulp.plan.io/issues/4209


How Does This Work at the Model Layer?
======================================

The presence of a `RemoteArtifact` is what allows the Pulp content app to fetch and serve that
Artifact on-demand. So a Content unit is lazy if and only if:

1. It has a saved Content unit

2. A `ContentArtifact` for each `Artifact` is saved that the Content unit would have referenced.
   Note: the `ContentArtifact` is created in both lazy and non-lazy cases.

3. Instead of creating and saving an `Artifact`, a `RemoteArtifact` is created. This contains any
   known digest or size information allowing for automatic validation when the `Artifact` is
   fetched.


How does the Content App work with this Model Layer?
====================================================

When a request for content arrives, it is matched against a `Distribution` and eventually against a
specific Artifact path, which actually matches against a `ContentArtifact` not an `Artifact`. If an
`Artifact` exists, it is served to the client. Otherwise a `RemoteArtifact` allows the `Artifact` to
be downloaded on-demand and served to the client.

If `Remote.policy == Remote.ON_DEMAND` the Artifact is saved on the first download. This causes
future requests to serve the already-downloaded and validated Artifact.

.. note::
   In situations where multiple Remotes synced and provided the same `Content` unit, only one
   `Content` unit is created but many `RemoteArtifact` objects may be created. The Pulp Content app
   will try all `RemoteArtifact` objects that correspond with a `ContentArtifact`. It's possible an
   unexpected `Remote` could be used when fetching that equivalent `Content` unit. Similar warnings
   are in the user documentation on lazy.
