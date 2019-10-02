.. _error-handling-basics:

Error Handling
--------------

Please see the `error-handling
<https://docs.pulpproject.org/en/3.0/nightly/contributing/error-handling.html>`_ section in the
code guidelines.

Non fatal exceptions should be recorded in the
:meth:`~pulpcore.plugin.models.Task.non_fatal_errors` field.
