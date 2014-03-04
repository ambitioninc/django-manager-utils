from django.core.exceptions import ValidationError


def import_string(module_string):
    """
    Imports a string as a python object. Returns None if the module could not be
    imported.
    """
    try:
        path = '.'.join(module_string.split('.')[:-1])
        module_name = module_string.split('.')[-1]
        file_name = module_string.split('.')[-2]

        module_path = __import__(path, globals(), locals(), [file_name])
        module = getattr(module_path, module_name)
    except:
        raise ValidationError('Could not import module {0}'.format(module_string))

    return module
