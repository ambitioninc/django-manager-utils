from django.db.models import SubfieldBase
from django.db.models.fields import CharField

from callable_field.import_string import import_string


class CallableField(CharField):
    """
    A field that loads a python path to a function or class.
    """
    description = 'A loadable path to a function or class'
    __metaclass__ = SubfieldBase
    # A cache of loaded callables for quicker lookup
    imported_module_cache = {}

    def get_prep_value(self, value):
        value = self.to_python(value)
        return self.value_to_string(value)

    def get_imported_module(self, path):
        if path not in self.imported_module_cache:
            self.imported_module_cache[path] = import_string(path)
        return self.imported_module_cache[path]

    def to_python(self, value):
        """
        Handles the following cases:
        1. If the value is already the proper type (a callable), return it.
        2. If the value is a string, import it and return the callable.

        Raises: A ValidationError if the string cannot be imported.
        """
        if callable(value):
            return value
        else:
            if value == '' and self.blank:
                return ''
            elif value is None and self.null:
                return None
            else:
                return self.get_imported_module(value)

    def value_to_string(self, obj):
        if type(obj) in (str, unicode):
            return obj
        elif obj is None:
            return None
        else:
            return '{0}.{1}'.format(obj.__module__, obj.__name__)


try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ['^callable_field\.fields\.CallableField'])
except ImportError:
    pass
