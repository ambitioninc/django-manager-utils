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

    def bulk_upsert(self, model_objs, unique_fields, update_fields):
        """
        Performs a bulk update or insert on a queryset.
        """
        if not unique_fields:
            raise ValueError('Must provide unique_fields argument')
        if not update_fields:
            raise ValueError('Must provide update_fields argument')

        # Create a look up table for all of the objects in the queryset keyed on the unique_fields
        extant_model_objs = {
            tuple(getattr(extant_model_obj, field) for field in unique_fields): extant_model_obj
            for extant_model_obj in self
        }

        # Find all of the objects to update and all of the objects to create
        model_objs_to_update, model_objs_to_create = [], []
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

        # Apply bulk updates and creates
        self.model.objects.bulk_update(model_objs_to_update, update_fields)
        self.model.objects.bulk_create(model_objs_to_create)

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

    def bulk_upsert(self, model_objs, unique_fields, update_fields):
        """
        Performs a bulk update or insert on a list of model objects. Matches all objects in the queryset
        with the objs provided using the field values in unique_fields.
        If an existing object is matched, it is updated with the values from the provided objects. Objects
        that don't match anything are bulk inserted.

        Args:
            objs: A list of dictionaries that have fields corresponding to the model in the manager.
            unique_fields: A list of fields that are used to determine if an object in objs matches a model
                from the queryset.
            update_fields: A list of fields used from the objects in objs as fields when updating existing
                models.

        Signals: Emits a post_bulk_operation when a bulk_update or a bulk_create occurs.

        Examples:
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
        """
        return self.get_queryset().bulk_upsert(model_objs, unique_fields, update_fields)

    def bulk_create(self, model_objs, batch_size=None):
        """
        Overrides Django's bulk_create function to emit a post_bulk_operation signal when bulk_create
        is finished.
        """
        ret_val = super(ManagerUtilsMixin, self).bulk_create(model_objs, batch_size=batch_size)
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
                the object. They are used in a similar manner to Django's get_or_create function.

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
        defaults = defaults or {}
        # Override any defaults with updates
        defaults.update(updates or {})

        # Do a get or create
        obj, created = self.model.objects.get_or_create(defaults=defaults, **kwargs)

        # Update any necessary fields
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
