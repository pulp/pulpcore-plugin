.. _plugin-concepts:

Plugin Concepts
===============

Like the Pulp Core itself, all Pulp Plugins are Django Applications, and could be created like any
other Django app with ``django-admin startapp <your_plugin>``. However, instead of writing all of
the boilerplate yourself, it is recommmended that you start your plugin by utilizing the `Plugin
Template <https://github.com/pulp/plugin_template>`_.  This guide will assume that you have used
the plugin_template, but if you are interested in the details of what it provides you, please see
:ref:`plugin-django-application` for more information for how plugins are "discovered" and connected to
the ``pulpcore`` Django app. Additional information is given as inline comments in the template.

Plugin API Usage
----------------
Plugin Applications interact with pulpcore with two high level interfaces, **subclassing** and
adding **tasks**. Additionally, plugins that need to implement dynamic web APIs can
optionally provide their own Django views. See our :ref:`live-apis` page for more information.

.. _subclassing-general:

Subclassing
-----------

Pulp Core and each plugin utilize `Django <https://docs.djangoproject.com/>`_ and the `Django Rest
Framework <https://www.django-rest-framework.org/>`_. Each plugin provides
:ref:`subclassing-models`, :ref:`subclassing-serializers`, and :ref:`subclassing-viewsets`. For
each object that a plugin writer needs to make, the ``pulpcore-plugin`` API provides base classes.
These base classes handle most of the boilerplate code, resulting in CRUD for each object out of
the box.

.. toctree::
   :maxdepth: 2

   subclassing/models
   subclassing/serializers
   subclassing/viewsets

.. _writing-tasks:

Tasks
-----

Any action that can run for a long time should be an asynchronous task. Plugin writers do not need
to understand the internals of the pulpcore tasking system, workers automatically execute tasks from
RQ, including tasks deployed by plugins.

**Reservations**

The tasking system adds a concept called **reservations** which ensures that actions that act on the
same resources are not run at the same time. To ensure data correctness, any action that alters the
content of a repository (thus creating a new version) must be run asynchronously, locking on the
repository and any other models which cannot change during the action. For example, sync tasks must
be asynchronous and lock on the repository and the remote. Publish should lock on the repository
version being published as well as the publisher.

**Deploying Tasks**

Tasks are deployed from Views or Viewsets, please see :ref:`kick-off-tasks`.

.. toctree::
   :maxdepth: 2

   tasks/add-remove
   tasks/publish
   tasks/export

Sync Pipeline
-------------

.. toctree::
   :maxdepth: 2

   sync_pipeline/sync_pipeline
