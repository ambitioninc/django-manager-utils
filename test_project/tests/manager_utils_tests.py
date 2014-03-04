from django.test import TestCase
from django_dynamic_fixture import G

from test_project.models import TestModel, ForeignKeyTestModel


class GetOrNoneTests(TestCase):
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


class SingleTests(TestCase):
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


class TestBulkUpdate(TestCase):
    """
    Tests the bulk_update function.
    """
    def test_none(self):
        """
        Tests when no values are provided to bulk update.
        """
        TestModel.objects.bulk_update([], [])

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
