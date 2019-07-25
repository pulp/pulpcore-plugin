=========
Changelog
=========

..
    You should *NOT* be adding new change log entries to this file, this
    file is managed by towncrier. You *may* edit previous change logs to
    fix problems like typo corrections or such.
    To add a new change log entry, please see
    https://docs.pulpproject.org/en/3.0/nightly/contributing/git.html#changelog-update

    WARNING: Don't drop the next directive!

.. towncrier release notes start

0.1.0rc4 (2019-07-25)
=====================


Features
--------

- The ``DigestValidationError`` and ``SizeValidationError`` are available in the
  ``pulpcore.plugin.exceptions`` package.
  `#5077 <https://pulp.plan.io/issues/5077>`_
- The ``HyperlinkRelatedFilter`` is available in the ``pulpcore.plugin.viewsets`` submodule.
  `#5103 <https://pulp.plan.io/issues/5103>`_


Improved Documentation
----------------------

- Adds a new page and various updates with ``ContentGuard`` documentation for plugin writers.
  `#3972 <https://pulp.plan.io/issues/3972>`_
- Removed beta changelog entries to shorten the changelog.
  `#5166 <https://pulp.plan.io/issues/5166>`_


----


0.1.0rc3 (2019-06-28)
=====================


Bugfixes
--------

- Fixes use of the proxy URL when syncing from a remote.
  `#5011 <https://pulp.plan.io/issues/5011>`_


Improved Documentation
----------------------

- Switch to using `towncrier <https://github.com/hawkowl/towncrier>`_ for better release notes.
  `#4875 <https://pulp.plan.io/issues/4875>`_
- The term 'lazy' and 'Lazy' is replaced with 'on-demand' and 'On-Demand' respectively.
  `#4990 <https://pulp.plan.io/issues/4990>`_


Deprecations and Removals
-------------------------

- The `RemoteSerializer.policy` attribute in the plugin API had its choices restricted to only
  'immediate'. Plugin writers wanting to use 'on_demand' or 'streamed' as values for 'policy' should
  redefine the 'policy' attribute on the detail Remote.
  `#4990 <https://pulp.plan.io/issues/4990>`_


----


