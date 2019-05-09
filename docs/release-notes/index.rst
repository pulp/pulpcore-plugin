============================
Plugin API 0.1 Release Notes
============================

The Plugin API is not yet declared as stable. Backwards incompatible changes might be made until
stable version 1.0 is reached.

The Plugin API currently supports version 3.y of Pulp Core.

See :doc:`Plugin API <../index>` and
:doc:`Plugin Development <../plugin-writer/index>`.

0.1.0rc2
========

* `List of plugin API related changes in rc 2 <https://github.com/pulp/pulpcore-plugin/compare/0.1.0rc1...0.1.0rc2>`_

Breaking Changes
----------------

`The RepositoryPublishURLSerializer was removed from the plugin API. <https://github.com/pulp/
pulpcore-plugin/pull/93/>`_

`Distributions are now Master/Detail. <https://pulp.plan.io/issues/4785>`_ All plugins will require
updating to provide a detail Distribution. Here is an example of pulp_file introducing the
`FileDistribution <https://github.com/pulp/pulp_file/pull/217>`_ as an example of changes to match.

`Publications are now Master/Detail. <https://pulp.plan.io/issues/4678>`_ Plugins that use
Publications will need to provide a detail Publication. Here is an example of pulp_file introducing
the `FilePublisher <https://github.com/pulp/pulp_file/pull/205>`_ as an example of changes to match
along with its `follow-on change <https://github.com/pulp/pulp_file/pull/215>`_.

0.1.0rc1
========

* `List of plugin API related changes in rc 1 <https://github.com/pulp/pulpcore-plugin/compare/0.1.0b21...0.1.0rc1>`_

0.1.0b21
========

* `List of plugin API related changes in beta 21 <https://github.com/pulp/pulpcore-plugin/compare/0.1.0b20...0.1.0b21>`_

Breaking Changes
----------------

* `Sync in additive mode by default <https://github.com/pulp/pulpcore-plugin/pull/68>`_

0.1.0b20
========

* `List of plugin API related changes in beta 20 <https://github.com/pulp/pulpcore-plugin/compare/0.1.0b19...0.1.0b20>`_

0.1.0b19
========

* `List of plugin API related changes in beta 19 <https://github.com/pulp/pulpcore-plugin/compare/0.1.0b18...0.1.0b19>`_

0.1.0b18
========

* `List of plugin API related changes in beta 18 <https://github.com/pulp/pulpcore-plugin/compare/0.1.0b17...0.1.0b18>`_

0.1.0b17
========

* `List of plugin API related changes in beta 17 <https://github.com/pulp/pulpcore-plugin/compare/0.1.0b16...0.1.0b17>`_

0.1.0b16
========

* `List of plugin API related changes in beta 16 <https://github.com/pulp/pulpcore-plugin/compare/0.1.0b15...0.1.0b16>`_

0.1.0b15
========

* `List of plugin API related changes in beta 15 <https://github.com/pulp/pulpcore-plugin/compare/pulpcore-plugin-0.1.0b14...0.1.0b15>`_

0.1.0b14
========

* `List of plugin API related changes in beta 14 <https://github.com/pulp/pulpcore-plugin/compare/pulpcore-plugin-0.1.0b13...pulpcore-plugin-0.1.0b14>`_

0.1.0b13
========

* `List of plugin API related changes in beta 13 <https://github.com/pulp/pulpcore-plugin/compare/pulpcore-plugin-0.1.0b12...pulpcore-plugin-0.1.0b13>`_

0.1.0b12
========

* `List of plugin API related changes in beta 12 <https://github.com/pulp/pulpcore-plugin/compare/pulpcore-plugin-0.1.0b11...pulpcore-plugin-0.1.0b12>`_

0.1.0b11
========

* `List of plugin API related changes in beta 11 <https://github.com/pulp/pulpcore-plugin/compare/pulpcore-plugin-0.1.0b10...pulpcore-plugin-0.1.0b11>`_

0.1.0b10
========

* `List of plugin API related changes in beta 10 <https://github.com/pulp/pulpcore-plugin/compare/pulpcore-plugin-0.1.0b9...pulpcore-plugin-0.1.0b10>`_

0.1.0b9
=======

* `List of plugin API related changes in beta 9 <https://github.com/pulp/pulpcore-plugin/compare/pulpcore-plugin-0.1.0b8...pulpcore-plugin-0.1.0b9>`_

0.1.0b8
=======

* `List of plugin API related changes in beta 8 <https://github.com/pulp/pulpcore-plugin/compare/pulpcore-plugin-0.1.0b7...pulpcore-plugin-0.1.0b8>`_

0.1.0b7
=======

* `List of plugin API related changes in beta 7 <https://github.com/pulp/pulpcore-plugin/compare/pulpcore-plugin-0.1.0b6...pulpcore-plugin-0.1.0b7>`_

0.1.0b6
=======

* `List of plugin API related changes in beta 6 <https://github.com/pulp/pulpcore-plugin/compare/pulpcore-plugin-0.0.1b5...pulpcore-plugin-0.1.0b6>`_

0.1.0b5
=======

* `List of plugin API related changes in beta 5 <https://github.com/pulp/pulpcore-plugin/compare/pulpcore-plugin-0.1.0b4...pulpcore-plugin-0.0.1b5>`_

0.1.0b4
=======

* `List of plugin API related changes in beta 4 <https://github.com/pulp/pulpcore-plugin/compare/pulpcore-plugin-0.1.0b3...pulpcore-plugin-0.1.0b4>`_

0.1.0b3
=======

* `List of plugin API related changes in beta 3 <https://github.com/pulp/pulpcore-plugin/compare/pulpcore-plugin-0.1.0b2...pulpcore-plugin-0.1.0b3>`_

0.1.0b2
=======

* Tasking system switching from Celery+RabbitMQ to RQ+Redis. This breaking change impacts both
  plugin writers and users. See
  `the blog post about this change and how to update <https://pulpproject.org/2018/05/08/pulp3-moving-to-rq/>`_.


0.1.0b1
=======

Initial beta release
