from django.test import TestCase
from django_dynamic_fixture import G
from manager_utils import post_bulk_operation
from mock import patch

from manager_utils.tests.models import TestModel, TestForeignKeyModel, TestPkForeignKey, TestPkChar


class SyncTest(TestCase):
    """
    Tests the sync function.
    """
    def test_w_char_pk(self):
        """
        Tests with a model that has a char pk.
        """
        extant_obj1 = G(TestPkChar, my_key='1', char_field='1')
        extant_obj2 = G(TestPkChar, my_key='2', char_field='1')
        extant_obj3 = G(TestPkChar, my_key='3', char_field='1')

        TestPkChar.objects.sync([
            TestPkChar(my_key='3', char_field='2'), TestPkChar(my_key='4', char_field='2'),
            TestPkChar(my_key='5', char_field='2')
        ], ['my_key'], ['char_field'])

        self.assertEquals(TestPkChar.objects.count(), 3)
        self.assertTrue(TestPkChar.objects.filter(my_key='3').exists())
        self.assertTrue(TestPkChar.objects.filter(my_key='4').exists())
        self.assertTrue(TestPkChar.objects.filter(my_key='5').exists())

        with self.assertRaises(TestPkChar.DoesNotExist):
            TestPkChar.objects.get(pk=extant_obj1.pk)
        with self.assertRaises(TestPkChar.DoesNotExist):
            TestPkChar.objects.get(pk=extant_obj2.pk)
        test_model = TestPkChar.objects.get(pk=extant_obj3.pk)
        self.assertEquals(test_model.char_field, '2')

    def test_no_existing_objs(self):
        """
        Tests when there are no existing objects before the sync.
        """
        TestModel.objects.sync(
            [TestModel(int_field=1), TestModel(int_field=3), TestModel(int_field=4)], ['int_field'], ['float_field'])
        self.assertEquals(TestModel.objects.count(), 3)
        self.assertTrue(TestModel.objects.filter(int_field=1).exists())
        self.assertTrue(TestModel.objects.filter(int_field=3).exists())
        self.assertTrue(TestModel.objects.filter(int_field=4).exists())

    def test_existing_objs_all_deleted(self):
        """
        Tests when there are existing objects that will all be deleted.
        """
        extant_obj1 = G(TestModel, int_field=1)
        extant_obj2 = G(TestModel, int_field=2)
        extant_obj3 = G(TestModel, int_field=3)

        TestModel.objects.sync(
            [TestModel(int_field=4), TestModel(int_field=5), TestModel(int_field=6)], ['int_field'], ['float_field'])

        self.assertEquals(TestModel.objects.count(), 3)
        self.assertTrue(TestModel.objects.filter(int_field=4).exists())
        self.assertTrue(TestModel.objects.filter(int_field=5).exists())
        self.assertTrue(TestModel.objects.filter(int_field=6).exists())

        with self.assertRaises(TestModel.DoesNotExist):
            TestModel.objects.get(id=extant_obj1.id)
        with self.assertRaises(TestModel.DoesNotExist):
            TestModel.objects.get(id=extant_obj2.id)
        with self.assertRaises(TestModel.DoesNotExist):
            TestModel.objects.get(id=extant_obj3.id)

    def test_existing_objs_all_deleted_empty_sync(self):
        """
        Tests when there are existing objects deleted because of an emtpy sync.
        """
        extant_obj1 = G(TestModel, int_field=1)
        extant_obj2 = G(TestModel, int_field=2)
        extant_obj3 = G(TestModel, int_field=3)

        TestModel.objects.sync([], ['int_field'], ['float_field'])

        self.assertEquals(TestModel.objects.count(), 0)
        with self.assertRaises(TestModel.DoesNotExist):
            TestModel.objects.get(id=extant_obj1.id)
        with self.assertRaises(TestModel.DoesNotExist):
            TestModel.objects.get(id=extant_obj2.id)
        with self.assertRaises(TestModel.DoesNotExist):
            TestModel.objects.get(id=extant_obj3.id)

    def test_existing_objs_some_deleted(self):
        """
        Tests when some existing objects will be deleted.
        """
        extant_obj1 = G(TestModel, int_field=1, float_field=1)
        extant_obj2 = G(TestModel, int_field=2, float_field=1)
        extant_obj3 = G(TestModel, int_field=3, float_field=1)

        TestModel.objects.sync([
            TestModel(int_field=3, float_field=2), TestModel(int_field=4, float_field=2),
            TestModel(int_field=5, float_field=2)
        ], ['int_field'], ['float_field'])

        self.assertEquals(TestModel.objects.count(), 3)
        self.assertTrue(TestModel.objects.filter(int_field=3).exists())
        self.assertTrue(TestModel.objects.filter(int_field=4).exists())
        self.assertTrue(TestModel.objects.filter(int_field=5).exists())

        with self.assertRaises(TestModel.DoesNotExist):
            TestModel.objects.get(id=extant_obj1.id)
        with self.assertRaises(TestModel.DoesNotExist):
            TestModel.objects.get(id=extant_obj2.id)
        test_model = TestModel.objects.get(id=extant_obj3.id)
        self.assertEquals(test_model.int_field, 3)

    def test_existing_objs_some_deleted_w_queryset(self):
        """
        Tests when some existing objects will be deleted on a queryset
        """
        extant_obj0 = G(TestModel, int_field=0, float_field=1)
        extant_obj1 = G(TestModel, int_field=1, float_field=1)
        extant_obj2 = G(TestModel, int_field=2, float_field=1)
        extant_obj3 = G(TestModel, int_field=3, float_field=1)
        extant_obj4 = G(TestModel, int_field=4, float_field=0)

        TestModel.objects.filter(int_field__lt=4).sync([
            TestModel(int_field=1, float_field=2), TestModel(int_field=2, float_field=2),
            TestModel(int_field=3, float_field=2)
        ], ['int_field'], ['float_field'])

        self.assertEquals(TestModel.objects.count(), 4)
        self.assertTrue(TestModel.objects.filter(int_field=1).exists())
        self.assertTrue(TestModel.objects.filter(int_field=2).exists())
        self.assertTrue(TestModel.objects.filter(int_field=3).exists())

        with self.assertRaises(TestModel.DoesNotExist):
            TestModel.objects.get(id=extant_obj0.id)

        test_model = TestModel.objects.get(id=extant_obj1.id)
        self.assertEquals(test_model.float_field, 2)
        test_model = TestModel.objects.get(id=extant_obj2.id)
        self.assertEquals(test_model.float_field, 2)
        test_model = TestModel.objects.get(id=extant_obj3.id)
        self.assertEquals(test_model.float_field, 2)
        test_model = TestModel.objects.get(id=extant_obj4.id)
        self.assertEquals(test_model.float_field, 0)


class BulkUpsertTest(TestCase):
    """
    Tests the bulk_upsert function.
    """
    def test_return_upserts_none(self):
        """
        Tests the return_upserts flag on bulk upserts when there is no data.
        """
        return_values = TestModel.objects.bulk_upsert([], ['float_field'], ['float_field'], return_upserts=True)
        self.assertEquals(return_values, [])

    def test_return_multi_unique_fields_not_supported(self):
        """
        Current manager utils doesn't support returning bulk upserts when there are multiple unique fields.
        """
        with self.assertRaises(NotImplementedError):
            TestModel.objects.bulk_upsert([], ['float_field', 'int_field'], ['float_field'], return_upserts=True)

    def test_return_created_values(self):
        """
        Tests that values that are created are returned properly when return_upserts is True.
        """
        return_values = TestModel.objects.bulk_upsert(
            [TestModel(int_field=1), TestModel(int_field=3), TestModel(int_field=4)],
            ['int_field'], ['float_field'], return_upserts=True)

        self.assertEquals(len(return_values), 3)
        for test_model, expected_int in zip(sorted(return_values, key=lambda k: k.int_field), [1, 3, 4]):
            self.assertEquals(test_model.int_field, expected_int)
            self.assertIsNotNone(test_model.id)
        self.assertEquals(TestModel.objects.count(), 3)

    def test_return_created_updated_values(self):
        """
        Tests returning values when the items are either updated or created.
        """
        # Create an item that will be updated
        G(TestModel, int_field=2, float_field=1.0)
        return_values = TestModel.objects.bulk_upsert(
            [
                TestModel(int_field=1, float_field=3.0), TestModel(int_field=2.0, float_field=3.0),
                TestModel(int_field=3, float_field=3.0), TestModel(int_field=4, float_field=3.0)
            ],
            ['int_field'], ['float_field'], return_upserts=True)

        self.assertEquals(len(return_values), 4)
        for test_model, expected_int in zip(sorted(return_values, key=lambda k: k.int_field), [1, 2, 3, 4]):
            self.assertEquals(test_model.int_field, expected_int)
            self.assertAlmostEquals(test_model.float_field, 3.0)
            self.assertIsNotNone(test_model.id)
        self.assertEquals(TestModel.objects.count(), 4)

    def test_wo_unique_fields(self):
        """
        Tests bulk_upsert with no unique fields. A ValueError should be raised since it is required to provide a
        list of unique_fields.
        """
        with self.assertRaises(ValueError):
            TestModel.objects.bulk_upsert([], [], ['field'])

    def test_wo_update_fields(self):
        """
        Tests bulk_upsert with no update fields. This function in turn should just do a bulk create for any
        models that do not already exist.
        """
        # Create models that already exist
        G(TestModel, int_field=1)
        G(TestModel, int_field=2)
        # Perform a bulk_upsert with one new model
        TestModel.objects.bulk_upsert([
            TestModel(int_field=1), TestModel(int_field=2), TestModel(int_field=3)
        ], ['int_field'])
        # Three objects should now exist
        self.assertEquals(TestModel.objects.count(), 3)
        for test_model, expected_int_value in zip(TestModel.objects.order_by('int_field'), [1, 2, 3]):
            self.assertEquals(test_model.int_field, expected_int_value)

    def test_w_blank_arguments(self):
        """
        Tests using required arguments and using blank arguments for everything else.
        """
        TestModel.objects.bulk_upsert([], ['field'], ['field'])
        self.assertEquals(TestModel.objects.count(), 0)

    def test_no_updates(self):
        """
        Tests the case when no updates were previously stored (i.e objects are only created)
        """
        TestModel.objects.bulk_upsert([
            TestModel(int_field=0, char_field='0', float_field=0),
            TestModel(int_field=1, char_field='1', float_field=1),
            TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field'], ['char_field', 'float_field'])

        for i, model_obj in enumerate(TestModel.objects.order_by('int_field')):
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
            G(TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int field as a uniqueness constraint
        TestModel.objects.bulk_upsert([
            TestModel(int_field=0, char_field='0', float_field=0),
            TestModel(int_field=1, char_field='1', float_field=1),
            TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field'], ['char_field', 'float_field'])

        # Verify that the fields were updated
        self.assertEquals(TestModel.objects.count(), 3)
        for i, model_obj in enumerate(TestModel.objects.order_by('int_field')):
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
            G(TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int field as a uniqueness constraint
        TestModel.objects.bulk_upsert([
            TestModel(int_field=0, char_field='0', float_field=0),
            TestModel(int_field=1, char_field='1', float_field=1),
            TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field'], update_fields=['float_field'])

        # Verify that the float field was updated
        self.assertEquals(TestModel.objects.count(), 3)
        for i, model_obj in enumerate(TestModel.objects.order_by('int_field')):
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
            G(TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int field as a uniqueness constraint. The first two are updated while the third is created
        TestModel.objects.bulk_upsert([
            TestModel(int_field=0, char_field='0', float_field=0),
            TestModel(int_field=1, char_field='1', float_field=1),
            TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field'], ['float_field'])

        # Verify that the float field was updated for the first two models and the char field was not updated for
        # the first two. The char field, however, should be '2' for the third model since it was created
        self.assertEquals(TestModel.objects.count(), 3)
        for i, model_obj in enumerate(TestModel.objects.order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, '-1' if i < 2 else '2')
            self.assertAlmostEqual(model_obj.float_field, i)

    def test_some_updates_unique_int_char_field_update_float_field(self):
        """
        Tests the case when some updates were previously stored and the int and char fields are used as a uniqueness
        constraint. Only updates the float field.
        """
        # Create previously stored test models with a unique int and char field
        for i in range(2):
            G(TestModel, int_field=i, char_field=str(i), float_field=-1)

        # Update using the int field as a uniqueness constraint. The first two are updated while the third is created
        TestModel.objects.bulk_upsert([
            TestModel(int_field=0, char_field='0', float_field=0),
            TestModel(int_field=1, char_field='1', float_field=1),
            TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field', 'char_field'], ['float_field'])

        # Verify that the float field was updated for the first two models and the char field was not updated for
        # the first two. The char field, however, should be '2' for the third model since it was created
        self.assertEquals(TestModel.objects.count(), 3)
        for i, model_obj in enumerate(TestModel.objects.order_by('int_field')):
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
            G(TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int and char field as a uniqueness constraint. All three objects are created
        TestModel.objects.bulk_upsert([
            TestModel(int_field=0, char_field='0', float_field=0),
            TestModel(int_field=1, char_field='1', float_field=1),
            TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field', 'char_field'], ['float_field'])

        # Verify that no updates occured
        self.assertEquals(TestModel.objects.count(), 6)
        self.assertEquals(TestModel.objects.filter(char_field='-1').count(), 3)
        for i, model_obj in enumerate(TestModel.objects.filter(char_field='-1').order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, '-1')
            self.assertAlmostEqual(model_obj.float_field, -1)
        self.assertEquals(TestModel.objects.exclude(char_field='-1').count(), 3)
        for i, model_obj in enumerate(TestModel.objects.exclude(char_field='-1').order_by('int_field')):
            self.assertEqual(model_obj.int_field, i)
            self.assertEqual(model_obj.char_field, str(i))
            self.assertAlmostEqual(model_obj.float_field, i)

    def test_some_updates_unique_int_char_field_queryset(self):
        """
        Tests the case when some updates were previously stored and a queryset is used on the bulk upsert.
        """
        # Create previously stored test models with a unique int field and -1 for all other fields
        for i in range(3):
            G(TestModel, int_field=i, char_field='-1', float_field=-1)

        # Update using the int field as a uniqueness constraint on a queryset. Only one object should be updated.
        TestModel.objects.filter(int_field=0).bulk_upsert([
            TestModel(int_field=0, char_field='0', float_field=0),
            TestModel(int_field=1, char_field='1', float_field=1),
            TestModel(int_field=2, char_field='2', float_field=2),
        ], ['int_field'], ['float_field'])

        # Verify that two new objecs were inserted
        self.assertEquals(TestModel.objects.count(), 5)
        self.assertEquals(TestModel.objects.filter(char_field='-1').count(), 3)
        for i, model_obj in enumerate(TestModel.objects.filter(char_field='-1').order_by('int_field')):
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

    def test_post_bulk_operation_queryset_update(self):
        """
        Tests that the update operation on a queryset emits the post_bulk_operation signal.
        """
        TestModel.objects.all().update(int_field=1)

        self.assertEquals(self.signal_handler.model, TestModel)
        self.assertEquals(self.signal_handler.num_times_called, 1)

    def test_post_bulk_operation_manager_update(self):
        """
        Tests that the update operation on a manager emits the post_bulk_operation signal.
        """
        TestModel.objects.update(int_field=1)

        self.assertEquals(self.signal_handler.model, TestModel)
        self.assertEquals(self.signal_handler.num_times_called, 1)

    def test_post_bulk_operation_bulk_update(self):
        """
        Tests that the bulk_update operation emits the post_bulk_operation signal.
        """
        model_obj = TestModel.objects.create(int_field=2)
        TestModel.objects.bulk_update([model_obj], ['int_field'])

        self.assertEquals(self.signal_handler.model, TestModel)
        self.assertEquals(self.signal_handler.num_times_called, 1)

    def test_post_bulk_operation_bulk_create(self):
        """
        Tests that the bulk_create operation emits the post_bulk_operation signal.
        """
        TestModel.objects.bulk_create([TestModel(int_field=2)])

        self.assertEquals(self.signal_handler.model, TestModel)
        self.assertEquals(self.signal_handler.num_times_called, 1)

    def test_save_doesnt_emit_signal(self):
        """
        Tests that a non-bulk operation doesn't emit the signal.
        """
        model_obj = TestModel.objects.create(int_field=2)
        model_obj.save()

        self.assertEquals(self.signal_handler.num_times_called, 0)


class IdDictTest(TestCase):
    """
    Tests the id_dict function.
    """
    def test_no_objects_manager(self):
        """
        Tests the output when no objects are present in the manager.
        """
        self.assertEquals(TestModel.objects.id_dict(), {})

    def test_objects_manager(self):
        """
        Tests retrieving a dict of objects keyed on their ID from the manager.
        """
        model_obj1 = G(TestModel, int_field=1)
        model_obj2 = G(TestModel, int_field=2)
        self.assertEquals(TestModel.objects.id_dict(), {model_obj1.id: model_obj1, model_obj2.id: model_obj2})

    def test_no_objects_queryset(self):
        """
        Tests the case when no objects are returned via a queryset.
        """
        G(TestModel, int_field=1)
        G(TestModel, int_field=2)
        self.assertEquals(TestModel.objects.filter(int_field__gte=3).id_dict(), {})

    def test_objects_queryset(self):
        """
        Tests the case when objects are returned via a queryset.
        """
        G(TestModel, int_field=1)
        model_obj = G(TestModel, int_field=2)
        self.assertEquals(TestModel.objects.filter(int_field__gte=2).id_dict(), {model_obj.id: model_obj})


class GetOrNoneTest(TestCase):
    """
    Tests the get_or_none function in the manager utils
    """
    def test_existing_using_objects(self):
        """
        Tests get_or_none on an existing object from Model.objects.
        """
        # Create an existing model
        model_obj = G(TestModel)
        # Verify that get_or_none on objects returns the test model
        self.assertEquals(model_obj, TestModel.objects.get_or_none(id=model_obj.id))

    def test_multiple_error_using_objects(self):
        """
        Tests get_or_none on multiple existing objects from Model.objects.
        """
        # Create an existing model
        model_obj = G(TestModel, char_field='hi')
        model_obj = G(TestModel, char_field='hi')
        # Verify that get_or_none on objects returns the test model
        with self.assertRaises(TestModel.MultipleObjectsReturned):
            self.assertEquals(model_obj, TestModel.objects.get_or_none(char_field='hi'))

    def test_existing_using_queryset(self):
        """
        Tests get_or_none on an existing object from a queryst.
        """
        # Create an existing model
        model_obj = G(TestModel)
        # Verify that get_or_none on objects returns the test model
        self.assertEquals(model_obj, TestModel.objects.filter(id=model_obj.id).get_or_none(id=model_obj.id))

    def test_none_using_objects(self):
        """
        Tests when no object exists when using Model.objects.
        """
        # Verify that get_or_none on objects returns the test model
        self.assertIsNone(TestModel.objects.get_or_none(id=1))

    def test_none_using_queryset(self):
        """
        Tests when no object exists when using a queryset.
        """
        # Verify that get_or_none on objects returns the test model
        self.assertIsNone(TestModel.objects.filter(id=1).get_or_none(id=1))


class SingleTest(TestCase):
    """
    Tests the single function in the manager utils.
    """
    def test_none_using_objects(self):
        """
        Tests when there are no objects using Model.objects.
        """
        with self.assertRaises(TestModel.DoesNotExist):
            TestModel.objects.single()

    def test_multiple_using_objects(self):
        """
        Tests when there are multiple objects using Model.objects.
        """
        G(TestModel)
        G(TestModel)
        with self.assertRaises(TestModel.MultipleObjectsReturned):
            TestModel.objects.single()

    def test_none_using_queryset(self):
        """
        Tests when there are no objects using a queryset.
        """
        with self.assertRaises(TestModel.DoesNotExist):
            TestModel.objects.filter(id__gte=0).single()

    def test_multiple_using_queryset(self):
        """
        Tests when there are multiple objects using a queryset.
        """
        G(TestModel)
        G(TestModel)
        with self.assertRaises(TestModel.MultipleObjectsReturned):
            TestModel.objects.filter(id__gte=0).single()

    def test_single_using_objects(self):
        """
        Tests accessing a single object using Model.objects.
        """
        model_obj = G(TestModel)
        self.assertEquals(model_obj, TestModel.objects.single())

    def test_single_using_queryset(self):
        """
        Tests accessing a single object using a queryset.
        """
        model_obj = G(TestModel)
        self.assertEquals(model_obj, TestModel.objects.filter(id__gte=0).single())

    def test_mutliple_to_single_using_queryset(self):
        """
        Tests accessing a single object using a queryset. The queryset is what filters it
        down to a single object.
        """
        model_obj = G(TestModel)
        G(TestModel)
        self.assertEquals(model_obj, TestModel.objects.filter(id=model_obj.id).single())


class BulkUpdateTest(TestCase):
    """
    Tests the bulk_update function.
    """
    def test_foreign_key_pk_using_id(self):
        """
        Tests a bulk update on a model that has a primary key to a foreign key. It uses the id of the pk in the
        update
        """
        t = G(TestPkForeignKey, char_field='hi')
        TestPkForeignKey.objects.bulk_update(
            [TestPkForeignKey(my_key_id=t.my_key_id, char_field='hello')], ['char_field'])
        self.assertEquals(TestPkForeignKey.objects.count(), 1)
        self.assertTrue(TestPkForeignKey.objects.filter(char_field='hello', my_key=t.my_key).exists())

    def test_foreign_key_pk(self):
        """
        Tests a bulk update on a model that has a primary key to a foreign key. It uses the foreign key itself
        in the update
        """
        t = G(TestPkForeignKey, char_field='hi')
        TestPkForeignKey.objects.bulk_update([TestPkForeignKey(my_key=t.my_key, char_field='hello')], ['char_field'])
        self.assertEquals(TestPkForeignKey.objects.count(), 1)
        self.assertTrue(TestPkForeignKey.objects.filter(char_field='hello', my_key=t.my_key).exists())

    def test_char_pk(self):
        """
        Tests a bulk update on a model that has a primary key to a char field.
        """
        G(TestPkChar, char_field='hi', my_key='1')
        TestPkChar.objects.bulk_update(
            [TestPkChar(my_key='1', char_field='hello')], ['char_field'])
        self.assertEquals(TestPkChar.objects.count(), 1)
        self.assertTrue(TestPkChar.objects.filter(char_field='hello', my_key='1').exists())

    def test_none(self):
        """
        Tests when no values are provided to bulk update.
        """
        TestModel.objects.bulk_update([], [])

    def test_update_floats_to_null(self):
        """
        Tests updating a float field to a null field.
        """
        test_obj_1 = G(TestModel, int_field=1, float_field=2)
        test_obj_2 = G(TestModel, int_field=2, float_field=3)
        test_obj_1.float_field = None
        test_obj_2.float_field = None

        TestModel.objects.bulk_update([test_obj_1, test_obj_2], ['float_field'])

        test_obj_1 = TestModel.objects.get(id=test_obj_1.id)
        test_obj_2 = TestModel.objects.get(id=test_obj_2.id)
        self.assertIsNone(test_obj_1.float_field)
        self.assertIsNone(test_obj_2.float_field)

    def test_update_ints_to_null(self):
        """
        Tests updating an int field to a null field.
        """
        test_obj_1 = G(TestModel, int_field=1, float_field=2)
        test_obj_2 = G(TestModel, int_field=2, float_field=3)
        test_obj_1.int_field = None
        test_obj_2.int_field = None

        TestModel.objects.bulk_update([test_obj_1, test_obj_2], ['int_field'])

        test_obj_1 = TestModel.objects.get(id=test_obj_1.id)
        test_obj_2 = TestModel.objects.get(id=test_obj_2.id)
        self.assertIsNone(test_obj_1.int_field)
        self.assertIsNone(test_obj_2.int_field)

    def test_update_chars_to_null(self):
        """
        Tests updating a char field to a null field.
        """
        test_obj_1 = G(TestModel, int_field=1, char_field='2')
        test_obj_2 = G(TestModel, int_field=2, char_field='3')
        test_obj_1.char_field = None
        test_obj_2.char_field = None

        TestModel.objects.bulk_update([test_obj_1, test_obj_2], ['char_field'])

        test_obj_1 = TestModel.objects.get(id=test_obj_1.id)
        test_obj_2 = TestModel.objects.get(id=test_obj_2.id)
        self.assertIsNone(test_obj_1.char_field)
        self.assertIsNone(test_obj_2.char_field)

    def test_objs_no_fields_to_update(self):
        """
        Tests when objects are given to bulk update with no fields to update. Nothing should change in
        the objects.
        """
        test_obj_1 = G(TestModel, int_field=1)
        test_obj_2 = G(TestModel, int_field=2)
        # Change the int fields on the models
        test_obj_1.int_field = 3
        test_obj_2.int_field = 4
        # Do a bulk update with no update fields
        TestModel.objects.bulk_update([test_obj_1, test_obj_2], [])
        # The test objects int fields should be untouched
        test_obj_1 = TestModel.objects.get(id=test_obj_1.id)
        test_obj_2 = TestModel.objects.get(id=test_obj_2.id)
        self.assertEquals(test_obj_1.int_field, 1)
        self.assertEquals(test_obj_2.int_field, 2)

    def test_objs_one_field_to_update(self):
        """
        Tests when objects are given to bulk update with one field to update.
        """
        test_obj_1 = G(TestModel, int_field=1)
        test_obj_2 = G(TestModel, int_field=2)
        # Change the int fields on the models
        test_obj_1.int_field = 3
        test_obj_2.int_field = 4
        # Do a bulk update with the int fields
        TestModel.objects.bulk_update([test_obj_1, test_obj_2], ['int_field'])
        # The test objects int fields should be untouched
        test_obj_1 = TestModel.objects.get(id=test_obj_1.id)
        test_obj_2 = TestModel.objects.get(id=test_obj_2.id)
        self.assertEquals(test_obj_1.int_field, 3)
        self.assertEquals(test_obj_2.int_field, 4)

    def test_objs_one_field_to_update_ignore_other_field(self):
        """
        Tests when objects are given to bulk update with one field to update. This test changes another field
        not included in the update and verifies it is not updated.
        """
        test_obj_1 = G(TestModel, int_field=1, float_field=1.0)
        test_obj_2 = G(TestModel, int_field=2, float_field=2.0)
        # Change the int and float fields on the models
        test_obj_1.int_field = 3
        test_obj_2.int_field = 4
        test_obj_1.float_field = 3.0
        test_obj_2.float_field = 4.0
        # Do a bulk update with the int fields
        TestModel.objects.bulk_update([test_obj_1, test_obj_2], ['int_field'])
        # The test objects int fields should be untouched
        test_obj_1 = TestModel.objects.get(id=test_obj_1.id)
        test_obj_2 = TestModel.objects.get(id=test_obj_2.id)
        self.assertEquals(test_obj_1.int_field, 3)
        self.assertEquals(test_obj_2.int_field, 4)
        # The float fields should not be updated
        self.assertEquals(test_obj_1.float_field, 1.0)
        self.assertEquals(test_obj_2.float_field, 2.0)

    def test_objs_two_fields_to_update(self):
        """
        Tests when objects are given to bulk update with two fields to update.
        """
        test_obj_1 = G(TestModel, int_field=1, float_field=1.0)
        test_obj_2 = G(TestModel, int_field=2, float_field=2.0)
        # Change the int and float fields on the models
        test_obj_1.int_field = 3
        test_obj_2.int_field = 4
        test_obj_1.float_field = 3.0
        test_obj_2.float_field = 4.0
        # Do a bulk update with the int fields
        TestModel.objects.bulk_update([test_obj_1, test_obj_2], ['int_field', 'float_field'])
        # The test objects int fields should be untouched
        test_obj_1 = TestModel.objects.get(id=test_obj_1.id)
        test_obj_2 = TestModel.objects.get(id=test_obj_2.id)
        self.assertEquals(test_obj_1.int_field, 3)
        self.assertEquals(test_obj_2.int_field, 4)
        # The float fields should be updated
        self.assertEquals(test_obj_1.float_field, 3.0)
        self.assertEquals(test_obj_2.float_field, 4.0)


class UpsertTest(TestCase):
    """
    Tests the upsert method in the manager utils.
    """
    @patch.object(TestModel, 'save', spec_set=True)
    def test_no_double_save_on_create(self, mock_save):
        """
        Tests that save isn't called on upsert after the object has been created.
        """
        model_obj, created = TestModel.objects.upsert(int_field=1, updates={'float_field': 1.0})
        self.assertEquals(mock_save.call_count, 1)

    def test_save_on_update(self):
        """
        Tests that save is called when the model is updated
        """
        model_obj, created = TestModel.objects.upsert(int_field=1, updates={'float_field': 1.0})

        with patch.object(TestModel, 'save', spec_set=True) as mock_save:
            TestModel.objects.upsert(int_field=1, updates={'float_field': 1.1})
            self.assertEquals(mock_save.call_count, 1)

    def test_no_save_on_no_update(self):
        """
        Tests that save is not called on upsert if the model is not actually updated.
        """
        model_obj, created = TestModel.objects.upsert(int_field=1, updates={'float_field': 1.0})

        with patch.object(TestModel, 'save', spec_set=True) as mock_save:
            TestModel.objects.upsert(int_field=1, updates={'float_field': 1.0})
            self.assertEquals(mock_save.call_count, 0)

    def test_upsert_creation_no_defaults(self):
        """
        Tests an upsert that results in a created object. Don't use defaults
        """
        model_obj, created = TestModel.objects.upsert(int_field=1)
        self.assertTrue(created)
        self.assertEquals(model_obj.int_field, 1)
        self.assertIsNone(model_obj.float_field)
        self.assertIsNone(model_obj.char_field)

    def test_upsert_creation_defaults(self):
        """
        Tests an upsert that results in a created object. Defaults are used.
        """
        model_obj, created = TestModel.objects.upsert(int_field=1, defaults={'float_field': 1.0})
        self.assertTrue(created)
        self.assertEquals(model_obj.int_field, 1)
        self.assertEquals(model_obj.float_field, 1.0)
        self.assertIsNone(model_obj.char_field)

    def test_upsert_creation_updates(self):
        """
        Tests an upsert that results in a created object. Updates are used.
        """
        model_obj, created = TestModel.objects.upsert(int_field=1, updates={'float_field': 1.0})
        self.assertTrue(created)
        self.assertEquals(model_obj.int_field, 1)
        self.assertEquals(model_obj.float_field, 1.0)
        self.assertIsNone(model_obj.char_field)

    def test_upsert_creation_defaults_updates(self):
        """
        Tests an upsert that results in a created object. Defaults are used and so are updates.
        """
        model_obj, created = TestModel.objects.upsert(
            int_field=1, defaults={'float_field': 1.0}, updates={'char_field': 'Hello'})
        self.assertTrue(created)
        self.assertEquals(model_obj.int_field, 1)
        self.assertEquals(model_obj.float_field, 1.0)
        self.assertEquals(model_obj.char_field, 'Hello')

    def test_upsert_creation_no_defaults_override(self):
        """
        Tests an upsert that results in a created object. Defaults are not used and
        the updates values override the defaults on creation.
        """
        test_model = G(TestModel)
        model_obj, created = TestForeignKeyModel.objects.upsert(int_field=1, updates={
            'test_model': test_model,
        })
        self.assertTrue(created)
        self.assertEquals(model_obj.int_field, 1)
        self.assertEquals(model_obj.test_model, test_model)

    def test_upsert_creation_defaults_updates_override(self):
        """
        Tests an upsert that results in a created object. Defaults are used and so are updates. Updates
        override the defaults.
        """
        model_obj, created = TestModel.objects.upsert(
            int_field=1, defaults={'float_field': 1.0}, updates={'char_field': 'Hello', 'float_field': 2.0})
        self.assertTrue(created)
        self.assertEquals(model_obj.int_field, 1)
        self.assertEquals(model_obj.float_field, 2.0)
        self.assertEquals(model_obj.char_field, 'Hello')

    def test_upsert_no_creation_no_defaults(self):
        """
        Tests an upsert that already exists. Don't use defaults
        """
        G(TestModel, int_field=1, float_field=None, char_field=None)
        model_obj, created = TestModel.objects.upsert(int_field=1)
        self.assertFalse(created)
        self.assertEquals(model_obj.int_field, 1)
        self.assertIsNone(model_obj.float_field)
        self.assertIsNone(model_obj.char_field)

    def test_upsert_no_creation_defaults(self):
        """
        Tests an upsert that already exists. Defaults are used but don't matter since the object already existed.
        """
        G(TestModel, int_field=1, float_field=None, char_field=None)
        model_obj, created = TestModel.objects.upsert(int_field=1, defaults={'float_field': 1.0})
        self.assertFalse(created)
        self.assertEquals(model_obj.int_field, 1)
        self.assertIsNone(model_obj.float_field)
        self.assertIsNone(model_obj.char_field)

    def test_upsert_no_creation_updates(self):
        """
        Tests an upsert that already exists. Updates are used.
        """
        G(TestModel, int_field=1, float_field=2.0, char_field=None)
        model_obj, created = TestModel.objects.upsert(int_field=1, updates={'float_field': 1.0})
        self.assertFalse(created)
        self.assertEquals(model_obj.int_field, 1)
        self.assertEquals(model_obj.float_field, 1.0)
        self.assertIsNone(model_obj.char_field)

    def test_upsert_no_creation_defaults_updates(self):
        """
        Tests an upsert that already exists. Defaults are used and so are updates.
        """
        G(TestModel, int_field=1, float_field=2.0, char_field='Hi')
        model_obj, created = TestModel.objects.upsert(
            int_field=1, defaults={'float_field': 1.0}, updates={'char_field': 'Hello'})
        self.assertFalse(created)
        self.assertEquals(model_obj.int_field, 1)
        self.assertEquals(model_obj.float_field, 2.0)
        self.assertEquals(model_obj.char_field, 'Hello')

    def test_upsert_no_creation_defaults_updates_override(self):
        """
        Tests an upsert that already exists. Defaults are used and so are updates. Updates override the defaults.
        """
        G(TestModel, int_field=1, float_field=3.0, char_field='Hi')
        model_obj, created = TestModel.objects.upsert(
            int_field=1, defaults={'float_field': 1.0}, updates={'char_field': 'Hello', 'float_field': 2.0})
        self.assertFalse(created)
        self.assertEquals(model_obj.int_field, 1)
        self.assertEquals(model_obj.float_field, 2.0)
        self.assertEquals(model_obj.char_field, 'Hello')
