"""
The new interface for manager utils upsert
"""
from collections import namedtuple

from django.db import connection, models
from django.utils import timezone


class UpsertResult(list):
    """
    Returned by the upsert operation.

    Wraps a list and provides properties to access created, updated,
    untouched, and deleted elements
    """
    @property
    def created(self):
        return (i for i in self if i.status_ == 'c')

    @property
    def updated(self):
        return (i for i in self if i.status_ == 'u')

    @property
    def untouched(self):
        return (i for i in self if i.status_ == 'n')

    @property
    def deleted(self):
        return (i for i in self if i.status_ == 'd')


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


def _get_values_for_row(model_obj, all_fields):
    return [
        # Convert field value to db value
        # Use attname here to support fields with custom db_column names
        field.get_db_prep_save(getattr(model_obj, field.attname), connection)
        for field in all_fields
    ]


def _get_values_for_rows(model_objs, all_fields):
    row_values = []
    sql_args = []

    for i, model_obj in enumerate(model_objs):
        sql_args.extend(_get_values_for_row(model_obj, all_fields))
        if i == 0:
            row_values.append('({0})'.format(
                ', '.join(['%s::{0}'.format(f.db_type(connection)) for f in all_fields]))
            )
        else:
            row_values.append('({0})'.format(', '.join(['%s'] * len(all_fields))))

    return row_values, sql_args


def _get_return_fields_sql(returning, return_status=False, alias=None):
    if alias:
        return_fields_sql = ', '.join('{0}.{1}'.format(alias, _quote(field)) for field in returning)
    else:
        return_fields_sql = ', '.join(_quote(field) for field in returning)

    if return_status:
        return_fields_sql += ', CASE WHEN xmax = 0 THEN \'c\' ELSE \'u\' END AS status_'

    return return_fields_sql


def _get_upsert_sql(queryset, model_objs, unique_fields, update_fields, returning,
                    ignore_duplicate_updates=True, return_untouched=False):
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
    returning = returning if returning is not True else [f.column for f in model._meta.fields]
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

    row_values, sql_args = _get_values_for_rows(model_objs, all_fields)

    return_sql = 'RETURNING ' + _get_return_fields_sql(returning, return_status=True) if returning else ''
    ignore_duplicates_sql = ''
    if ignore_duplicate_updates:
        ignore_duplicates_sql = (
            ' WHERE ({update_fields_sql}) IS DISTINCT FROM ({excluded_update_fields_sql}) '
        ).format(
            update_fields_sql=', '.join(
                '{0}.{1}'.format(model._meta.db_table, _quote(field.column))
                for field in update_fields
            ),
            excluded_update_fields_sql=', '.join(
                'EXCLUDED.' + _quote(field.column)
                for field in update_fields
            )
        )

    on_conflict = (
        'DO UPDATE SET {0} {1}'.format(update_fields_sql, ignore_duplicates_sql) if update_fields else 'DO NOTHING'
    )

    if return_untouched:
        row_values_sql = ', '.join([
            '(\'{0}\', {1})'.format(i, row_value[1:-1])
            for i, row_value in enumerate(row_values)
        ])
        sql = (
            ' WITH input_rows("temp_id_", {all_field_names_sql}) AS ('
            '     VALUES {row_values_sql}'
            ' ), ins AS ( '
            '     INSERT INTO {table_name} ({all_field_names_sql})'
            '     SELECT {all_field_names_sql} FROM input_rows ORDER BY temp_id_'
            '     ON CONFLICT ({unique_field_names_sql}) {on_conflict} {return_sql}'
            ' )'
            ' SELECT DISTINCT ON ({table_pk_name}) * FROM ('
            '     SELECT status_, {return_fields_sql}'
            '     FROM   ins'
            '     UNION  ALL'
            '     SELECT \'n\' AS status_, {aliased_return_fields_sql}'
            '     FROM input_rows'
            '     JOIN {table_name} c USING ({unique_field_names_sql})'
            ' ) as results'
            ' ORDER BY results."{table_pk_name}", CASE WHEN(status_ = \'n\') THEN 1 ELSE 0 END;'
        ).format(
            all_field_names_sql=all_field_names_sql,
            row_values_sql=row_values_sql,
            table_name=model._meta.db_table,
            unique_field_names_sql=unique_field_names_sql,
            on_conflict=on_conflict,
            return_sql=return_sql,
            table_pk_name=model._meta.pk.name,
            return_fields_sql=_get_return_fields_sql(returning),
            aliased_return_fields_sql=_get_return_fields_sql(returning, alias='c')
        )
    else:
        row_values_sql = ', '.join(row_values)
        sql = (
            ' INSERT INTO {table_name} ({all_field_names_sql})'
            ' VALUES {row_values_sql}'
            ' ON CONFLICT ({unique_field_names_sql}) {on_conflict} {return_sql}'
        ).format(
            table_name=model._meta.db_table,
            all_field_names_sql=all_field_names_sql,
            row_values_sql=row_values_sql,
            unique_field_names_sql=unique_field_names_sql,
            on_conflict=on_conflict,
            return_sql=return_sql
        )

    return sql, sql_args


def _fetch(
    queryset, model_objs, unique_fields, update_fields, returning, sync,
    ignore_duplicate_updates=True, return_untouched=False
):
    """
    Perfom the upsert and do an optional sync operation
    """
    model = queryset.model
    if (return_untouched or sync) and returning is not True:
        returning = set(returning) if returning else set()
        returning.add(model._meta.pk.name)
    upserted = []
    deleted = []
    # We must return untouched rows when doing a sync operation
    return_untouched = True if sync else return_untouched

    if model_objs:
        sql, sql_args = _get_upsert_sql(queryset, model_objs, unique_fields, update_fields, returning,
                                        ignore_duplicate_updates=ignore_duplicate_updates,
                                        return_untouched=return_untouched)

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

    nt_deleted_result = namedtuple('DeletedResult', [model._meta.pk.name, 'status_'])
    return UpsertResult(
        upserted + [nt_deleted_result(**{pk_field: d, 'status_': 'd'}) for d in deleted]
    )


def upsert(
    queryset, model_objs, unique_fields,
    update_fields=None, returning=False, sync=False,
    ignore_duplicate_updates=True,
    return_untouched=False
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
        ignore_duplicate_updates (bool, default=False): Don't perform an update if the row is
            a duplicate.
        return_untouched (bool, default=False): Return untouched rows by the operation
    """
    queryset = queryset if isinstance(queryset, models.QuerySet) else queryset.objects.all()
    model = queryset.model

    # Populate automatically generated fields in the rows like date times
    _fill_auto_fields(model, model_objs)

    # Sort the rows to reduce the chances of deadlock during concurrent upserts
    model_objs = _sort_by_unique_fields(model, model_objs, unique_fields)
    update_fields = _get_update_fields(model, unique_fields, update_fields)

    return _fetch(queryset, model_objs, unique_fields, update_fields, returning, sync,
                  ignore_duplicate_updates=ignore_duplicate_updates,
                  return_untouched=return_untouched)
