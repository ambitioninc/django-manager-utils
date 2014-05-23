[![Build Status](https://travis-ci.org/ambitioninc/django-manager-utils.png)](https://travis-ci.org/ambitioninc/django-manager-utils)
django-manager-utils
=====================

Additional utilities for Django model managers.

# A Brief Overview
Django manager utils allows a user to perform various functions not natively supported by Django's model managers. To use the manager in your Django models, do:

    from manager_utils import ManagerUtilsManager

    class MyModel(Model):
        objects = ManagerUtilsManager()

If you want to extend an existing manager to use the manager utils, include mixin provided first (since it overrides the get_queryset function) as follows:

    from manager_utils import ManagerUtilsMixin

    class MyManager(ManagerUtilsMixin, Manager):
        pass

An overview of each util is below with links to more in-depth documentation and examples for each function.

- [single](#single): Grabs a single element from table and verifies it is the only element.
- [get_or_none](#get_or_none): Performs a get on a queryset and returns None if the object does not exist.
- [upsert](#upsert): Performs an upsert (update or insert) to a model.
- [bulk_upsert](#bulk_upsert): Performs a bulk upsert to a list of objects.
- [bulk_update](#bulk_update): Bulk updates a list of models and the fields that have been updated.
- [id_dict](#id_dict): Returns a dictionary of objects keyed on their ID.
- [post_bulk_operation](#post_bulk_operation): A signal that is fired when a bulk operation happens.

## single()<a name="single"></a>
Assumes that the model only has one element in the table or queryset and returns that value. If the table has more than one or no value, an exception is raised.

**Returns**: The only model object in the queryset.

**Raises**: DoesNotExist error when the object does not exist or a MultipleObjectsReturned error when there is more than one object.

**Examples**:

    TestModel.objects.create(int_field=1)
    model_obj = TestModel.objects.single()
    print model_obj.int_field
    1

## get_or_none(\*\*query_params)<a name="get_or_none"></a>
Get an object or return None if it doesn't exist.

**Args**:
- \*\*query_params: The query parameters used in the lookup.

**Returns**: A model object if one exists with the query params, None otherwise.

**Examples**:

    model_obj = TestModel.objects.get_or_none(int_field=1)
    print model_obj
    None

    TestModel.objects.create(int_field=1)
    model_obj = TestModel.objects.get_or_none(int_field=1)
    print model_obj.int_field
    1

## upsert(defaults=None, updates=None, \*\*kwargs)<a name="upsert"></a>
Performs an update on an object or an insert if the object does not exist.

**Args**:
- defaults: These values are set when the object is inserted, but are irrelevant when the object already exists. This field should only be used when values only need to be set during creation.
- updates: These values are updated when the object is updated. They also override any values provided in the defaults when inserting the object.
- \*\*kwargs: These values provide the arguments used when checking for the existence of the object. They are used in a similar manner to Django's get_or_create function and are set in a created object.

**Returns**: A tuple of the upserted object and a Boolean that is True if it was created (False otherwise)

**Examples**:

    # Upsert a test model with an int value of 1. Use default values that will be given to it when created
    model_obj, created = TestModel.objects.upsert(int_field=1, defaults={'float_field': 2.0})
    print created
    True
    print model_obj.int_field, model_obj.float_field
    1, 2.0

    # Do an upsert on that same model with different default fields. Since it already exists, the defaults
    # are not used
    model_obj, created = TestModel.objects.upsert(int_field=1, defaults={'float_field': 3.0})
    print created
    False
    print model_obj.int_field, model_obj.float_field
    1, 2.0

    # In order to update the float field in an existing object, use the updates dictionary
    model_obj, created = TestModel.objects.upsert(int_field=1, updates={'float_field': 3.0})
    print created
    False
    print model_obj.int_field, model_obj.float_field
    1, 3.0

    # You can use updates on a newly created object that will also be used as initial values.
    model_obj, created = TestModel.objects.upsert(int_field=2, updates={'float_field': 4.0})
    print created
    True
    print model_obj.int_field, model_obj.float_field
    2, 4.0

## bulk_upsert(model_objs, unique_fields, update_fields=None, return_upserts=False)<a name="bulk_upsert"></a>
Performs a bulk update or insert on a list of model objects. Matches all objects in the queryset with the objs provided using the field values in unique_fields. If an existing object is matched, it is updated with the values from the provided objects. Objects that don't match anything are bulk inserted. If update_fields is None, this function reduces down to bulk creating objects that didn't previously exist.

**Args**:
- objs: A list of dictionaries that have fields corresponding to the model in the manager.
- unique_fields: A list of fields that are used to determine if an object in objs matches a model from the queryset.
- update_fields: A list of fields used from the objects in objs as fields when updating existing models.
- return_upserts: A flag to return upserted values. Incurs an additional DB read to fetch any bulk created values.

**Signals**: Emits a post_bulk_operation when a bulk_update or a bulk_create occurs.

**Examples:**

    # Start off with no objects in the database. Call a bulk_upsert on the TestModel, which includes
    # a char_field, int_field, and float_field
    TestModel.objects.bulk_upsert([
        TestModel(float_field=1.0, char_field='1', int_field=1),
        TestModel(float_field=2.0, char_field='2', int_field=2),
        TestModel(float_field=3.0, char_field='3', int_field=3),
    ], ['int_field'], ['char_field'])

    # All objects should have been created
    print TestModel.objects.count()
    3

    # Now perform a bulk upsert on all the char_field values. Since the objects existed previously
    # (known by the int_field uniqueness constraint), the char fields should be updated
    TestModel.objects.bulk_upsert([
        TestModel(float_field=1.0, char_field='0', int_field=1),
        TestModel(float_field=2.0, char_field='0', int_field=2),
        TestModel(float_field=3.0, char_field='0', int_field=3),
    ], ['int_field'], ['char_field'])

    # No more new objects should have been created, and every char field should be 0
    print TestModel.objects.count(), TestModel.objects.filter(char_field='-1').count()
    3, 3

    # Do the exact same operation, but this time add an additional object that is not already
    # stored. It will be inserted.
    TestModel.objects.bulk_upsert([
        TestModel(float_field=1.0, char_field='1', int_field=1),
        TestModel(float_field=2.0, char_field='2', int_field=2),
        TestModel(float_field=3.0, char_field='3', int_field=3),
        TestModel(float_field=4.0, char_field='4', int_field=4),
    ], ['int_field'], ['char_field'])

    # There should be one more object
    print TestModel.objects.count()
    4

    # Note that one can also do the upsert on a queryset. Perform the same data upsert on a
    # filter for int_field=1. In this case, only one object has the ability to be updated.
    # All of the other objects will be inserted
    TestModel.objects.filter(int_field=1).bulk_upsert([
        TestModel(float_field=1.0, char_field='1', int_field=1),
        TestModel(float_field=2.0, char_field='2', int_field=2),
        TestModel(float_field=3.0, char_field='3', int_field=3),
        TestModel(float_field=4.0, char_field='4', int_field=4),
    ], ['int_field'], ['char_field'])

    # There should be three more objects
    print TestModel.objects.count()
    7

## bulk_update(model_objs, fields_to_update)<a name="bulk_update"></a>
Performs an bulk update on an list of objects. Any fields listed in the fields_to_update array will be updated in the database.

**Args**:
- model_objs: A list of model objects that are already stored in the database.
- fields_to_update: A list of fields to update in the models. Only these fields will be updated in the database. The 'id' field is included by default.

**Examples**:

    # Create a couple test models
    model_obj1 = TestModel.objects.create(int_field=1, float_field=2.0, char_field='Hi')
    model_obj2 = TestModel.objects.create(int_field=3, float_field=4.0, char_field='Hello')

    # Change their fields and do a bulk update
    model_obj1.int_field = 10
    model_obj1.float_field = 20.0
    model_obj2.int_field = 30
    model_obj2.float_field = 40.0
    TestModel.objects.bulk_update([model_obj1, model_obj2], ['int_field', 'float_field'])

    # Reload the models and view their changes
    model_obj1 = TestModel.objects.get(id=model_obj1.id)
    print model_obj1.int_field, model_obj1.float_field
    10, 20.0

    model_obj2 = TestModel.objects.get(id=model_obj2.id)
    print model_obj2.int_field, model_obj2.float_field
    10, 20.0

## id_dict()<a name="id_dict"></a>
Returns a dictionary of the model objects keyed on their ID.

**Examples**

    TestModel.objects.create(int_field=1)
    TestModel.objects.create(int_field=2)

    print TestModel.objects.id_dict()
    {1: <TestModel: TestModel object>, 2: <TestModel: TestModel object>}

    print TestModel.objects.filter(int_field=2).id_dict()
    {2: <TestModel: TestModel object>}

## post_bulk_operation(providing_args=['model'])<a name="post_bulk_operation"></a>
A signal that is emitted at the end of a bulk operation. The current bulk operations are Django's update and bulk_create methods and this package's bulk_update method. The signal provides the model that was updated.

**Examples**

    from manager_utils import post_bulk_operation

    def signal_handler(self, *args, **kwargs):
        print kwargs['model']

    post_bulk_operation.connect(signal_handler)

    TestModel.objects.all().update(int_field=1)
    <type 'TestModel'>

# Calling Manager Utils as Standalone Functions
All of the main manager utils functions listed can also be called as standalone functions so that third-party managers can take advantage of them. For example:

```python
from manager_utils import bulk_update


bulk_update(TestModel.objects, [model_obj1, model_obj2], ['int_field', 'float_field'])
```

# License
MIT License (See the LICENSE file included in this repository)
