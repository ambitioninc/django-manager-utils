.. _ref-method-documentation:

Method Documentation
====================

.. automodule:: manager_utils.manager_utils

single
------

.. autofunction:: manager_utils.manager_utils.single

get_or_none
-----------

.. autofunction:: manager_utils.manager_utils.get_or_none

upsert
------

.. autofunction:: manager_utils.manager_utils.upsert

bulk_upsert
-----------

.. autofunction:: manager_utils.manager_utils.bulk_upsert

bulk_upsert2
------------

.. autofunction:: manager_utils.manager_utils.bulk_upsert2

bulk_update
-----------

.. autofunction:: manager_utils.manager_utils.bulk_update

sync
----

.. autofunction:: manager_utils.manager_utils.sync

sync2
-----

.. autofunction:: manager_utils.manager_utils.sync2

id_dict
-------

.. autofunction:: manager_utils.manager_utils.id_dict

post_bulk_operation
-------------------
A signal that is emitted at the end of a bulk operation. The current bulk
operations are Django's update and bulk_create methods and this package's
bulk_update method. The signal provides the model that was updated.

.. autoattribute:: manager_utils.manager_utils.post_bulk_operation

.. code-block:: python

    from manager_utils import post_bulk_operation

    def signal_handler(self, *args, **kwargs):
        print kwargs['model']

    post_bulk_operation.connect(signal_handler)

    print(TestModel.objects.all().update(int_field=1))
    <type 'TestModel'>
