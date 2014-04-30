from django.db import models
from manager_utils import ManagerUtilsManager


class TestModel(models.Model):
    """
    A model for testing manager utils.
    """
    int_field = models.IntegerField()
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
