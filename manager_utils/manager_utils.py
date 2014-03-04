from itertools import chain

from django.db.models import QuerySet
from querybuilder.query import Query


class ManagerUtilsQuerySet(QuerySet):
    """
    Defines the methods in the manager utils that can also be applied to querysets.
    """
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
        return self.get(id__gte=0)


class ManagerUtilsMixin(object):
    """
    A mixin that can be used by django model managers. It provides additional functionality on top
    of the regular Django Manager class.
    """
    def get_queryset(self):
        return ManagerUtilsQuerySet(self.model)

    def bulk_update(self, model_objs, fields_to_update):
        """
        Bulk updates a list of model objects that are already saved.

        Args:
            model_objs: A list of model objects that have been updated.
            fields_to_update: A list of fields to be updated. Only these fields will be updated
        """
        updated_rows = [
            chain((model_obj.id,), (getattr(model_obj, field_name) for field_name in fields_to_update))
            for model_obj in model_objs
        ]
        if len(updated_rows) == 0:
            return

        # Execute the bulk update
        Query().from_table(
            table=self.model,
            fields=chain(('id',), fields_to_update),
        ).update(updated_rows)

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
                the object.
        """
        obj, created = self.model.objects.get_or_create(defaults=defaults, **kwargs)

        if updates is not None:
            for k, v in updates.iteritems():
                setattr(obj, k, v)
            obj.save(update_fields=updates)

        return obj, created

    def get_or_none(self, **query_params):
        """
        Get an object or return None if it doesn't exist.

        Returns:
            A model object if one exists with the query params, None otherwise.
        """
        return self.get_queryset().get_or_none(**query_params)

    def single(self):
        """
        Assumes that this model only has one element in the table and returns it. If the table has more
        than one or no value, an exception is raised.
        """
        return self.get_queryset().single()
