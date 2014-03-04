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
