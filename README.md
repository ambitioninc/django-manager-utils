[![Build Status](https://travis-ci.org/ambitioninc/django-callable-field.png)](https://travis-ci.org/ambitioninc/django-callable-field)
django-callable-field
=====================

Store callable functions/classes in Django models.

## A Brief Overview
The Django callable field app provides a custom field for a Django model that stores a callable function or class. This provides the ability to easily store paths to code in a model field and quickly execute it without having to load it manually.


## Storing and Calling a Function
Assume that you have defined the following function that returns the argument that you passed to it:

    def ret_arg(arg):
        return arg

In order to save this callable function to a model, simply do the following:

    from django.db import models
    from callable_field import CallableField

    class CallableModel(models.Model):
        my_function = CallableField(max_length=128)

    model_obj = CallableModel.objects.create(my_function='full_path_to_function.ret_arg')
    # Call the function from the my_function field and print the results
    print model_obj.my_function('Hello World')
    Hello World

You can similarly pass a function variable (instead of a string) to the model constructor:

    model_obj = CallableModel.objects.create(my_function=ret_arg)
    print model_obj.my_function('Hello World')
    Hello World


## Storing and Calling a Class
Similar to the function example, assume that you have defined the following class that returns the argument passes to its constructor:

    class RetArg(object):
        def __init__(arg):
            self.arg = arg

        def ret_arg():
            return self.arg

Similar to the function example, do the following to save the class:

    from django.db import models
    from callable_field import CallableField

    class CallableModel(models.Model):
        my_class = CallableField(max_length=128)

    model_obj = CallableModel.objects.create(my_class='full_path_to_class.RetArg')
    # Instantiate the class from the my_class field and print the results
    print model_obj.my_class('Hello World').ret_arg()
    Hello World

You can similarly pass a class variable (instead of a string) to the model constructor:

    model_obj = CallableModel.objects.create(my_class=RetArg)
    print model_obj.my_class('Hello World').ret_arg()
    Hello World
