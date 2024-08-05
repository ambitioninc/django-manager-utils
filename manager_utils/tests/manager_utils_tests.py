import datetime as dt

from django.test import TestCase
from django_dynamic_fixture import G
import freezegun
from manager_utils import post_bulk_operation
from manager_utils.manager_utils import _get_prepped_model_field
from unittest.mock import patch
from parameterized import parameterized
from pytz import timezone

from manager_utils.tests import models


class TestGetPreppedModelField(TestCase):
    def test_invalid_field(self):
        t = models.TestModel()
        with self.assertRaises(Exception):
            _get_prepped_model_field(t, 'non_extant_field')


class SyncTest(TestCase):
    """
    Tests the sync function.
    """
    @parameterized.expand([(True,), (False,)])
    def test_w_char_pk(self, native):
        """
        Tests with a model that has a char pk.
        """
        extant_obj1 = G(models.TestPkChar, my_key='1', char_field='1')
        extant_obj2 = G(models.TestPkChar, my_key='2', char_field='1')
        extant_obj3 = G(models.TestPkChar, my_key='3', char_field='1')

        models.TestPkChar.objects.sync([
            models.TestPkChar(my_key='3', char_field='2'), models.TestPkChar(my_key='4', char_field='2'),
            models.TestPkChar(my_key='5', char_field='2')
        ], ['my_key'], ['char_field'], native=native)

        self.assertEqual(models.TestPkChar.objects.count(), 3)
        self.assertTrue(models.TestPkChar.objects.filter(my_key='3').exists())
        self.assertTrue(models.TestPkChar.objects.filter(my_key='4').exists())
        self.assertTrue(models.TestPkChar.objects.filter(my_key='5').exists())

        with self.assertRaises(models.TestPkChar.DoesNotExist):
            models.TestPkChar.objects.get(pk=extant_obj1.pk)
        with self.assertRaises(models.TestPkChar.DoesNotExist):
            models.TestPkChar.objects.get(pk=extant_obj2.pk)
        test_model = models.TestPkChar.objects.get(pk=extant_obj3.pk)
        self.assertEqual(test_model.char_field, '2')

    @parameterized.expand([(True,), (False,)])
    def test_no_existing_objs(self, native):
        """
        Tests when there are no existing objects before the sync.
        """
        models.TestModel.objects.sync([
            models.TestModel(int_field=1), models.TestModel(int_field=3),
            models.TestModel(int_field=4)
        ], ['int_field'], ['float_field'], native=native)
        self.assertEqual(models.TestModel.objects.count(), 3)
        self.assertTrue(models.TestModel.objects.filter(int_field=1).exists())
        self.assertTrue(models.TestModel.objects.filter(int_field=3).exists())
        self.assertTrue(models.TestModel.objects.filter(int_field=4).exists())

    @parameterized.expand([(True,), (False,)])
    def test_existing_objs_all_deleted(self, native):
        """
        Tests when there are existing objects that will all be deleted.
        """
        extant_obj1 = G(models.TestModel, int_field=1)
        extant_obj2 = G(models.TestModel, int_field=2)
        extant_obj3 = G(models.TestModel, int_field=3)

        models.TestModel.objects.sync([
            models.TestModel(int_field=4), models.TestModel(int_field=5), models.TestModel(int_field=6)
        ], ['int_field'], ['float_field'], native=native)

        self.assertEqual(models.TestModel.objects.count(), 3)
        self.assertTrue(models.TestModel.objects.filter(int_field=4).exists())
        self.assertTrue(models.TestModel.objects.filter(int_field=5).exists())
        self.assertTrue(models.TestModel.objects.filter(int_field=6).exists())

        with self.assertRaises(models.TestModel.DoesNotExist):
            models.TestModel.objects.get(id=extant_obj1.id)
        with self.assertRaises(models.TestModel.DoesNotExist):
            models.TestModel.objects.get(id=extant_obj2.id)
        with self.assertRaises(models.TestModel.DoesNotExist):
            models.TestModel.objects.get(id=extant_obj3.id)

    @parameterized.expand([(True,), (False,)])
    def test_existing_objs_all_deleted_empty_sync(self, native):
        """
        Tests when there are existing objects deleted because of an emtpy sync.
        """
        extant_obj1 = G(models.TestModel, int_field=1)
        extant_obj2 = G(models.TestModel, int_field=2)
        extant_obj3 = G(models.TestModel, int_field=3)

        models.TestModel.objects.sync([], ['int_field'], ['float_field'], native=native)

        self.assertEqual(models.TestModel.objects.count(), 0)
        with self.assertRaises(models.TestModel.DoesNotExist):
            models.TestModel.objects.get(id=extant_obj1.id)
        with self.assertRaises(models.TestModel.DoesNotExist):
            models.TestModel.objects.get(id=extant_obj2.id)
        with self.assertRaises(models.TestModel.DoesNotExist):
            models.TestModel.objects.get(id=extant_obj3.id)

    @parameterized.expand([(True,), (False,)])
    def test_existing_objs_some_deleted(self, native):
        """
        Tests when some existing objects will be deleted.
        """
        extant_obj1 = G(models.TestModel, int_field=1, float_field=1)
        extant_obj2 = G(models.TestModel, int_field=2, float_field=1)
        extant_obj3 = G(models.TestModel, int_field=3, float_field=1)

        models.TestModel.objects.sync([
            models.TestModel(int_field=3, float_field=2), models.TestModel(int_field=4, float_field=2),
            models.TestModel(int_field=5, float_field=2)
        ], ['int_field'], ['float_field'], native=native)

        self.assertEqual(models.TestModel.objects.count(), 3)
        self.assertTrue(models.TestModel.objects.filter(int_field=3).exists())
        self.assertTrue(models.TestModel.objects.filter(int_field=4).exists())
        self.assertTrue(models.TestModel.objects.filter(int_field=5).exists())

        with self.assertRaises(models.TestModel.DoesNotExist):
            models.TestModel.objects.get(id=extant_obj1.id)
        with self.assertRaises(models.TestModel.DoesNotExist):
            models.TestModel.objects.get(id=extant_obj2.id)
        test_model = models.TestModel.objects.get(id=extant_obj3.id)
        self.assertEqual(test_model.int_field, 3)

    @parameterized.expand([(True,), (False,)])
    def test_existing_objs_some_deleted_w_queryset(self, native):
        """
        Tests when some existing objects will be deleted on a queryset
        """
        extant_obj0 = G(models.TestModel, int_field=0, float_field=1)
        extant_obj1 = G(models.TestModel, int_field=1, float_field=1)
        extant_obj2 = G(models.TestModel, int_field=2, float_field=1)
        extant_obj3 = G(models.TestModel, int_field=3, float_field=1)
        extant_obj4 = G(models.TestModel, int_field=4, float_field=0)

        models.TestModel.objects.filter(int_field__lt=4).sync([
            models.TestModel(int_field=1, float_field=2), models.TestModel(int_field=2, float_field=2),
            models.TestModel(int_field=3, float_field=2)
        ], ['int_field'], ['float_field'], native=native)

        self.assertEqual(models.TestModel.objects.count(), 4)
        self.assertTrue(models.TestModel.objects.filter(int_field=1).exists())
        self.assertTrue(models.TestModel.objects.filter(int_field=2).exists())
        self.assertTrue(models.TestModel.objects.filter(int_field=3).exists())

        with self.assertRaises(models.TestModel.DoesNotExist):
            models.TestModel.objects.get(id=extant_obj0.id)

        test_model = models.TestModel.objects.get(id=extant_obj1.id)
        self.assertEqual(test_model.float_field, 2)
        test_model = models.TestModel.objects.get(id=extant_obj2.id)
        self.assertEqual(test_model.float_field, 2)
        test_model = models.TestModel.objects.get(id=extant_obj3.id)
        self.assertEqual(test_model.float_field, 2)
        test_model = models.TestModel.objects.get(id=extant_obj4.id)
        self.assertEqual(test_model.float_field, 0)


class Sync2Test(TestCase):
    """
    Tests the sync2 function.
    """
    def test_w_char_pk(self):
        """
        Tests with a model that has a char pk.
        """
        extant_obj1 = G(models.TestPkChar, my_key='1', char_field='1')
        extant_obj2 = G(models.TestPkChar, my_key='2', char_field='1')
        extant_obj3 = G(models.TestPkChar, my_key='3', char_field='1')

        models.TestPkChar.objects.sync2([
            models.TestPkChar(my_key='3', char_field='2'), models.TestPkChar(my_key='4', char_field='2'),
            models.TestPkChar(my_key='5', char_field='2')
        ], ['my_key'], ['char_field'])

        self.assertEqual(models.TestPkChar.objects.count(), 3)
        self.assertTrue(models.TestPkChar.objects.filter(my_key='3').exists())
        self.assertTrue(models.TestPkChar.objects.filter(my_key='4').exists())
        self.assertTrue(models.TestPkChar.objects.filter(my_key='5').exists())

        with self.assertRaises(models.TestPkChar.DoesNotExist):
            models.TestPkChar.objects.get(pk=extant_obj1.pk)
        with self.assertRaises(models.TestPkChar.DoesNotExist):
            models.TestPkChar.objects.get(pk=extant_obj2.pk)
        test_model = models.TestPkChar.objects.get(pk=extant_obj3.pk)
        self.assertEqual(test_model.char_field, '2')

    def test_no_existing_objs(self):
        """
        Tests when there are no existing objects before the sync.
        """
        models.TestModel.objects.sync([
            models.TestModel(int_field=1), models.TestModel(int_field=3),
            models.TestModel(int_field=4)
        ], ['int_field'], ['float_field'])
        self.assertEqual(models.TestModel.objects.count(), 3)
        self.assertTrue(models.TestModel.objects.filter(int_field=1).exists())
        self.assertTrue(models.TestModel.objects.filter(int_field=3).exists())
        self.assertTrue(models.TestModel.objects.filter(int_field=4).exists())

    def test_existing_objs_all_deleted(self):
        """
        Tests when there are existing objects that will all be deleted.
        """
        extant_obj1 = G(models.TestModel, int_field=1)
        extant_obj2 = G(models.TestModel, int_field=2)
        extant_obj3 = G(models.TestModel, int_field=3)

        models.TestModel.objects.sync2([
            models.TestModel(int_field=4), models.TestModel(int_field=5), models.TestModel(int_field=6)
        ], ['int_field'], ['float_field'])

        self.assertEqual(models.TestModel.objects.count(), 3)
        self.assertTrue(models.TestModel.objects.filter(int_field=4).exists())
        self.assertTrue(models.TestModel.objects.filter(int_field=5).exists())
        self.assertTrue(models.TestModel.objects.filter(int_field=6).exists())

        with self.assertRaises(models.TestModel.DoesNotExist):
            models.TestModel.objects.get(id=extant_obj1.id)
        with self.assertRaises(models.TestModel.DoesNotExist):
            models.TestModel.objects.get(id=extant_obj2.id)
        with self.assertRaises(models.TestModel.DoesNotExist):
            models.TestModel.objects.get(id=extant_obj3.id)

    def test_existing_objs_all_deleted_empty_sync(self):
        """
        Tests when there are existing objects deleted because of an emtpy sync.
        """
        extant_obj1 = G(models.TestModel, int_field=1)
        extant_obj2 = G(models.TestModel, int_field=2)
        extant_obj3 = G(models.TestModel, int_field=3)

        models.TestModel.objects.sync2([], ['int_field'], ['float_field'])

        self.assertEqual(models.TestModel.objects.count(), 0)
        with self.assertRaises(models.TestModel.DoesNotExist):
            models.TestModel.objects.get(id=extant_obj1.id)
        with self.assertRaises(models.TestModel.DoesNotExist):
            models.TestModel.objects.get(id=extant_obj2.id)
        with self.assertRaises(models.TestModel.DoesNotExist):
            models.TestModel.objects.get(id=extant_obj3.id)

    def test_existing_objs_some_deleted(self):
        """
        Tests when some existing objects will be deleted.
        """
        extant_obj1 = G(models.TestModel, int_field=1, float_field=1)
        extant_obj2 = G(models.TestModel, int_field=2, float_field=1)
        extant_obj3 = G(models.TestModel, int_field=3, float_field=1)

        models.TestModel.objects.sync2([
            models.TestModel(int_field=3, float_field=2), models.TestModel(int_field=4, float_field=2),
            models.TestModel(int_field=5, float_field=2)
        ], ['int_field'], ['float_field'])

        self.assertEqual(models.TestModel.objects.count(), 3)
        self.assertTrue(models.TestModel.objects.filter(int_field=3).exists())
        self.assertTrue(models.TestModel.objects.filter(int_field=4).exists())
        self.assertTrue(models.TestModel.objects.filter(int_field=5).exists())

        with self.assertRaises(models.TestModel.DoesNotExist):
            models.TestModel.objects.get(id=extant_obj1.id)
        with self.assertRaises(models.TestModel.DoesNotExist):
            models.TestModel.objects.get(id=extant_obj2.id)
        test_model = models.TestModel.objects.get(id=extant_obj3.id)
        self.assertEqual(test_model.int_field, 3)

    def test_existing_objs_some_deleted_w_queryset(self):
        """
        Tests when some existing objects will be deleted on a queryset
        """
        extant_obj0 = G(models.TestModel, int_field=0, float_field=1)
        extant_obj1 = G(models.TestModel, int_field=1, float_field=1)
        extant_obj2 = G(models.TestModel, int_field=2, float_field=1)
        extant_obj3 = G(models.TestModel, int_field=3, float_field=1)
        extant_obj4 = G(models.TestModel, int_field=4, float_field=0)

        models.TestModel.objects.filter(int_field__lt=4).sync2([
            models.TestModel(int_field=1, float_field=2), models.TestModel(int_field=2, float_field=2),
            models.TestModel(int_field=3, float_field=2)
        ], ['int_field'], ['float_field'])

        self.assertEqual(models.TestModel.objects.count(), 4)
        self.assertTrue(models.TestModel.objects.filter(int_field=1).exists())
        self.assertTrue(models.TestModel.objects.filter(int_field=2).exists())
        self.assertTrue(models.TestModel.objects.filter(int_field=3).exists())

        with self.assertRaises(models.TestModel.DoesNotExist):
            models.TestModel.objects.get(id=extant_obj0.id)

        test_model = models.TestModel.objects.get(id=extant_obj1.id)
        self.assertEqual(test_model.float_field, 2)
        test_model = models.TestModel.objects.get(id=extant_obj2.id)
        self.assertEqual(test_model.float_field, 2)
        test_model = models.TestModel.objects.get(id=extant_obj3.id)
        self.assertEqual(test_model.float_field, 2)
        test_model = models.TestModel.objects.get(id=extant_obj4.id)
        self.assertEqual(test_model.float_field, 0)

    def test_existing_objs_some_deleted_wo_update(self):
        """
        Tests when some existing objects will be deleted on a queryset. Run syncing
        with no update fields and verify they are untouched in the sync
        """
        objs = [G(models.TestModel, int_field=i, float_field=i) for i in range(5)]

        results = models.TestModel.objects.filter(int_field__lt=4).sync2([
            models.TestModel(int_field=1, float_field=2), models.TestModel(int_field=2, float_field=2),
            models.TestModel(int_field=3, float_field=2)
        ], ['int_field'], [], returning=True)

        self.assertEqual(len(list(results)), 4)
        self.assertEqual(len(list(results.deleted)), 1)
        self.assertEqual(len(list(results.untouched)), 3)
        self.assertEqual(list(results.deleted)[0].id, objs[0].id)

    def test_existing_objs_some_deleted_some_updated(self):
        """
        Tests when some existing objects will be deleted on a queryset. Run syncing
        with some update fields.
        """
        objs = [G(models.TestModel, int_field=i, float_field=i) for i in range(5)]

        results = models.TestModel.objects.filter(int_field__lt=4).sync2([
            models.TestModel(int_field=1, float_field=2), models.TestModel(int_field=2, float_field=2),
            models.TestModel(int_field=3, float_field=2)
        ], ['int_field'], ['float_field'], returning=True, ignore_duplicate_updates=True)

        self.assertEqual(len(list(results)), 4)
        self.assertEqual(len(list(results.deleted)), 1)
        self.assertEqual(len(list(results.updated)), 2)
        self.assertEqual(len(list(results.untouched)), 1)
        self.assertEqual(list(results.deleted)[0].id, objs[0].id)


class BulkUpsertTest(TestCase):
    """
    Tests the bulk_upsert function.
    """
    def test_return_upserts_none(self):
        """
        Tests the return_upserts flag on bulk upserts when there is no data.
        """
        return_values = models.TestModel.objects.bulk_upsert([], ['float_field'], ['float_field'], return_upserts=True)
        self.assertEqual(return_values, [])

    def test_return_upserts_distinct_none(self):
        """
        Tests the return_upserts_distinct flag on bulk upserts when there is no data.
        """
        return_values = models.TestModel.objects.bulk_upsert(
            [], ['float_field'], ['float_field'], return_upserts_distinct=True)
        self.assertEqual(return_values, ([], []))

    def test_return_upserts_none_native(self):
        """
        Tests the return_upserts flag on bulk upserts when there is no data.
        """
        return_values = models.TestModel.objects.bulk_upsert(
            [], ['float_field'], ['float_field'], return_upserts=True, native=True
        )
        self.assertEqual(return_values, [])

    def test_return_upserts_distinct_none_native(self):
        """
        verifies that return_upserts_distinct flag with native is not supported
        """
        with self.assertRaises(NotImplementedError):
            models.TestModel.objects.bulk_upsert(
                [], ['float_field'], ['float_field'], return_upserts_distinct=True, native=True)

    def test_return_created_values(self):
        """
        Tests that values that are created are returned properly when return_upserts is True.
        """

        return_values = models.TestModel.objects.bulk_upsert(
            [
                models.TestModel(int_field=1, char_field='1'),
                models.TestModel(int_field=3, char_field='3'),
                models.TestModel(int_field=4, char_field='4')
            ],
            ['int_field', 'char_field'],
            ['float_field'],
            return_upserts=True
        )

        # Assert that we properly returned the models
        self.assertEqual(len(return_values), 3)
        for test_model, expected_int in zip(sorted(return_values, key=lambda k: k.int_field), [1, 3, 4]):
            self.assertEqual(test_model.int_field, expected_int)
            self.assertIsNotNone(test_model.id)
        self.assertEqual(models.TestModel.objects.count(), 3)

        # Run additional upserts
        return_values = models.TestModel.objects.bulk_upsert(
            [
                models.TestModel(int_field=1, char_field='1', float_field=10),
                models.TestModel(int_field=3, char_field='3'),
                models.TestModel(int_field=4, char_field='4'),
                models.TestModel(int_field=5, char_field='5', float_field=50),
            ],
            ['int_field', 'char_field'],
            ['float_field'],
            return_upserts=True
        )
        self.assertEqual(len(return_values), 4)
        self.assertEqual(
            [
                [1, '1', 10],
                [3, '3', None],
                [4, '4', None],
                [5, '5', 50],
            ],
            [
                [test_model.int_field, test_model.char_field, test_model.float_field]
                for test_model in return_values
            ]
        )

    def test_return_created_values_native(self):
        """
        Tests that values that are created are returned properly when return_upserts is True.
        """
        return_values = models.TestModel.objects.bulk_upsert(
            [
                models.TestModel(int_field=1, char_field='1'),
                models.TestModel(int_field=3, char_field='3'),
                models.TestModel(int_field=4, char_field='4')
            ],
            ['int_field', 'char_field'],
            ['float_field'],
            return_upserts=True,
            native=True
        )

        self.assertEqual(len(return_values), 3)
        for test_model, expected_int in zip(sorted(return_values, key=lambda k: k.int_field), [1, 3, 4]):
            self.assertEqual(test_model.int_field, expected_int)
            self.assertIsNotNone(test_model.id)
        self.assertEqual(models.TestModel.objects.count(), 3)

    def test_return_created_updated_values(self):
        """
        Tests returning values when the items are either updated or created.
        """
        # Create an item that will be updated
        G(models.TestModel, int_field=2, float_field=1.0)
        return_values = models.TestModel.objects.bulk_upsert(
            [
                models.TestModel(int_field=1, float_field=3.0), models.TestModel(int_field=2.0, float_field=3.0),
                models.TestModel(int_field=3, float_field=3.0), models.TestModel(int_field=4, float_field=3.0)
            ],
            ['int_field'], ['float_field'], return_upserts=True)

        self.assertEqual(len(return_values), 4)
        for test_model, expected_int in zip(sorted(return_values, key=lambda k: k.int_field), [1, 2, 3, 4]):
            self.assertEqual(test_model.int_field, expected_int)
            self.assertAlmostEqual(test_model.float_field, 3.0)
            self.assertIsNotNone(test_model.id)
        self.assertEqual(models.TestModel.objects.count(), 4)

    def test_return_created_updated_values_native(self):
        """
        Tests returning values when the items are either updated or created.
        """
        # Create an item that will be updated
        G(models.TestModel, int_field=2, float_field=1.0)
        model_objects = [
            models.TestModel(int_field=1, float_field=3.0),
            models.TestModel(int_field=2.0, float_field=3.0),
            models.TestModel(int_field=3, float_field=3.0),
            models.TestModel(int_field=4, float_field=3.0)
        ]
        return_values = models.TestModel.objects.bulk_upsert(
            model_objects,
            ['int_field'],
            ['float_field'],
            return_upserts=True,
            native=True
        )

        self.assertEqual(len(return_values), 4)
        for test_model, expected_int in zip(sorted(return_values, key=lambda k: k.int_field), [1, 2, 3, 4]):
            self.assertEqual(test_model.int_field, expected_int)
            self.assertAlmostEqual(test_model.float_field, 3.0)
            self.assertIsNotNone(test_model.id)
        self.assertEqual(models.TestModel.objects.count(), 4)

    def test_return_created_updated_values_distinct(self):
        """
        Tests returning distinct sets of values when the items are either updated or created.
        """
        # Create an item that will be updated
        G(models.TestModel, int_field=2, float_field=1.0)
        model_objects = [
            models.TestModel(int_field=1, float_field=3.0),
            models.TestModel(int_field=2.0, float_field=3.0),
            models.TestModel(int_field=3, float_field=3.0),
            models.TestModel(int_field=4, float_field=3.0)
        ]
        updated, created = models.TestModel.objects.bulk_upsert(
            model_objects, ['int_field'], ['float_field'], return_upserts_distinct=True)
        self.assertEqual(
            [(2, 3.0)],
            [
                (obj.int_field, obj.float_field)
                for obj in sorted(updated, key=lambda k: k.int_field)
            ]
        )
        self.assertEqual(
            [(1, 3.0), (3, 3.0), (4, 3.0)],
            [
                (obj.int_field, obj.float_field)
                for obj in sorted(created, key=lambda k: k.int_field)
            ]
        )

    def test_wo_unique_fields(self):
        """
        Tests bulk_upsert with no unique fields. A ValueError should be raised since it is required to provide a
        list of unique_fields.
        """
        with self.assertRaises(ValueError):
            models.TestModel.objects.bulk_upsert([], [], ['field'])

    def test_wo_update_fields(self):
        """
        Tests bulk_upsert with no update fields. This function in turn should just do a bulk create for any
        models that do not already exist.
        """
        # Create models that already exist
        G(models.TestModel, int_field=1)
        G(models.TestModel, int_field=2)
        # Perform a bulk_upsert with one new model
        models.TestModel.objects.bulk_upsert([
            models.TestModel(int_field=1), models.TestModel(int_field=2), models.TestModel(int_field=3)
        ], ['int_field'])
        # Three objects should now exist
        self.assertEqual(models.TestModel.objects.count(), 3)
        for test_model, expected_int_value in zip(models.TestModel.objects.order_by('int_field'), [1, 2, 3]):
            self.assertEqual(test_model.int_field, expected_int_value)

    def test_wo_update_fields_native(self):
        """
        Tests bulk_upsert with no update fields. This function in turn should just do a bulk create for any
        models that do not already exist.
        """
        # Create models that already exist
        G(models.TestModel, int_field=1)
        G(models.TestModel, int_field=2)
        # Perform a bulk_upsert with one new model
        models.TestModel.objects.bulk_upsert(
            [
                models.TestModel(int_field=1), models.TestModel(int_field=2), models.TestModel(int_field=3)
            ],
            ['int_field'],
            native=True
        )
        # Three objects should now exist
        self.assertEqual(models.TestModel.objects.count(), 3)
        for test_model, expected_int_value in zip(models.TestModel.objects.order_by('int_field'), [1, 2, 3]):
            self.assertEqual(test_model.int_field, expected_int_value)

    def test_w_blank_arguments(self):
        """
        Tests using required arguments and using blank arguments for everything else.
        """
        models.TestModel.objects.bulk_upsert([], ['field'], ['field'])
        self.assertEqual(models.TestModel.objects.count(), 0)

        # Test native
        models.TestModel.objects.bulk_upsert([], ['field'], ['field'], native=True)
        self.assertEqual(models.TestModel.objects.count(), 0)

    def test_w_blank_arguments_native(self):
        """
        Tests using required arguments and using blank arguments for everything else.
        """
        models.TestModel.objects.bulk_upsert([], ['field'], ['field'], native=True)
        self.assertEqual(models.TestModel.objects.count(), 0)

    def test_no_updates(self):
        """
        Tests the case when no updates were previously stored (i.e objects are only created)
        """
        models.TestModel.objects.bulk_upsert([
            models.TestModel(int_field=0, char_field='0', float_field=0),
            models.TestModel(int_field=1, char_field='1', float_field=1),
            models.TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field'], ['char_field', 'float_field'])

        for i, model_obj in enumerate(models.TestModel.objects.order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, str(i))
            self.assertAlmostEqual(model_obj.float_field, i)

    def test_no_updates_native(self):
        """
        Tests the case when no updates were previously stored (i.e objects are only created)
        """
        models.TestModel.objects.bulk_upsert([
            models.TestModel(int_field=0, char_field='0', float_field=0),
            models.TestModel(int_field=1, char_field='1', float_field=1),
            models.TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field'], ['char_field', 'float_field'], native=True)

        for i, model_obj in enumerate(models.TestModel.objects.order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, str(i))
            self.assertAlmostEqual(model_obj.float_field, i)

    def test_all_updates_unique_int_field(self):
        """
        Tests the case when all updates were previously stored and the int field is used as a uniqueness
        constraint.
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        for i in range(3):
            G(models.TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int field as a uniqueness constraint
        models.TestModel.objects.bulk_upsert([
            models.TestModel(int_field=0, char_field='0', float_field=0),
            models.TestModel(int_field=1, char_field='1', float_field=1),
            models.TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field'], ['char_field', 'float_field'])

        # Verify that the fields were updated
        self.assertEqual(models.TestModel.objects.count(), 3)
        for i, model_obj in enumerate(models.TestModel.objects.order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, str(i))
            self.assertAlmostEqual(model_obj.float_field, i)

    def test_all_updates_unique_int_field_native(self):
        """
        Tests the case when all updates were previously stored and the int field is used as a uniqueness
        constraint.
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        for i in range(3):
            G(models.TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int field as a uniqueness constraint
        models.TestModel.objects.bulk_upsert([
            models.TestModel(int_field=0, char_field='0', float_field=0),
            models.TestModel(int_field=1, char_field='1', float_field=1),
            models.TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field'], ['char_field', 'float_field'], native=True)

        # Verify that the fields were updated
        self.assertEqual(models.TestModel.objects.count(), 3)
        for i, model_obj in enumerate(models.TestModel.objects.order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, str(i))
            self.assertAlmostEqual(model_obj.float_field, i)

    def test_all_updates_unique_int_field_update_float_field(self):
        """
        Tests the case when all updates were previously stored and the int field is used as a uniqueness
        constraint. Only updates the float field
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        for i in range(3):
            G(models.TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int field as a uniqueness constraint
        models.TestModel.objects.bulk_upsert([
            models.TestModel(int_field=0, char_field='0', float_field=0),
            models.TestModel(int_field=1, char_field='1', float_field=1),
            models.TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field'], update_fields=['float_field'])

        # Verify that the float field was updated
        self.assertEqual(models.TestModel.objects.count(), 3)
        for i, model_obj in enumerate(models.TestModel.objects.order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, '-1')
            self.assertAlmostEqual(model_obj.float_field, i)

    def test_all_updates_unique_int_field_update_float_field_native(self):
        """
        Tests the case when all updates were previously stored and the int field is used as a uniqueness
        constraint. Only updates the float field
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        for i in range(3):
            G(models.TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int field as a uniqueness constraint
        models.TestModel.objects.bulk_upsert([
            models.TestModel(int_field=0, char_field='0', float_field=0),
            models.TestModel(int_field=1, char_field='1', float_field=1),
            models.TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field'], update_fields=['float_field'], native=True)

        # Verify that the float field was updated
        self.assertEqual(models.TestModel.objects.count(), 3)
        for i, model_obj in enumerate(models.TestModel.objects.order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, '-1')
            self.assertAlmostEqual(model_obj.float_field, i)

    def test_some_updates_unique_int_field_update_float_field(self):
        """
        Tests the case when some updates were previously stored and the int field is used as a uniqueness
        constraint. Only updates the float field.
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        for i in range(2):
            G(models.TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int field as a uniqueness constraint. The first two are updated while the third is created
        models.TestModel.objects.bulk_upsert([
            models.TestModel(int_field=0, char_field='0', float_field=0),
            models.TestModel(int_field=1, char_field='1', float_field=1),
            models.TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field'], ['float_field'])

        # Verify that the float field was updated for the first two models and the char field was not updated for
        # the first two. The char field, however, should be '2' for the third model since it was created
        self.assertEqual(models.TestModel.objects.count(), 3)
        for i, model_obj in enumerate(models.TestModel.objects.order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, '-1' if i < 2 else '2')
            self.assertAlmostEqual(model_obj.float_field, i)

    def test_some_updates_unique_int_field_update_float_field_native(self):
        """
        Tests the case when some updates were previously stored and the int field is used as a uniqueness
        constraint. Only updates the float field.
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        for i in range(2):
            G(models.TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int field as a uniqueness constraint. The first two are updated while the third is created
        models.TestModel.objects.bulk_upsert([
            models.TestModel(int_field=0, char_field='0', float_field=0),
            models.TestModel(int_field=1, char_field='1', float_field=1),
            models.TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field'], ['float_field'], native=True)

        # Verify that the float field was updated for the first two models and the char field was not updated for
        # the first two. The char field, however, should be '2' for the third model since it was created
        self.assertEqual(models.TestModel.objects.count(), 3)
        for i, model_obj in enumerate(models.TestModel.objects.order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, '-1' if i < 2 else '2')
            self.assertAlmostEqual(model_obj.float_field, i)

    def test_some_updates_unique_timezone_field_update_float_field(self):
        """
        Tests the case when some updates were previously stored and the timezone field is used as a uniqueness
        constraint. Only updates the float field.
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        for i in ['US/Eastern', 'US/Central']:
            G(models.TestModel, time_zone=i, char_field='-1', float_field=-1)

        # Update using the int field as a uniqueness constraint. The first two are updated while the third is created
        models.TestModel.objects.bulk_upsert([
            models.TestModel(time_zone=timezone('US/Eastern'), char_field='0', float_field=0),
            models.TestModel(time_zone=timezone('US/Central'), char_field='1', float_field=1),
            models.TestModel(time_zone=timezone('UTC'), char_field='2', float_field=2),
        ], ['time_zone'], ['float_field'])

        # Verify that the float field was updated for the first two models and the char field was not updated for
        # the first two. The char field, however, should be '2' for the third model since it was created
        m1 = models.TestModel.objects.get(time_zone=timezone('US/Eastern'))
        self.assertEqual(m1.char_field, '-1')
        self.assertAlmostEqual(m1.float_field, 0)

        m2 = models.TestModel.objects.get(time_zone=timezone('US/Central'))
        self.assertEqual(m2.char_field, '-1')
        self.assertAlmostEqual(m2.float_field, 1)

        m3 = models.TestModel.objects.get(time_zone=timezone('UTC'))
        self.assertEqual(m3.char_field, '2')
        self.assertAlmostEqual(m3.float_field, 2)

    def test_some_updates_unique_int_char_field_update_float_field(self):
        """
        Tests the case when some updates were previously stored and the int and char fields are used as a uniqueness
        constraint. Only updates the float field.
        """
        # Create previously stored test models with a unique int and char field
        for i in range(2):
            G(models.TestModel, int_field=i, char_field=str(i), float_field=-1)

        # Update using the int field as a uniqueness constraint. The first two are updated while the third is created
        models.TestModel.objects.bulk_upsert([
            models.TestModel(int_field=0, char_field='0', float_field=0),
            models.TestModel(int_field=1, char_field='1', float_field=1),
            models.TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field', 'char_field'], ['float_field'])

        # Verify that the float field was updated for the first two models and the char field was not updated for
        # the first two. The char field, however, should be '2' for the third model since it was created
        self.assertEqual(models.TestModel.objects.count(), 3)
        for i, model_obj in enumerate(models.TestModel.objects.order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, str(i))
            self.assertAlmostEqual(model_obj.float_field, i)

    def test_some_updates_unique_int_char_field_update_float_field_native(self):
        """
        Tests the case when some updates were previously stored and the int and char fields are used as a uniqueness
        constraint. Only updates the float field.
        """
        # Create previously stored test models with a unique int and char field
        for i in range(2):
            G(models.TestModel, int_field=i, char_field=str(i), float_field=-1)

        # Update using the int field as a uniqueness constraint. The first two are updated while the third is created
        models.TestModel.objects.bulk_upsert([
            models.TestModel(int_field=0, char_field='0', float_field=0),
            models.TestModel(int_field=1, char_field='1', float_field=1),
            models.TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field', 'char_field'], ['float_field'], native=True)

        # Verify that the float field was updated for the first two models and the char field was not updated for
        # the first two. The char field, however, should be '2' for the third model since it was created
        self.assertEqual(models.TestModel.objects.count(), 3)
        for i, model_obj in enumerate(models.TestModel.objects.order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, str(i))
            self.assertAlmostEqual(model_obj.float_field, i)

    def test_no_updates_unique_int_char_field(self):
        """
        Tests the case when no updates were previously stored and the int and char fields are used as a uniqueness
        constraint. In this case, there is data previously stored, but the uniqueness constraints dont match.
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        for i in range(3):
            G(models.TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int and char field as a uniqueness constraint. All three objects are created
        models.TestModel.objects.bulk_upsert([
            models.TestModel(int_field=3, char_field='0', float_field=0),
            models.TestModel(int_field=4, char_field='1', float_field=1),
            models.TestModel(int_field=5, char_field='2', float_field=2),
        ], ['int_field', 'char_field'], ['float_field'])

        # Verify that no updates occured
        self.assertEqual(models.TestModel.objects.count(), 6)
        self.assertEqual(models.TestModel.objects.filter(char_field='-1').count(), 3)
        for i, model_obj in enumerate(models.TestModel.objects.filter(char_field='-1').order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, '-1')
            self.assertAlmostEqual(model_obj.float_field, -1)
        self.assertEqual(models.TestModel.objects.exclude(char_field='-1').count(), 3)
        for i, model_obj in enumerate(models.TestModel.objects.exclude(char_field='-1').order_by('int_field')):
            self.assertEqual(model_obj.int_field, i + 3)
            self.assertEqual(model_obj.char_field, str(i))
            self.assertAlmostEqual(model_obj.float_field, i)

    def test_no_updates_unique_int_char_field_native(self):
        """
        Tests the case when no updates were previously stored and the int and char fields are used as a uniqueness
        constraint. In this case, there is data previously stored, but the uniqueness constraints dont match.
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        for i in range(3):
            G(models.TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int and char field as a uniqueness constraint. All three objects are created
        models.TestModel.objects.bulk_upsert([
            models.TestModel(int_field=3, char_field='0', float_field=0),
            models.TestModel(int_field=4, char_field='1', float_field=1),
            models.TestModel(int_field=5, char_field='2', float_field=2),
        ], ['int_field', 'char_field'], ['float_field'], native=True)

        # Verify that no updates occured
        self.assertEqual(models.TestModel.objects.count(), 6)
        self.assertEqual(models.TestModel.objects.filter(char_field='-1').count(), 3)
        for i, model_obj in enumerate(models.TestModel.objects.filter(char_field='-1').order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, '-1')
            self.assertAlmostEqual(model_obj.float_field, -1)
        self.assertEqual(models.TestModel.objects.exclude(char_field='-1').count(), 3)
        for i, model_obj in enumerate(models.TestModel.objects.exclude(char_field='-1').order_by('int_field')):
            self.assertEqual(model_obj.int_field, i + 3)
            self.assertEqual(model_obj.char_field, str(i))
            self.assertAlmostEqual(model_obj.float_field, i)

    def test_some_updates_unique_int_char_field_queryset(self):
        """
        Tests the case when some updates were previously stored and a queryset is used on the bulk upsert.
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        for i in range(3):
            G(models.TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int field as a uniqueness constraint on a queryset. Only one object should be updated.
        models.TestModel.objects.filter(int_field=0).bulk_upsert([
            models.TestModel(int_field=0, char_field='0', float_field=0),
            models.TestModel(int_field=4, char_field='1', float_field=1),
            models.TestModel(int_field=5, char_field='2', float_field=2),
        ], ['int_field'], ['float_field'])

        # Verify that two new objecs were created
        self.assertEqual(models.TestModel.objects.count(), 5)
        self.assertEqual(models.TestModel.objects.filter(char_field='-1').count(), 3)
        for i, model_obj in enumerate(models.TestModel.objects.filter(char_field='-1').order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, '-1')

    def test_some_updates_unique_int_char_field_queryset_native(self):
        """
        Tests the case when some updates were previously stored and a queryset is used on the bulk upsert.
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        for i in range(3):
            G(models.TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int field as a uniqueness constraint on a queryset. Only one object should be updated.
        models.TestModel.objects.filter(int_field=0).bulk_upsert([
            models.TestModel(int_field=0, char_field='0', float_field=0),
            models.TestModel(int_field=4, char_field='1', float_field=1),
            models.TestModel(int_field=5, char_field='2', float_field=2),
        ], ['int_field'], ['float_field'], native=True)

        # Verify that two new objecs were created
        self.assertEqual(models.TestModel.objects.count(), 5)
        self.assertEqual(models.TestModel.objects.filter(char_field='-1').count(), 3)
        for i, model_obj in enumerate(models.TestModel.objects.filter(char_field='-1').order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, '-1')


class BulkUpsert2Test(TestCase):
    """
    Tests the bulk_upsert2 function.
    """
    def test_return_upserts_none(self):
        """
        Tests the return_upserts flag on bulk upserts when there is no data.
        """
        return_values = models.TestModel.objects.bulk_upsert2([], ['float_field'], ['float_field'], returning=True)
        self.assertEqual(return_values, [])

    def test_return_multi_unique_fields_not_supported(self):
        """
        The new manager utils supports returning bulk upserts when there are multiple unique fields.
        """
        return_values = models.TestModel.objects.bulk_upsert2([], ['float_field', 'int_field'], ['float_field'],
                                                              returning=True)
        self.assertEqual(return_values, [])

    def test_return_created_values(self):
        """
        Tests that values that are created are returned properly when returning is True.
        """
        results = models.TestModel.objects.bulk_upsert2(
            [models.TestModel(int_field=1), models.TestModel(int_field=3), models.TestModel(int_field=4)],
            ['int_field'], ['float_field'], returning=True
        )

        self.assertEqual(len(list(results.created)), 3)
        for test_model, expected_int in zip(sorted(results.created, key=lambda k: k.int_field), [1, 3, 4]):
            self.assertEqual(test_model.int_field, expected_int)
            self.assertIsNotNone(test_model.id)
        self.assertEqual(models.TestModel.objects.count(), 3)

    def test_return_list_of_values(self):
        """
        Tests that values that are created are returned properly when returning is True.
        Set returning to a list of fields
        """
        results = models.TestModel.objects.bulk_upsert2(
            [models.TestModel(int_field=1, float_field=2),
             models.TestModel(int_field=3, float_field=4),
             models.TestModel(int_field=4, float_field=5)],
            ['int_field'], ['float_field'], returning=['float_field']
        )

        self.assertEqual(len(list(results.created)), 3)
        with self.assertRaises(AttributeError):
            list(results.created)[0].int_field
        self.assertEqual(set([2, 4, 5]), set([m.float_field for m in results.created]))

    def test_return_created_updated_values(self):
        """
        Tests returning values when the items are either updated or created.
        """
        # Create an item that will be updated
        G(models.TestModel, int_field=2, float_field=1.0)
        results = models.TestModel.objects.bulk_upsert2(
            [
                models.TestModel(int_field=1, float_field=3.0), models.TestModel(int_field=2.0, float_field=3.0),
                models.TestModel(int_field=3, float_field=3.0), models.TestModel(int_field=4, float_field=3.0)
            ],
            ['int_field'], ['float_field'], returning=True)

        created = list(results.created)
        updated = list(results.updated)
        self.assertEqual(len(created), 3)
        self.assertEqual(len(updated), 1)
        for test_model, expected_int in zip(sorted(created, key=lambda k: k.int_field), [1, 3, 4]):
            self.assertEqual(test_model.int_field, expected_int)
            self.assertAlmostEqual(test_model.float_field, 3.0)
            self.assertIsNotNone(test_model.id)

        self.assertEqual(updated[0].int_field, 2)
        self.assertAlmostEqual(updated[0].float_field, 3.0)
        self.assertIsNotNone(updated[0].id)
        self.assertEqual(models.TestModel.objects.count(), 4)

    def test_created_updated_auto_datetime_values(self):
        """
        Tests when the items are either updated or created when auto_now
        and auto_now_add datetime values are used
        """
        # Create an item that will be updated
        with freezegun.freeze_time('2018-09-01 00:00:00'):
            G(models.TestAutoDateTimeModel, int_field=1)

        with freezegun.freeze_time('2018-09-02 00:00:00'):
            results = models.TestAutoDateTimeModel.objects.bulk_upsert2(
                [
                    models.TestAutoDateTimeModel(int_field=1),
                    models.TestAutoDateTimeModel(int_field=2),
                    models.TestAutoDateTimeModel(int_field=3),
                    models.TestAutoDateTimeModel(int_field=4)
                ],
                ['int_field'], returning=True)

        self.assertEqual(len(list(results.created)), 3)
        self.assertEqual(len(list(results.updated)), 1)

        expected_auto_now = [dt.datetime(2018, 9, 2), dt.datetime(2018, 9, 2),
                             dt.datetime(2018, 9, 2), dt.datetime(2018, 9, 2)]
        expected_auto_now_add = [dt.datetime(2018, 9, 1), dt.datetime(2018, 9, 2),
                                 dt.datetime(2018, 9, 2), dt.datetime(2018, 9, 2)]
        for i, test_model in enumerate(sorted(results, key=lambda k: k.int_field)):
            self.assertEqual(test_model.auto_now_field, expected_auto_now[i])
            self.assertEqual(test_model.auto_now_add_field, expected_auto_now_add[i])

    def test_wo_update_fields(self):
        """
        Tests bulk_upsert with no update fields. This function in turn should just do a bulk create for any
        models that do not already exist.
        """
        # Create models that already exist
        G(models.TestModel, int_field=1, float_field=1)
        G(models.TestModel, int_field=2, float_field=2)
        # Perform a bulk_upsert with one new model
        models.TestModel.objects.bulk_upsert2([
            models.TestModel(int_field=1, float_field=3),
            models.TestModel(int_field=2, float_field=3),
            models.TestModel(int_field=3, float_field=3)
        ], ['int_field'], update_fields=[])
        # Three objects should now exist, but no float fields should be updated
        self.assertEqual(models.TestModel.objects.count(), 3)
        for test_model, expected_int_value in zip(models.TestModel.objects.order_by('int_field'), [1, 2, 3]):
            self.assertEqual(test_model.int_field, expected_int_value)
            self.assertEqual(test_model.float_field, expected_int_value)

    def test_w_blank_arguments(self):
        """
        Tests using required arguments and using blank arguments for everything else.
        """
        models.TestModel.objects.bulk_upsert2([], ['field'], ['field'])
        self.assertEqual(models.TestModel.objects.count(), 0)

    def test_no_updates(self):
        """
        Tests the case when no updates were previously stored (i.e objects are only created)
        """
        models.TestModel.objects.bulk_upsert([
            models.TestModel(int_field=0, char_field='0', float_field=0),
            models.TestModel(int_field=1, char_field='1', float_field=1),
            models.TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field'], ['char_field', 'float_field'])

        for i, model_obj in enumerate(models.TestModel.objects.order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, str(i))
            self.assertAlmostEqual(model_obj.float_field, i)

    def test_update_fields_returning(self):
        """
        Tests the case when all updates were previously stored and the int field is used as a uniqueness
        constraint. Assert returned values are expected and that it updates all fields by default
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        test_models = [
            G(models.TestModel, int_field=i, char_field='-1', float_field=-1)
            for i in range(3)
        ]

        # Update using the int field as a uniqueness constraint
        results = models.TestModel.objects.bulk_upsert2([
            models.TestModel(int_field=0, char_field='0', float_field=0),
            models.TestModel(int_field=1, char_field='1', float_field=1),
            models.TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field'], returning=True)

        self.assertEqual(list(results.created), [])
        self.assertEqual(set([u.id for u in results.updated]), set([t.id for t in test_models]))
        self.assertEqual(set([u.int_field for u in results.updated]), set([0, 1, 2]))
        self.assertEqual(set([u.float_field for u in results.updated]), set([0, 1, 2]))
        self.assertEqual(set([u.char_field for u in results.updated]), set(['0', '1', '2']))

    def test_no_update_fields_returning(self):
        """
        Tests the case when all updates were previously stored and the int field is used as a uniqueness
        constraint. This test does not update any fields
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        for i in range(3):
            G(models.TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int field as a uniqueness constraint
        results = models.TestModel.objects.bulk_upsert2([
            models.TestModel(int_field=0, char_field='0', float_field=0),
            models.TestModel(int_field=1, char_field='1', float_field=1),
            models.TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field'], [], returning=True)

        self.assertEqual(list(results), [])

    def test_update_duplicate_fields_returning_none_updated(self):
        """
        Tests the case when all updates were previously stored and the upsert tries to update the rows
        with duplicate values.
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        for i in range(3):
            G(models.TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int field as a uniqueness constraint
        results = models.TestModel.objects.bulk_upsert2([
            models.TestModel(int_field=0, char_field='-1', float_field=-1),
            models.TestModel(int_field=1, char_field='-1', float_field=-1),
            models.TestModel(int_field=2, char_field='-1', float_field=-1),
        ], ['int_field'], ['char_field', 'float_field'], returning=True, ignore_duplicate_updates=True)

        self.assertEqual(list(results), [])

    def test_update_duplicate_fields_returning_some_updated(self):
        """
        Tests the case when all updates were previously stored and the upsert tries to update the rows
        with duplicate values. Test when some aren't duplicates
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        for i in range(3):
            G(models.TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int field as a uniqueness constraint
        results = models.TestModel.objects.bulk_upsert2([
            models.TestModel(int_field=0, char_field='-1', float_field=-1),
            models.TestModel(int_field=1, char_field='-1', float_field=-1),
            models.TestModel(int_field=2, char_field='0', float_field=-1),
        ], ['int_field'], ['char_field', 'float_field'], returning=['char_field'], ignore_duplicate_updates=True)

        self.assertEqual(list(results.created), [])
        self.assertEqual(len(list(results.updated)), 1)
        self.assertEqual(list(results.updated)[0].char_field, '0')

    def test_update_duplicate_fields_returning_some_updated_return_untouched(self):
        """
        Tests the case when all updates were previously stored and the upsert tries to update the rows
        with duplicate values. Test when some aren't duplicates
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        for i in range(3):
            G(models.TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int field as a uniqueness constraint
        results = models.TestModel.objects.bulk_upsert2(
            [
                models.TestModel(int_field=0, char_field='-1', float_field=-1),
                models.TestModel(int_field=1, char_field='-1', float_field=-1),
                models.TestModel(int_field=2, char_field='0', float_field=-1),
                models.TestModel(int_field=3, char_field='3', float_field=3),
            ],
            ['int_field'], ['char_field', 'float_field'],
            returning=['char_field'], ignore_duplicate_updates=True, return_untouched=True)

        self.assertEqual(len(list(results.updated)), 1)
        self.assertEqual(len(list(results.untouched)), 2)
        self.assertEqual(len(list(results.created)), 1)
        self.assertEqual(list(results.updated)[0].char_field, '0')
        self.assertEqual(list(results.created)[0].char_field, '3')

    def test_update_duplicate_fields_returning_some_updated_return_untouched_ignore_dups(self):
        """
        Tests the case when all updates were previously stored and the upsert tries to update the rows
        with duplicate values. Test when some aren't duplicates and return untouched results.
        There will be no untouched results in this test since we turn off ignoring duplicate
        updates
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        for i in range(3):
            G(models.TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int field as a uniqueness constraint
        results = models.TestModel.objects.bulk_upsert2(
            [
                models.TestModel(int_field=0, char_field='-1', float_field=-1),
                models.TestModel(int_field=1, char_field='-1', float_field=-1),
                models.TestModel(int_field=2, char_field='0', float_field=-1),
                models.TestModel(int_field=3, char_field='3', float_field=3),
            ],
            ['int_field'], ['char_field', 'float_field'],
            returning=['char_field'], ignore_duplicate_updates=False, return_untouched=True)

        self.assertEqual(len(list(results.untouched)), 0)
        self.assertEqual(len(list(results.updated)), 3)
        self.assertEqual(len(list(results.created)), 1)
        self.assertEqual(list(results.created)[0].char_field, '3')

    def test_all_updates_unique_int_field(self):
        """
        Tests the case when all updates were previously stored and the int field is used as a uniqueness
        constraint.
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        for i in range(3):
            G(models.TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int field as a uniqueness constraint
        models.TestModel.objects.bulk_upsert2([
            models.TestModel(int_field=0, char_field='0', float_field=0),
            models.TestModel(int_field=1, char_field='1', float_field=1),
            models.TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field'], ['char_field', 'float_field'])

        # Verify that the fields were updated
        self.assertEqual(models.TestModel.objects.count(), 3)
        for i, model_obj in enumerate(models.TestModel.objects.order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, str(i))
            self.assertAlmostEqual(model_obj.float_field, i)

    def test_all_updates_unique_int_field_update_float_field(self):
        """
        Tests the case when all updates were previously stored and the int field is used as a uniqueness
        constraint. Only updates the float field
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        for i in range(3):
            G(models.TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int field as a uniqueness constraint
        models.TestModel.objects.bulk_upsert2([
            models.TestModel(int_field=0, char_field='0', float_field=0),
            models.TestModel(int_field=1, char_field='1', float_field=1),
            models.TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field'], update_fields=['float_field'])

        # Verify that the float field was updated
        self.assertEqual(models.TestModel.objects.count(), 3)
        for i, model_obj in enumerate(models.TestModel.objects.order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, '-1')
            self.assertAlmostEqual(model_obj.float_field, i)

    def test_some_updates_unique_int_field_update_float_field(self):
        """
        Tests the case when some updates were previously stored and the int field is used as a uniqueness
        constraint. Only updates the float field.
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        for i in range(2):
            G(models.TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int field as a uniqueness constraint. The first two are updated while the third is created
        models.TestModel.objects.bulk_upsert2([
            models.TestModel(int_field=0, char_field='0', float_field=0),
            models.TestModel(int_field=1, char_field='1', float_field=1),
            models.TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field'], ['float_field'])

        # Verify that the float field was updated for the first two models and the char field was not updated for
        # the first two. The char field, however, should be '2' for the third model since it was created
        self.assertEqual(models.TestModel.objects.count(), 3)
        for i, model_obj in enumerate(models.TestModel.objects.order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, '-1' if i < 2 else '2')
            self.assertAlmostEqual(model_obj.float_field, i)

    def test_some_updates_unique_timezone_field_update_float_field(self):
        """
        Tests the case when some updates were previously stored and the timezone field is used as a uniqueness
        constraint. Only updates the float field.
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        for i in ['US/Eastern', 'US/Central']:
            G(models.TestUniqueTzModel, time_zone=i, char_field='-1', float_field=-1)

        # Update using the int field as a uniqueness constraint. The first two are updated while the third is created
        models.TestUniqueTzModel.objects.bulk_upsert2([
            models.TestModel(time_zone=timezone('US/Eastern'), char_field='0', float_field=0),
            models.TestModel(time_zone=timezone('US/Central'), char_field='1', float_field=1),
            models.TestModel(time_zone=timezone('UTC'), char_field='2', float_field=2),
        ], ['time_zone'], ['float_field'])

        # Verify that the float field was updated for the first two models and the char field was not updated for
        # the first two. The char field, however, should be '2' for the third model since it was created
        m1 = models.TestUniqueTzModel.objects.get(time_zone=timezone('US/Eastern'))
        self.assertEqual(m1.char_field, '-1')
        self.assertAlmostEqual(m1.float_field, 0)

        m2 = models.TestUniqueTzModel.objects.get(time_zone=timezone('US/Central'))
        self.assertEqual(m2.char_field, '-1')
        self.assertAlmostEqual(m2.float_field, 1)

        m3 = models.TestUniqueTzModel.objects.get(time_zone=timezone('UTC'))
        self.assertEqual(m3.char_field, '2')
        self.assertAlmostEqual(m3.float_field, 2)

    def test_some_updates_unique_int_char_field_update_float_field(self):
        """
        Tests the case when some updates were previously stored and the int and char fields are used as a uniqueness
        constraint. Only updates the float field.
        """
        # Create previously stored test models with a unique int and char field
        for i in range(2):
            G(models.TestModel, int_field=i, char_field=str(i), float_field=-1)

        # Update using the int field as a uniqueness constraint. The first two are updated while the third is created
        models.TestModel.objects.bulk_upsert2([
            models.TestModel(int_field=0, char_field='0', float_field=0),
            models.TestModel(int_field=1, char_field='1', float_field=1),
            models.TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field', 'char_field'], ['float_field'])

        # Verify that the float field was updated for the first two models and the char field was not updated for
        # the first two. The char field, however, should be '2' for the third model since it was created
        self.assertEqual(models.TestModel.objects.count(), 3)
        for i, model_obj in enumerate(models.TestModel.objects.order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, str(i))
            self.assertAlmostEqual(model_obj.float_field, i)

    def test_no_updates_unique_int_char_field(self):
        """
        Tests the case when no updates were previously stored and the int and char fields are used as a uniqueness
        constraint. In this case, there is data previously stored, but the uniqueness constraints dont match.
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        for i in range(3):
            G(models.TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int and char field as a uniqueness constraint. All three objects are created
        models.TestModel.objects.bulk_upsert2([
            models.TestModel(int_field=3, char_field='0', float_field=0),
            models.TestModel(int_field=4, char_field='1', float_field=1),
            models.TestModel(int_field=5, char_field='2', float_field=2),
        ], ['int_field', 'char_field'], ['float_field'])

        # Verify that no updates occured
        self.assertEqual(models.TestModel.objects.count(), 6)
        self.assertEqual(models.TestModel.objects.filter(char_field='-1').count(), 3)
        for i, model_obj in enumerate(models.TestModel.objects.filter(char_field='-1').order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, '-1')
            self.assertAlmostEqual(model_obj.float_field, -1)
        self.assertEqual(models.TestModel.objects.exclude(char_field='-1').count(), 3)
        for i, model_obj in enumerate(models.TestModel.objects.exclude(char_field='-1').order_by('int_field')):
            self.assertEqual(model_obj.int_field, i + 3)
            self.assertEqual(model_obj.char_field, str(i))
            self.assertAlmostEqual(model_obj.float_field, i)

    def test_some_updates_unique_int_char_field_queryset(self):
        """
        Tests the case when some updates were previously stored and a queryset is used on the bulk upsert.
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        for i in range(3):
            G(models.TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int field as a uniqueness constraint on a queryset. Only one object should be updated.
        models.TestModel.objects.filter(int_field=0).bulk_upsert2([
            models.TestModel(int_field=0, char_field='0', float_field=0),
            models.TestModel(int_field=4, char_field='1', float_field=1),
            models.TestModel(int_field=5, char_field='2', float_field=2),
        ], ['int_field'], ['float_field'])

        # Verify that two new objecs were created
        self.assertEqual(models.TestModel.objects.count(), 5)
        self.assertEqual(models.TestModel.objects.filter(char_field='-1').count(), 3)
        for i, model_obj in enumerate(models.TestModel.objects.filter(char_field='-1').order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, '-1')


class PostBulkOperationSignalTest(TestCase):
    """
    Tests that the post_bulk_operation signal is emitted on all functions that emit the signal.
    """
    def setUp(self):
        """
        Defines a siangl handler that collects information about fired signals
        """
        class SignalHandler(object):
            num_times_called = 0
            model = None

            def __call__(self, *args, **kwargs):
                self.num_times_called += 1
                self.model = kwargs['model']

        self.signal_handler = SignalHandler()
        post_bulk_operation.connect(self.signal_handler)

    def tearDown(self):
        """
        Disconnect the siangl to make sure it doesn't get connected multiple times.
        """
        post_bulk_operation.disconnect(self.signal_handler)

    def test_custom_field_bulk_update(self):
        model_obj = models.TestModel.objects.create(int_field=2)
        model_obj.time_zone = timezone('US/Eastern')
        models.TestModel.objects.bulk_update([model_obj], ['time_zone'])
        model_obj = models.TestModel.objects.get(id=model_obj.id)
        self.assertEqual(model_obj.time_zone, timezone('US/Eastern'))

    def test_post_bulk_operation_queryset_update(self):
        """
        Tests that the update operation on a queryset emits the post_bulk_operation signal.
        """
        models.TestModel.objects.all().update(int_field=1)

        self.assertEqual(self.signal_handler.model, models.TestModel)
        self.assertEqual(self.signal_handler.num_times_called, 1)

    def test_post_bulk_operation_manager_update(self):
        """
        Tests that the update operation on a manager emits the post_bulk_operation signal.
        """
        models.TestModel.objects.update(int_field=1)

        self.assertEqual(self.signal_handler.model, models.TestModel)
        self.assertEqual(self.signal_handler.num_times_called, 1)

    def test_post_bulk_operation_bulk_update(self):
        """
        Tests that the bulk_update operation emits the post_bulk_operation signal.
        """
        model_obj = models.TestModel.objects.create(int_field=2)
        models.TestModel.objects.bulk_update([model_obj], ['int_field'])

        self.assertEqual(self.signal_handler.model, models.TestModel)
        self.assertEqual(self.signal_handler.num_times_called, 1)

    def test_post_bulk_operation_bulk_upsert2(self):
        """
        Tests that the bulk_upsert2 operation emits the post_bulk_operation signal.
        """
        model_obj = models.TestModel.objects.create(int_field=2)
        models.TestModel.objects.bulk_upsert2([model_obj], ['int_field'])

        self.assertEqual(self.signal_handler.model, models.TestModel)
        self.assertEqual(self.signal_handler.num_times_called, 1)

    def test_post_bulk_operation_bulk_create(self):
        """
        Tests that the bulk_create operation emits the post_bulk_operation signal.
        """
        models.TestModel.objects.bulk_create([models.TestModel(int_field=2)])

        self.assertEqual(self.signal_handler.model, models.TestModel)
        self.assertEqual(self.signal_handler.num_times_called, 1)

    def test_post_bulk_operation_bulk_create_queryset(self):
        """
        Tests that the bulk_create operation emits the post_bulk_operation signal.
        """
        models.TestModel.objects.all().bulk_create([models.TestModel(int_field=2)])

        self.assertEqual(self.signal_handler.model, models.TestModel)
        self.assertEqual(self.signal_handler.num_times_called, 1)

    def test_save_doesnt_emit_signal(self):
        """
        Tests that a non-bulk operation doesn't emit the signal.
        """
        model_obj = models.TestModel.objects.create(int_field=2)
        model_obj.save()

        self.assertEqual(self.signal_handler.num_times_called, 0)


class IdDictTest(TestCase):
    """
    Tests the id_dict function.
    """
    def test_no_objects_manager(self):
        """
        Tests the output when no objects are present in the manager.
        """
        self.assertEqual(models.TestModel.objects.id_dict(), {})

    def test_objects_manager(self):
        """
        Tests retrieving a dict of objects keyed on their ID from the manager.
        """
        model_obj1 = G(models.TestModel, int_field=1)
        model_obj2 = G(models.TestModel, int_field=2)
        self.assertEqual(models.TestModel.objects.id_dict(), {model_obj1.id: model_obj1, model_obj2.id: model_obj2})

    def test_no_objects_queryset(self):
        """
        Tests the case when no objects are returned via a queryset.
        """
        G(models.TestModel, int_field=1)
        G(models.TestModel, int_field=2)
        self.assertEqual(models.TestModel.objects.filter(int_field__gte=3).id_dict(), {})

    def test_objects_queryset(self):
        """
        Tests the case when objects are returned via a queryset.
        """
        G(models.TestModel, int_field=1)
        model_obj = G(models.TestModel, int_field=2)
        self.assertEqual(models.TestModel.objects.filter(int_field__gte=2).id_dict(), {model_obj.id: model_obj})


class GetOrNoneTest(TestCase):
    """
    Tests the get_or_none function in the manager utils
    """
    def test_existing_using_objects(self):
        """
        Tests get_or_none on an existing object from Model.objects.
        """
        # Create an existing model
        model_obj = G(models.TestModel)
        # Verify that get_or_none on objects returns the test model
        self.assertEqual(model_obj, models.TestModel.objects.get_or_none(id=model_obj.id))

    def test_multiple_error_using_objects(self):
        """
        Tests get_or_none on multiple existing objects from Model.objects.
        """
        # Create an existing model
        model_obj = G(models.TestModel, char_field='hi')
        model_obj = G(models.TestModel, char_field='hi')
        # Verify that get_or_none on objects returns the test model
        with self.assertRaises(models.TestModel.MultipleObjectsReturned):
            self.assertEqual(model_obj, models.TestModel.objects.get_or_none(char_field='hi'))

    def test_existing_using_queryset(self):
        """
        Tests get_or_none on an existing object from a queryst.
        """
        # Create an existing model
        model_obj = G(models.TestModel)
        # Verify that get_or_none on objects returns the test model
        self.assertEqual(model_obj, models.TestModel.objects.filter(id=model_obj.id).get_or_none(id=model_obj.id))

    def test_none_using_objects(self):
        """
        Tests when no object exists when using Model.objects.
        """
        # Verify that get_or_none on objects returns the test model
        self.assertIsNone(models.TestModel.objects.get_or_none(id=1))

    def test_none_using_queryset(self):
        """
        Tests when no object exists when using a queryset.
        """
        # Verify that get_or_none on objects returns the test model
        self.assertIsNone(models.TestModel.objects.filter(id=1).get_or_none(id=1))


class SingleTest(TestCase):
    """
    Tests the single function in the manager utils.
    """
    def test_none_using_objects(self):
        """
        Tests when there are no objects using Model.objects.
        """
        with self.assertRaises(models.TestModel.DoesNotExist):
            models.TestModel.objects.single()

    def test_multiple_using_objects(self):
        """
        Tests when there are multiple objects using Model.objects.
        """
        G(models.TestModel)
        G(models.TestModel)
        with self.assertRaises(models.TestModel.MultipleObjectsReturned):
            models.TestModel.objects.single()

    def test_none_using_queryset(self):
        """
        Tests when there are no objects using a queryset.
        """
        with self.assertRaises(models.TestModel.DoesNotExist):
            models.TestModel.objects.filter(id__gte=0).single()

    def test_multiple_using_queryset(self):
        """
        Tests when there are multiple objects using a queryset.
        """
        G(models.TestModel)
        G(models.TestModel)
        with self.assertRaises(models.TestModel.MultipleObjectsReturned):
            models.TestModel.objects.filter(id__gte=0).single()

    def test_single_using_objects(self):
        """
        Tests accessing a single object using Model.objects.
        """
        model_obj = G(models.TestModel)
        self.assertEqual(model_obj, models.TestModel.objects.single())

    def test_single_using_queryset(self):
        """
        Tests accessing a single object using a queryset.
        """
        model_obj = G(models.TestModel)
        self.assertEqual(model_obj, models.TestModel.objects.filter(id__gte=0).single())

    def test_mutliple_to_single_using_queryset(self):
        """
        Tests accessing a single object using a queryset. The queryset is what filters it
        down to a single object.
        """
        model_obj = G(models.TestModel)
        G(models.TestModel)
        self.assertEqual(model_obj, models.TestModel.objects.filter(id=model_obj.id).single())


class BulkUpdateTest(TestCase):
    """
    Tests the bulk_update function.
    """
    def test_update_foreign_key_by_id(self):
        t_model = G(models.TestModel)
        t_fk_model = G(models.TestForeignKeyModel)
        t_fk_model.test_model = t_model
        models.TestForeignKeyModel.objects.bulk_update([t_fk_model], ['test_model_id'])
        self.assertEqual(models.TestForeignKeyModel.objects.get().test_model, t_model)

    def test_update_foreign_key_by_name(self):
        t_model = G(models.TestModel)
        t_fk_model = G(models.TestForeignKeyModel)
        t_fk_model.test_model = t_model
        models.TestForeignKeyModel.objects.bulk_update([t_fk_model], ['test_model'])
        self.assertEqual(models.TestForeignKeyModel.objects.get().test_model, t_model)

    def test_foreign_key_pk_using_id(self):
        """
        Tests a bulk update on a model that has a primary key to a foreign key. It uses the id of the pk in the
        update
        """
        t = G(models.TestPkForeignKey, char_field='hi')
        models.TestPkForeignKey.objects.bulk_update(
            [models.TestPkForeignKey(my_key_id=t.my_key_id, char_field='hello')], ['char_field'])
        self.assertEqual(models.TestPkForeignKey.objects.count(), 1)
        self.assertTrue(models.TestPkForeignKey.objects.filter(char_field='hello', my_key=t.my_key).exists())

    def test_foreign_key_pk(self):
        """
        Tests a bulk update on a model that has a primary key to a foreign key. It uses the foreign key itself
        in the update
        """
        t = G(models.TestPkForeignKey, char_field='hi')
        models.TestPkForeignKey.objects.bulk_update(
            [models.TestPkForeignKey(my_key=t.my_key, char_field='hello')], ['char_field'])
        self.assertEqual(models.TestPkForeignKey.objects.count(), 1)
        self.assertTrue(models.TestPkForeignKey.objects.filter(char_field='hello', my_key=t.my_key).exists())

    def test_char_pk(self):
        """
        Tests a bulk update on a model that has a primary key to a char field.
        """
        G(models.TestPkChar, char_field='hi', my_key='1')
        models.TestPkChar.objects.bulk_update(
            [models.TestPkChar(my_key='1', char_field='hello')], ['char_field'])
        self.assertEqual(models.TestPkChar.objects.count(), 1)
        self.assertTrue(models.TestPkChar.objects.filter(char_field='hello', my_key='1').exists())

    def test_none(self):
        """
        Tests when no values are provided to bulk update.
        """
        models.TestModel.objects.bulk_update([], [])

    def test_update_floats_to_null(self):
        """
        Tests updating a float field to a null field.
        """
        test_obj_1 = G(models.TestModel, int_field=1, float_field=2)
        test_obj_2 = G(models.TestModel, int_field=2, float_field=3)
        test_obj_1.float_field = None
        test_obj_2.float_field = None

        models.TestModel.objects.bulk_update([test_obj_1, test_obj_2], ['float_field'])

        test_obj_1 = models.TestModel.objects.get(id=test_obj_1.id)
        test_obj_2 = models.TestModel.objects.get(id=test_obj_2.id)
        self.assertIsNone(test_obj_1.float_field)
        self.assertIsNone(test_obj_2.float_field)

    def test_update_ints_to_null(self):
        """
        Tests updating an int field to a null field.
        """
        test_obj_1 = G(models.TestModel, int_field=1, float_field=2)
        test_obj_2 = G(models.TestModel, int_field=2, float_field=3)
        test_obj_1.int_field = None
        test_obj_2.int_field = None

        models.TestModel.objects.bulk_update([test_obj_1, test_obj_2], ['int_field'])

        test_obj_1 = models.TestModel.objects.get(id=test_obj_1.id)
        test_obj_2 = models.TestModel.objects.get(id=test_obj_2.id)
        self.assertIsNone(test_obj_1.int_field)
        self.assertIsNone(test_obj_2.int_field)

    def test_update_chars_to_null(self):
        """
        Tests updating a char field to a null field.
        """
        test_obj_1 = G(models.TestModel, int_field=1, char_field='2')
        test_obj_2 = G(models.TestModel, int_field=2, char_field='3')
        test_obj_1.char_field = None
        test_obj_2.char_field = None

        models.TestModel.objects.bulk_update([test_obj_1, test_obj_2], ['char_field'])

        test_obj_1 = models.TestModel.objects.get(id=test_obj_1.id)
        test_obj_2 = models.TestModel.objects.get(id=test_obj_2.id)
        self.assertIsNone(test_obj_1.char_field)
        self.assertIsNone(test_obj_2.char_field)

    def test_objs_no_fields_to_update(self):
        """
        Tests when objects are given to bulk update with no fields to update. Nothing should change in
        the objects.
        """
        test_obj_1 = G(models.TestModel, int_field=1)
        test_obj_2 = G(models.TestModel, int_field=2)
        # Change the int fields on the models
        test_obj_1.int_field = 3
        test_obj_2.int_field = 4
        # Do a bulk update with no update fields
        models.TestModel.objects.bulk_update([test_obj_1, test_obj_2], [])
        # The test objects int fields should be untouched
        test_obj_1 = models.TestModel.objects.get(id=test_obj_1.id)
        test_obj_2 = models.TestModel.objects.get(id=test_obj_2.id)
        self.assertEqual(test_obj_1.int_field, 1)
        self.assertEqual(test_obj_2.int_field, 2)

    def test_objs_one_field_to_update(self):
        """
        Tests when objects are given to bulk update with one field to update.
        """
        test_obj_1 = G(models.TestModel, int_field=1)
        test_obj_2 = G(models.TestModel, int_field=2)
        # Change the int fields on the models
        test_obj_1.int_field = 3
        test_obj_2.int_field = 4
        # Do a bulk update with the int fields
        models.TestModel.objects.bulk_update([test_obj_1, test_obj_2], ['int_field'])
        # The test objects int fields should be untouched
        test_obj_1 = models.TestModel.objects.get(id=test_obj_1.id)
        test_obj_2 = models.TestModel.objects.get(id=test_obj_2.id)
        self.assertEqual(test_obj_1.int_field, 3)
        self.assertEqual(test_obj_2.int_field, 4)

    def test_objs_one_field_to_update_ignore_other_field(self):
        """
        Tests when objects are given to bulk update with one field to update. This test changes another field
        not included in the update and verifies it is not updated.
        """
        test_obj_1 = G(models.TestModel, int_field=1, float_field=1.0)
        test_obj_2 = G(models.TestModel, int_field=2, float_field=2.0)
        # Change the int and float fields on the models
        test_obj_1.int_field = 3
        test_obj_2.int_field = 4
        test_obj_1.float_field = 3.0
        test_obj_2.float_field = 4.0
        # Do a bulk update with the int fields
        models.TestModel.objects.bulk_update([test_obj_1, test_obj_2], ['int_field'])
        # The test objects int fields should be untouched
        test_obj_1 = models.TestModel.objects.get(id=test_obj_1.id)
        test_obj_2 = models.TestModel.objects.get(id=test_obj_2.id)
        self.assertEqual(test_obj_1.int_field, 3)
        self.assertEqual(test_obj_2.int_field, 4)
        # The float fields should not be updated
        self.assertEqual(test_obj_1.float_field, 1.0)
        self.assertEqual(test_obj_2.float_field, 2.0)

    def test_objs_two_fields_to_update(self):
        """
        Tests when objects are given to bulk update with two fields to update.
        """
        test_obj_1 = G(models.TestModel, int_field=1, float_field=1.0)
        test_obj_2 = G(models.TestModel, int_field=2, float_field=2.0)
        # Change the int and float fields on the models
        test_obj_1.int_field = 3
        test_obj_2.int_field = 4
        test_obj_1.float_field = 3.0
        test_obj_2.float_field = 4.0
        # Do a bulk update with the int fields
        models.TestModel.objects.bulk_update([test_obj_1, test_obj_2], ['int_field', 'float_field'])
        # The test objects int fields should be untouched
        test_obj_1 = models.TestModel.objects.get(id=test_obj_1.id)
        test_obj_2 = models.TestModel.objects.get(id=test_obj_2.id)
        self.assertEqual(test_obj_1.int_field, 3)
        self.assertEqual(test_obj_2.int_field, 4)
        # The float fields should be updated
        self.assertEqual(test_obj_1.float_field, 3.0)
        self.assertEqual(test_obj_2.float_field, 4.0)

    def test_updating_objects_with_custom_db_field_types(self):
        """
        Tests when objects are updated that have custom field types
        """
        test_obj_1 = G(
            models.TestModel,
            int_field=1,
            float_field=1.0,
            json_field={'test': 'test'},
            array_field=['one', 'two']
        )
        test_obj_2 = G(
            models.TestModel,
            int_field=2,
            float_field=2.0,
            json_field={'test2': 'test2'},
            array_field=['three', 'four']
        )

        # Change the fields on the models
        test_obj_1.json_field = {'test': 'updated'}
        test_obj_1.array_field = ['one', 'two', 'updated']

        test_obj_2.json_field = {'test2': 'updated'}
        test_obj_2.array_field = ['three', 'four', 'updated']

        # Do a bulk update with the int fields
        models.TestModel.objects.bulk_update(
            [test_obj_1, test_obj_2],
            ['json_field', 'array_field']
        )

        # Refetch the objects
        test_obj_1 = models.TestModel.objects.get(id=test_obj_1.id)
        test_obj_2 = models.TestModel.objects.get(id=test_obj_2.id)

        # Assert that the json field was updated
        self.assertEqual(test_obj_1.json_field, {'test': 'updated'})
        self.assertEqual(test_obj_2.json_field, {'test2': 'updated'})

        # Assert that the array field was updated
        self.assertEqual(test_obj_1.array_field, ['one', 'two', 'updated'])
        self.assertEqual(test_obj_2.array_field, ['three', 'four', 'updated'])


class UpsertTest(TestCase):
    """
    Tests the upsert method in the manager utils.
    """
    @patch.object(models.TestModel, 'save', spec_set=True)
    def test_no_double_save_on_create(self, mock_save):
        """
        Tests that save isn't called on upsert after the object has been created.
        """
        model_obj, created = models.TestModel.objects.upsert(int_field=1, updates={'float_field': 1.0})
        self.assertEqual(mock_save.call_count, 1)

    def test_save_on_update(self):
        """
        Tests that save is called when the model is updated
        """
        model_obj, created = models.TestModel.objects.upsert(int_field=1, updates={'float_field': 1.0})

        with patch.object(models.TestModel, 'save', spec_set=True) as mock_save:
            models.TestModel.objects.upsert(int_field=1, updates={'float_field': 1.1})
            self.assertEqual(mock_save.call_count, 1)

    def test_no_save_on_no_update(self):
        """
        Tests that save is not called on upsert if the model is not actually updated.
        """
        model_obj, created = models.TestModel.objects.upsert(int_field=1, updates={'float_field': 1.0})

        with patch.object(models.TestModel, 'save', spec_set=True) as mock_save:
            models.TestModel.objects.upsert(int_field=1, updates={'float_field': 1.0})
            self.assertEqual(mock_save.call_count, 0)

    def test_upsert_creation_no_defaults(self):
        """
        Tests an upsert that results in a created object. Don't use defaults
        """
        model_obj, created = models.TestModel.objects.upsert(int_field=1)
        self.assertTrue(created)
        self.assertEqual(model_obj.int_field, 1)
        self.assertIsNone(model_obj.float_field)
        self.assertIsNone(model_obj.char_field)

    def test_upsert_creation_defaults(self):
        """
        Tests an upsert that results in a created object. Defaults are used.
        """
        model_obj, created = models.TestModel.objects.upsert(int_field=1, defaults={'float_field': 1.0})
        self.assertTrue(created)
        self.assertEqual(model_obj.int_field, 1)
        self.assertEqual(model_obj.float_field, 1.0)
        self.assertIsNone(model_obj.char_field)

    def test_upsert_creation_updates(self):
        """
        Tests an upsert that results in a created object. Updates are used.
        """
        model_obj, created = models.TestModel.objects.upsert(int_field=1, updates={'float_field': 1.0})
        self.assertTrue(created)
        self.assertEqual(model_obj.int_field, 1)
        self.assertEqual(model_obj.float_field, 1.0)
        self.assertIsNone(model_obj.char_field)

    def test_upsert_creation_defaults_updates(self):
        """
        Tests an upsert that results in a created object. Defaults are used and so are updates.
        """
        model_obj, created = models.TestModel.objects.upsert(
            int_field=1, defaults={'float_field': 1.0}, updates={'char_field': 'Hello'})
        self.assertTrue(created)
        self.assertEqual(model_obj.int_field, 1)
        self.assertEqual(model_obj.float_field, 1.0)
        self.assertEqual(model_obj.char_field, 'Hello')

    def test_upsert_creation_no_defaults_override(self):
        """
        Tests an upsert that results in a created object. Defaults are not used and
        the updates values override the defaults on creation.
        """
        test_model = G(models.TestModel)
        model_obj, created = models.TestForeignKeyModel.objects.upsert(int_field=1, updates={
            'test_model': test_model,
        })
        self.assertTrue(created)
        self.assertEqual(model_obj.int_field, 1)
        self.assertEqual(model_obj.test_model, test_model)

    def test_upsert_creation_defaults_updates_override(self):
        """
        Tests an upsert that results in a created object. Defaults are used and so are updates. Updates
        override the defaults.
        """
        model_obj, created = models.TestModel.objects.upsert(
            int_field=1, defaults={'float_field': 1.0}, updates={'char_field': 'Hello', 'float_field': 2.0})
        self.assertTrue(created)
        self.assertEqual(model_obj.int_field, 1)
        self.assertEqual(model_obj.float_field, 2.0)
        self.assertEqual(model_obj.char_field, 'Hello')

    def test_upsert_no_creation_no_defaults(self):
        """
        Tests an upsert that already exists. Don't use defaults
        """
        G(models.TestModel, int_field=1, float_field=None, char_field=None)
        model_obj, created = models.TestModel.objects.upsert(int_field=1)
        self.assertFalse(created)
        self.assertEqual(model_obj.int_field, 1)
        self.assertIsNone(model_obj.float_field)
        self.assertIsNone(model_obj.char_field)

    def test_upsert_no_creation_defaults(self):
        """
        Tests an upsert that already exists. Defaults are used but don't matter since the object already existed.
        """
        G(models.TestModel, int_field=1, float_field=None, char_field=None)
        model_obj, created = models.TestModel.objects.upsert(int_field=1, defaults={'float_field': 1.0})
        self.assertFalse(created)
        self.assertEqual(model_obj.int_field, 1)
        self.assertIsNone(model_obj.float_field)
        self.assertIsNone(model_obj.char_field)

    def test_upsert_no_creation_updates(self):
        """
        Tests an upsert that already exists. Updates are used.
        """
        G(models.TestModel, int_field=1, float_field=2.0, char_field=None)
        model_obj, created = models.TestModel.objects.upsert(int_field=1, updates={'float_field': 1.0})
        self.assertFalse(created)
        self.assertEqual(model_obj.int_field, 1)
        self.assertEqual(model_obj.float_field, 1.0)
        self.assertIsNone(model_obj.char_field)

    def test_upsert_no_creation_defaults_updates(self):
        """
        Tests an upsert that already exists. Defaults are used and so are updates.
        """
        G(models.TestModel, int_field=1, float_field=2.0, char_field='Hi')
        model_obj, created = models.TestModel.objects.upsert(
            int_field=1, defaults={'float_field': 1.0}, updates={'char_field': 'Hello'})
        self.assertFalse(created)
        self.assertEqual(model_obj.int_field, 1)
        self.assertEqual(model_obj.float_field, 2.0)
        self.assertEqual(model_obj.char_field, 'Hello')

    def test_upsert_no_creation_defaults_updates_override(self):
        """
        Tests an upsert that already exists. Defaults are used and so are updates. Updates override the defaults.
        """
        G(models.TestModel, int_field=1, float_field=3.0, char_field='Hi')
        model_obj, created = models.TestModel.objects.upsert(
            int_field=1, defaults={'float_field': 1.0}, updates={'char_field': 'Hello', 'float_field': 2.0})
        self.assertFalse(created)
        self.assertEqual(model_obj.int_field, 1)
        self.assertEqual(model_obj.float_field, 2.0)
        self.assertEqual(model_obj.char_field, 'Hello')
