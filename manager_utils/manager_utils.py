from itertools import chain

from django.db.models import Manager
from django.db.models.query import QuerySet
from django.dispatch import Signal
from querybuilder.query import Query


# A signal that is emitted when any bulk operation occurs
post_bulk_operation = Signal(providing_args=['model'])


def id_dict(queryset):
    """
    Returns a dictionary of all the objects keyed on their ID.

    :rtype: dict
    :returns: A dictionary of objects from the queryset or manager that is keyed
            on the objects' IDs.

    Examples:

    .. code-block:: python

        TestModel.objects.create(int_field=1)
        TestModel.objects.create(int_field=2)

        print(id_dict(TestModel.objects.all()))

    """
    return {obj.pk: obj for obj in queryset}


def _get_upserts(queryset, model_objs_updated, model_objs_created, unique_fields):
    """
    Given a list of model objects that were updated and model objects that were created,
    return the list of all model objects upserted. Doing this requires fetching all of
    the models created with bulk create (since django can't return bulk_create pks)
    """
    # The upserted models default to the objects that were updated
    upserted_models = model_objs_updated
    # Fetch the objects that were created based on the uniqueness constraint. Note - only support the case
    # where there is one update field so that we can perform an in query. TODO perform an OR query to gather
    # the created values when there is more than one update field
    if len(unique_fields) == 1:
        unique_field = unique_fields[0]
        upserted_models.extend(
            queryset.filter(**{'{0}__in'.format(unique_field): (
                getattr(model_obj, unique_field) for model_obj in model_objs_created
            )})
        )
    else:
        raise NotImplementedError(
            'bulk_upsert currently doesnt support returning upserts with more than one update field')

    return upserted_models


def _get_model_objs_to_update_and_create(model_objs, unique_fields, update_fields, extant_model_objs):
    """
    Used by bulk_upsert to gather lists of models that should be updated and created.
    """

    # Find all of the objects to update and all of the objects to create
    model_objs_to_update, model_objs_to_create = list(), list()
    for model_obj in model_objs:
        extant_model_obj = extant_model_objs.get(tuple(getattr(model_obj, field) for field in unique_fields), None)
        if extant_model_obj is None:
            # If the object needs to be created, make a new instance of it
            model_objs_to_create.append(model_obj)
        else:
            # If the object needs to be updated, update its fields
            for field in update_fields:
                setattr(extant_model_obj, field, getattr(model_obj, field))
            model_objs_to_update.append(extant_model_obj)

    return model_objs_to_update, model_objs_to_create


def bulk_upsert(queryset, model_objs, unique_fields, update_fields=None, return_upserts=False, sync=False):
    """
    Performs a bulk update or insert on a list of model objects. Matches all objects in the queryset
    with the objs provided using the field values in unique_fields.
    If an existing object is matched, it is updated with the values from the provided objects. Objects
    that don't match anything are bulk inserted.
    A user can provide a list update_fields so that any changed values on those fields will be updated.
    However, if update_fields is not provided, this function reduces down to performing a bulk_create
    on any non extant objects.

    :type model_objs: list of dict
    :param model_objs: A list of dictionaries that have fields corresponding to the model in the manager.

    :type unique_fields: list of str
    :param unique_fields: A list of fields that are used to determine if an object in objs matches a model
            from the queryset.

    :type update_fields: list of str
    :param update_fields: A list of fields used from the objects in objs as fields when updating existing
            models. If None, this function will only perform a bulk create for model_objs that do not
            currently exist in the database.

    :type return_upserts: bool
    :param return_upserts: A flag specifying whether to return the upserted values. If True, this performs
            an additional query to fetch any bulk created values.

    :type sync: bool
    :param sync: A flag specifying whether a sync operation should be applied to the bulk_upsert. If this
            is True, all values in the queryset that were not updated will be deleted such that the
            entire list of model objects is synced to the queryset.

    :signals: Emits a post_bulk_operation when a bulk_update or a bulk_create occurs.

    Examples:

    .. code-block:: python

        # Start off with no objects in the database. Call a bulk_upsert on the TestModel, which includes
        # a char_field, int_field, and float_field
        bulk_upsert(TestModel.objects.all(), [
            TestModel(float_field=1.0, char_field='1', int_field=1),
            TestModel(float_field=2.0, char_field='2', int_field=2),
            TestModel(float_field=3.0, char_field='3', int_field=3),
        ], ['int_field'], ['char_field'])

        # All objects should have been created
        print(TestModel.objects.count())
        3

        # Now perform a bulk upsert on all the char_field values. Since the objects existed previously
        # (known by the int_field uniqueness constraint), the char fields should be updated
        bulk_upsert(TestModel.objects.all(), [
            TestModel(float_field=1.0, char_field='0', int_field=1),
            TestModel(float_field=2.0, char_field='0', int_field=2),
            TestModel(float_field=3.0, char_field='0', int_field=3),
        ], ['int_field'], ['char_field'])

        # No more new objects should have been created, and every char field should be 0
        print(TestModel.objects.count(), TestModel.objects.filter(char_field='-1').count())
        3, 3

        # Do the exact same operation, but this time add an additional object that is not already
        # stored. It will be inserted.
        bulk_upsert(TestModel.objects.all(), [
            TestModel(float_field=1.0, char_field='1', int_field=1),
            TestModel(float_field=2.0, char_field='2', int_field=2),
            TestModel(float_field=3.0, char_field='3', int_field=3),
            TestModel(float_field=4.0, char_field='4', int_field=4),
        ], ['int_field'], ['char_field'])

        # There should be one more object
        print(TestModel.objects.count())
        4

        # Note that one can also do the upsert on a queryset. Perform the same data upsert on a
        # filter for int_field=1. In this case, only one object has the ability to be updated.
        # All of the other objects will be inserted
        bulk_upsert(TestModel.objects.filter(int_field=1), [
            TestModel(float_field=1.0, char_field='1', int_field=1),
            TestModel(float_field=2.0, char_field='2', int_field=2),
            TestModel(float_field=3.0, char_field='3', int_field=3),
            TestModel(float_field=4.0, char_field='4', int_field=4),
        ], ['int_field'], ['char_field'])

        # There should be three more objects
        print(TestModel.objects.count())
        7

    """
    if not unique_fields:
        raise ValueError('Must provide unique_fields argument')
    update_fields = update_fields or []

    # Create a look up table for all of the objects in the queryset keyed on the unique_fields
    extant_model_objs = {
        tuple(getattr(extant_model_obj, field) for field in unique_fields): extant_model_obj
        for extant_model_obj in queryset
    }

    # Find all of the objects to update and all of the objects to create
    model_objs_to_update, model_objs_to_create = _get_model_objs_to_update_and_create(
        model_objs, unique_fields, update_fields, extant_model_objs)

    # Find all objects in the queryset that will not be updated. These will be deleted if the sync option is
    # True
    if sync:
        model_objs_to_update_set = frozenset(model_objs_to_update)
        model_objs_to_delete = [
            model_obj.pk for model_obj in extant_model_objs.values() if model_obj not in model_objs_to_update_set
        ]
        if model_objs_to_delete:
            queryset.filter(pk__in=model_objs_to_delete).delete()

    # Apply bulk updates and creates
    if update_fields:
        bulk_update(queryset.model.objects, model_objs_to_update, update_fields)
    queryset.model.objects.bulk_create(model_objs_to_create)

    # Optionally return the bulk upserted values
    if return_upserts:
        return _get_upserts(queryset, model_objs_to_update, model_objs_to_create, unique_fields)


def sync(queryset, model_objs, unique_fields, update_fields=None):
    """
    Performs a sync operation on a queryset, making the contents of the
    queryset match the contents of model_objs.

    This function calls bulk_upsert underneath the hood with sync=True.

    :type model_objs: list of :class:`Models<django:django.db.models.Model>`
    :param model_objs: The models to sync

    :type update_fields: list of str
    :param unique_fields: A list of fields that are used to determine if an
            object in objs matches a model from the queryset.

    :type update_fields: list of str
    :param update_fields: A list of fields used from the objects in objs as fields when updating existing
            models. If None, this function will only perform a bulk create for model_objs that do not
            currently exist in the database.

    """
    return bulk_upsert(queryset, model_objs, unique_fields, update_fields=update_fields, sync=True)


def get_or_none(queryset, **query_params):
    """
    Get an object or return None if it doesn't exist.

    :param \*\*query_params: The query parameters used in the lookup.

    :returns: A model object if one exists with the query params, None otherwise.

    Examples:

    .. code-block:: python

        model_obj = get_or_none(TestModel.objects, int_field=1)
        print(model_obj)
        None

        TestModel.objects.create(int_field=1)
        model_obj = get_or_none(TestModel.objects, int_field=1)
        print(model_obj.int_field)
        1

    """
    try:
        obj = queryset.get(**query_params)
    except queryset.model.DoesNotExist:
        obj = None
    return obj


def single(queryset):
    """
    Assumes that this model only has one element in the table and returns it.
    If the table has more than one or no value, an exception is raised.

    :returns: The only model object in the queryset.

    :raises: :class:`DoesNotExist <django:django.core.exceptions.ObjectDoesNotExist>`
            error when the object does not exist or a
            :class:`MultipleObjectsReturned <django:django.core.exceptions.MultipleObjectsReturned>`
            error when thereis more than one object.

    Examples:

    .. code-block:: python

        TestModel.objects.create(int_field=1)
        model_obj = single(TestModel.objects)
        print(model_obj.int_field)
        1

    """
    return queryset.get()


def bulk_update(manager, model_objs, fields_to_update):
    """
    Bulk updates a list of model objects that are already saved.

    :type model_objs: list of :class:`Models<django:django.db.models.Model>`
    :param model_objs: A list of model objects that have been updated.
        fields_to_update: A list of fields to be updated. Only these fields will be updated


    :signals: Emits a post_bulk_operation signal when completed.

    Examples:

    .. code-block:: python

        # Create a couple test models
        model_obj1 = TestModel.objects.create(int_field=1, float_field=2.0, char_field='Hi')
        model_obj2 = TestModel.objects.create(int_field=3, float_field=4.0, char_field='Hello')

        # Change their fields and do a bulk update
        model_obj1.int_field = 10
        model_obj1.float_field = 20.0
        model_obj2.int_field = 30
        model_obj2.float_field = 40.0
        bulk_update(TestModel.objects, [model_obj1, model_obj2], ['int_field', 'float_field'])

        # Reload the models and view their changes
        model_obj1 = TestModel.objects.get(id=model_obj1.id)
        print(model_obj1.int_field, model_obj1.float_field)
        10, 20.0

        model_obj2 = TestModel.objects.get(id=model_obj2.id)
        print(model_obj2.int_field, model_obj2.float_field)
        10, 20.0

    """
    updated_rows = [
        [model_obj.pk] + [getattr(model_obj, field_name) for field_name in fields_to_update]
        for model_obj in model_objs
    ]
    if len(updated_rows) == 0 or len(fields_to_update) == 0:
        return

    # Execute the bulk update
    Query().from_table(
        table=manager.model,
        fields=chain([manager.model._meta.pk.attname] + fields_to_update),
    ).update(updated_rows)

    post_bulk_operation.send(sender=manager, model=manager.model)


def upsert(manager, defaults=None, updates=None, **kwargs):
    """
    Performs an update on an object or an insert if the object does not exist.

    :type defaults: dict
    :param defaults: These values are set when the object is inserted, but are irrelevant
            when the object already exists. This field should only be used when values only need to
            be set during creation.

    :type updates: dict
    :param updates: These values are updated when the object is updated. They also override any
            values provided in the defaults when inserting the object.

    :param \*\*kwargs: These values provide the arguments used when checking for the existence of
            the object. They are used in a similar manner to Django's get_or_create function.

    :returns: A tuple of the upserted object and a Boolean that is True if it was created (False otherwise)

    Examples:

    .. code-block:: python

        # Upsert a test model with an int value of 1. Use default values that will be given to it when created
        model_obj, created = upsert(TestModel.objects, int_field=1, defaults={'float_field': 2.0})
        print(created)
        True
        print(model_obj.int_field, model_obj.float_field)
        1, 2.0

        # Do an upsert on that same model with different default fields. Since it already exists, the defaults
        # are not used
        model_obj, created = upsert(TestModel.objects, int_field=1, defaults={'float_field': 3.0})
        print(created)
        False
        print(model_obj.int_field, model_obj.float_field)
        1, 2.0

        # In order to update the float field in an existing object, use the updates dictionary
        model_obj, created = upsert(TestModel.objects, int_field=1, updates={'float_field': 3.0})
        print(created)
        False
        print(model_obj.int_field, model_obj.float_field)
        1, 3.0

        # You can use updates on a newly created object that will also be used as initial values.
        model_obj, created = upsert(TestModel.objects, int_field=2, updates={'float_field': 4.0})
        print(created)
        True
        print(model_obj.int_field, model_obj.float_field)
        2, 4.0

    """
    defaults = defaults or {}
    # Override any defaults with updates
    defaults.update(updates or {})

    # Do a get or create
    obj, created = manager.model.objects.get_or_create(defaults=defaults, **kwargs)

    # Update any necessary fields
    if updates is not None and not created and any(getattr(obj, k) != updates[k] for k in updates):
        for k, v in updates.items():
            setattr(obj, k, v)
        obj.save(update_fields=updates)

    return obj, created


class ManagerUtilsQuerySet(QuerySet):
    """
    Defines the methods in the manager utils that can also be applied to querysets.
    """
    def id_dict(self):
        return id_dict(self)

    def bulk_upsert(self, model_objs, unique_fields, update_fields=None, return_upserts=False):
        return bulk_upsert(self, model_objs, unique_fields, update_fields=update_fields, return_upserts=return_upserts)

    def sync(self, model_objs, unique_fields, update_fields=None):
        return sync(self, model_objs, unique_fields, update_fields=update_fields)

    def get_or_none(self, **query_params):
        return get_or_none(self, **query_params)

    def single(self):
        return single(self)

    def update(self, **kwargs):
        """
        Overrides Django's update method to emit a post_bulk_operation signal when it completes.
        """
        ret_val = super(ManagerUtilsQuerySet, self).update(**kwargs)
        post_bulk_operation.send(sender=self, model=self.model)
        return ret_val


class ManagerUtilsMixin(object):
    """
    A mixin that can be used by django model managers. It provides additional functionality on top
    of the regular Django Manager class.
    """
    def get_queryset(self):
        return ManagerUtilsQuerySet(self.model)

    def id_dict(self):
        return id_dict(self.get_queryset())

    def bulk_upsert(self, model_objs, unique_fields, update_fields=None, return_upserts=False):
        return bulk_upsert(
            self.get_queryset(), model_objs, unique_fields, update_fields=update_fields, return_upserts=return_upserts)

    def sync(self, model_objs, unique_fields, update_fields=None):
        return sync(self.get_queryset(), model_objs, unique_fields, update_fields=update_fields)

    def bulk_create(self, model_objs, batch_size=None):
        """
        Overrides Django's bulk_create function to emit a post_bulk_operation signal when bulk_create
        is finished.
        """
        ret_val = super(ManagerUtilsMixin, self).bulk_create(model_objs, batch_size=batch_size)
        post_bulk_operation.send(sender=self, model=self.model)
        return ret_val

    def bulk_update(self, model_objs, fields_to_update):
        return bulk_update(self.get_queryset(), model_objs, fields_to_update)

    def upsert(self, defaults=None, updates=None, **kwargs):
        return upsert(self.get_queryset(), defaults=defaults, updates=updates, **kwargs)

    def get_or_none(self, **query_params):
        return get_or_none(self.get_queryset(), **query_params)

    def single(self):
        return single(self.get_queryset())


class ManagerUtilsManager(ManagerUtilsMixin, Manager):
    """
    A class that can be used as a manager. It already inherits the Django Manager class and adds
    the mixin.
    """
    pass
