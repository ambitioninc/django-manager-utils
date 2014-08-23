from django.db import models
from manager_utils import ManagerUtilsManager


class TestModel(models.Model):
    """
    A model for testing manager utils.
    """
    int_field = models.IntegerField(null=True)
    char_field = models.CharField(max_length=128, null=True)
    float_field = models.FloatField(null=True)

    objects = ManagerUtilsManager()


class TestForeignKeyModel(models.Model):
    """
    A test model that has a foreign key.
    """
    int_field = models.IntegerField()
    test_model = models.ForeignKey(TestModel)

    objects = ManagerUtilsManager()


class TestPkForeignKey(models.Model):
    """
    A test model with a primary key thats a foreign key to another model.
    """
    my_key = models.ForeignKey(TestModel, primary_key=True)
    char_field = models.CharField(max_length=128, null=True)

    objects = ManagerUtilsManager()


class TestPkChar(models.Model):
    """
    A test model with a primary key that is a char field.
    """
    my_key = models.CharField(max_length=128, primary_key=True)
    char_field = models.CharField(max_length=128, null=True)

    objects = ManagerUtilsManager()
