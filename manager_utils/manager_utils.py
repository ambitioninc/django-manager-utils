from itertools import chain

from django.db.models import Manager
from django.db.models.query import QuerySet
from django.dispatch import Signal
from querybuilder.query import Query


# A signal that is emitted when any bulk operation occurs
post_bulk_operation = Signal(providing_args=['model'])


class ManagerUtilsQuerySet(QuerySet):
    """
    Defines the methods in the manager utils that can also be applied to querysets.
    """
    def id_dict(self):
        """
        Returns a dictionary of all the objects keyed on their id.
        """
        return {obj.id: obj for obj in self}

    def get_or_none(self, **query_params):
        """
        Get an object or return None if it doesn't exist.

        Returns:
            A model object if one exists with the query params, None otherwise.
        """
        try:
            obj = self.get(**query_params)
        except self.model.DoesNotExist:
            obj = None
        return obj

    def single(self):
        """
        Assumes that this model only has one element in the table and returns it. If the table has more
        than one or no value, an exception is raised.
        """
        return self.get()

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
        """
        Returns a dictionary of all the objects keyed on their ID.

        Returns:
            A dictionary of objects from the queryset or manager that is keyed on the objects' IDs.

        Examples:

            TestModel.objects.create(int_field=1)
            TestModel.objects.create(int_field=2)

            print TestModel.objects.id_dict()

        """
        return self.get_queryset().id_dict()

    def bulk_create(self, objs, batch_size=None):
        """
        Overrides Django's bulk_create function to emit a post_bulk_operation signal when bulk_create
        is finished.
        """
        ret_val = super(ManagerUtilsMixin, self).bulk_create(objs, batch_size=batch_size)
        post_bulk_operation.send(sender=self, model=self.model)
        return ret_val

    def bulk_update(self, model_objs, fields_to_update):
        """
        Bulk updates a list of model objects that are already saved.

        Args:
            model_objs: A list of model objects that have been updated.
            fields_to_update: A list of fields to be updated. Only these fields will be updated

        Sianals: Emits a post_bulk_operation signal when completed.

        Examples:
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
        """
        updated_rows = [
            [model_obj.id] + [getattr(model_obj, field_name) for field_name in fields_to_update]
            for model_obj in model_objs
        ]
        if len(updated_rows) == 0 or len(fields_to_update) == 0:
            return

        # Execute the bulk update
        Query().from_table(
            table=self.model,
            fields=chain(['id'] + fields_to_update),
        ).update(updated_rows)

        post_bulk_operation.send(sender=self, model=self.model)

    def upsert(self, defaults=None, updates=None, **kwargs):
        """
        Performs an update on an object or an insert if the object does not exist.
        Args:
            defaults: These values are set when the object is inserted, but are irrelevant
                when the object already exists. This field should only be used when values only need to
                be set during creation.
            updates: These values are updated when the object is updated. They also override any
                values provided in the defaults when inserting the object.
            **kwargs: These values provide the arguments used when checking for the existence of
                the object.  They are used in a similar manner to Django's get_or_create function.

        Returns: A tuple of the upserted object and a Boolean that is True if it was created (False otherwise)

        Examples:
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
        """
        obj, created = self.model.objects.get_or_create(defaults=defaults or {}, **kwargs)

        if updates is not None:
            for k, v in updates.iteritems():
                setattr(obj, k, v)
            obj.save(update_fields=updates)

        return obj, created

    def get_or_none(self, **query_params):
        """
        Get an object or return None if it doesn't exist.

        Args:
            **query_params: The query parameters used in the lookup.

        Returns: A model object if one exists with the query params, None otherwise.

        Examples:
            model_obj = TestModel.objects.get_or_none(int_field=1)
            print model_obj
            None

            TestModel.objects.create(int_field=1)
            model_obj = TestModel.objects.get_or_none(int_field=1)
            print model_obj.int_field
            1
        """
        return self.get_queryset().get_or_none(**query_params)

    def single(self):
        """
        Assumes that this model only has one element in the table and returns it. If the table has more
        than one or no value, an exception is raised.

        Returns: The only model object in the queryset.

        Raises: DoesNotExist error when the object does not exist or a MultipleObjectsReturned error when there
            is more than one object.

        Examples:
            TestModel.objects.create(int_field=1)
            model_obj = TestModel.objects.single()
            print model_obj.int_field
            1
        """
        return self.get_queryset().single()


class ManagerUtilsManager(ManagerUtilsMixin, Manager):
    """
    A class that can be used as a manager. It already inherits the Django Manager class and adds
    the mixin.
    """
    pass
