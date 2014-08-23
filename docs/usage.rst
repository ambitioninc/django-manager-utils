Usage
=====

Use as a Model Manager
----------------------
Django manager utils allows a user to perform various functions not natively
supported by Django's model managers. To use the manager in your Django
models, do:

.. code-block:: python

    from manager_utils import ManagerUtilsManager

    class MyModel(Model):
        objects = ManagerUtilsManager()

If you want to extend an existing manager to use the manager utils, include
mixin provided first (since it overrides the get_queryset function) as follows:

.. code-block:: python

    from django.db import models
    from manager_utils import ManagerUtilsMixin

    class MyManager(ManagerUtilsMixin, models.Manager):
        pass


Calling Manager Utils as Standalone Functions
---------------------------------------------
All of the main manager utils functions listed can also be called as standalone
functions so that third-party managers can take advantage of them. For example:

.. code-block:: python

    from manager_utils import bulk_update

    bulk_update(TestModel.objects, [model_obj1, model_obj2], ['int_field', 'float_field'])

