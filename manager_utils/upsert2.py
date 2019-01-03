"""
The new interface for manager utils upsert
"""
from collections import namedtuple

from django.db import connection, models
from django.utils import timezone


def _quote(field):
    return '"{0}"'.format(field)


def _get_update_fields(model, uniques, to_update):
    """
    Get the fields to be updated in an upsert.

    Always exclude auto_now_add, auto_created fields, and unique fields in an update
    """
    fields = {
        field.attname: field
        for field in model._meta.fields
    }

    if to_update is None:
        to_update = [
            field.attname for field in model._meta.fields
        ]

    to_update = [
        attname for attname in to_update
        if (attname not in uniques
            and not getattr(fields[attname], 'auto_now_add', False)
            and not fields[attname].auto_created)
    ]

    return to_update


def _fill_auto_fields(model, values):
    """
    Given a list of models, fill in auto_now and auto_now_add fields
    for upserts. Since django manager utils passes Django's ORM, these values
    have to be automatically constructed
    """
    auto_field_names = [
        f.attname
        for f in model._meta.fields
        if getattr(f, 'auto_now', False) or getattr(f, 'auto_now_add', False)
    ]
    now = timezone.now()
    for value in values:
        for f in auto_field_names:
            setattr(value, f, now)

    return values


def _sort_by_unique_fields(model, model_objs, unique_fields):
    """
    Sort a list of models by their unique fields.

    Sorting models in an upsert greatly reduces the chances of deadlock
    when doing concurrent upserts
    """
    unique_fields = [
        field for field in model._meta.fields
        if field.attname in unique_fields
    ]

    def sort_key(model_obj):
        return tuple(
            field.get_db_prep_save(getattr(model_obj, field.attname),
                                   connection)
            for field in unique_fields
        )
    return sorted(model_objs, key=sort_key)


def _get_upsert_sql(queryset, model_objs, unique_fields, update_fields, returning):
    """
    Generates the postgres specific sql necessary to perform an upsert (ON CONFLICT)
    INSERT INTO table_name (field1, field2)
    VALUES (1, 'two')
    ON CONFLICT (unique_field) DO UPDATE SET field2 = EXCLUDED.field2;
    """
    model = queryset.model

    # Use all fields except pk unless the uniqueness constraint is the pk field
    all_fields = [
        field for field in model._meta.fields
        if field.column != model._meta.pk.name or not field.auto_created
    ]

    all_field_names = [field.column for field in all_fields]
    all_field_names_sql = ', '.join([_quote(field) for field in all_field_names])

    # Convert field names to db column names
    unique_fields = [
        model._meta.get_field(unique_field)
        for unique_field in unique_fields
    ]
    update_fields = [
        model._meta.get_field(update_field)
        for update_field in update_fields
    ]

    unique_field_names_sql = ', '.join([
        _quote(field.column) for field in unique_fields
    ])
    update_fields_sql = ', '.join([
        '{0} = EXCLUDED.{0}'.format(_quote(field.column))
        for field in update_fields
    ])

    row_values = []
    sql_args = []

    for model_obj in model_objs:
        placeholders = []
        for field in all_fields:
            # Convert field value to db value
            # Use attname here to support fields with custom db_column names
            sql_args.append(field.get_db_prep_save(getattr(model_obj, field.attname),
                                                   connection))
            placeholders.append('%s')
        row_values.append('({0})'.format(', '.join(placeholders)))
    row_values_sql = ', '.join(row_values)

    return_sql = ''
    if returning:
        action_sql = ', (xmax = 0) AS inserted_'
        if returning is True:
            return_sql = 'RETURNING * {action_sql}'.format(action_sql=action_sql)
        else:
            return_fields_sql = ', '.join(_quote(field) for field in returning)
            return_sql = 'RETURNING {return_fields_sql} {action_sql}'.format(return_fields_sql=return_fields_sql,
                                                                             action_sql=action_sql)

    if update_fields:
        sql = (
            'INSERT INTO {0} ({1}) VALUES {2} ON CONFLICT ({3}) DO UPDATE SET {4} {5}'
        ).format(
            model._meta.db_table,
            all_field_names_sql,
            row_values_sql,
            unique_field_names_sql,
            update_fields_sql,
            return_sql
        )
    else:
        sql = (
            'INSERT INTO {0} ({1}) VALUES {2} ON CONFLICT ({3}) {4} {5}'
        ).format(
            model._meta.db_table,
            all_field_names_sql,
            row_values_sql,
            unique_field_names_sql,
            'DO UPDATE SET {0}=EXCLUDED.{0}'.format(unique_fields[0].column),
            return_sql
        )

    return sql, sql_args


def _fetch(queryset, model_objs, unique_fields, update_fields, returning, sync):
    """
    Perfom the upsert and do an optional sync operation
    """
    model = queryset.model
    upserted = []
    deleted = []
    if model_objs:
        sql, sql_args = _get_upsert_sql(queryset, model_objs, unique_fields, update_fields, returning)

        with connection.cursor() as cursor:
            cursor.execute(sql, sql_args)
            if cursor.description:
                nt_result = namedtuple('Result', [col[0] for col in cursor.description])
                upserted = [nt_result(*row) for row in cursor.fetchall()]

    pk_field = model._meta.pk.name
    if sync:
        orig_ids = queryset.values_list(pk_field, flat=True)
        deleted = set(orig_ids) - {getattr(r, pk_field) for r in upserted}
        model.objects.filter(pk__in=deleted).delete()

    nt_deleted_result = namedtuple('DeletedResult', [model._meta.pk.name])
    return (
        [r for r in upserted if r.inserted_],
        [r for r in upserted if not r.inserted_],
        [nt_deleted_result(**{pk_field: d}) for d in deleted]
    )


def upsert(
    queryset, model_objs, unique_fields,
    update_fields=None, returning=False, sync=False
):
    """
    Perform a bulk upsert on a table, optionally syncing the results.

    Args:
        queryset (Model|QuerySet): A model or a queryset that defines the collection to sync
        model_objs (List[Model]): A list of Django models to sync. All models in this list
            will be bulk upserted and any models not in the table (or queryset) will be deleted
            if sync=True.
        unique_fields (List[str]): A list of fields that define the uniqueness of the model. The
            model must have a unique constraint on these fields
        update_fields (List[str], default=None): A list of fields to update whenever objects
            already exist. If an empty list is provided, it is equivalent to doing a bulk
            insert on the objects that don't exist. If `None`, all fields will be updated.
        returning (bool|List[str]): If True, returns all fields. If a list, only returns
            fields in the list
        sync (bool, default=False): Perform a sync operation on the queryset
    """
    queryset = queryset if isinstance(queryset, models.QuerySet) else queryset.objects.all()
    model = queryset.model

    # Populate automatically generated fields in the rows like date times
    _fill_auto_fields(model, model_objs)

    # Sort the rows to reduce the chances of deadlock during concurrent upserts
    model_objs = _sort_by_unique_fields(model, model_objs, unique_fields)
    update_fields = _get_update_fields(model, unique_fields, update_fields)

    if sync and returning is not True:
        returning = set(returning) if returning else set()
        returning.add(model._meta.pk.name)

    return _fetch(queryset, model_objs, unique_fields, update_fields, returning, sync)
