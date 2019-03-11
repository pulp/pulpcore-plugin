from pulpcore.app import models


class ContentGuard(models.ContentGuard):
    """
    Defines a named content guard.

    This is meant to be subclassed by plugin authors as an opportunity to provide
    plugin-specific persistent attributes and additional validation for those attributes.
    The permit() method must be overridden to provide the web request authorization logic.

    This object is a Django model that inherits from :class: `pulpcore.app.models.ContentGuard`
    which provides the platform persistent attributes for a content-guard. Plugin authors can
    add additional persistent attributes by subclassing this class and adding Django fields.
    We defer to the Django docs on extending this model definition with additional fields.
    """

    class Meta:
        abstract = True

    def permit(self, request):
        """
        Authorize the specified web request.

        Args:
            request (django.http.HttpRequest): A request for a published file.

        Raises:
            PermissionError: When not authorized.
        """
        raise NotImplementedError()


class Content(models.Content):
    """
    A piece of managed content.

    Relations:

        _artifacts (models.ManyToManyField): Artifacts related to Content through ContentArtifact
    """
    class Meta:
        abstract = True

    @staticmethod
    def init_from_artifact_and_relative_path(artifact, relative_path):
        """
        Return an instance of the specific content by inspecting an artifact.

        Plugin writers are expected to override this method with an implementation for a specific
        content type.

        For example:
            >>> if path.isabs(relative_path):
            >>>     raise ValueError(_("Relative path can't start with '/'."))
            >>> return FileContent(relative_path=relative_path, digest=artifact.sha256)

        Args:
            artifact (:class:`~pulpcore.plugin.models.Artifact`): An instance of an Artifact
            relative_path (str): Relative path for the content

        Raises:
            ValueError: If relative_path starts with a '/'.

        Returns:
            An un-saved instance of :class:`~pulpcore.plugin.models.Content` sub-class.
        """
        raise NotImplementedError()
