from django.db import models


class ForeignKeyTestModel(models.Model):
    value = models.CharField(max_length=128)


class TestModel(models.Model):
    """
    A model for testing manager utils.
    """
    int_field = models.IntegerField()
    char_field = models.CharField(max_length=128)
    float_field = models.FloatField()
    foreign_key = models.ForeignKey(ForeignKeyTestModel)
