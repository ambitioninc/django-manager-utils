import os
import json

from django.conf import settings


def configure_settings():
    """
    Configures settings for manage.py and for run_tests.py.
    """
    if not settings.configured:
        # Determine the database settings depending on if a test_db var is set in CI mode or not
        test_db = os.environ.get('DB', None)
        if test_db is None:
            db_config = {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': 'ambition_test',
                'USER': 'postgres',
                'PASSWORD': '',
                'HOST': 'db',
            }
        elif test_db == 'postgres':
            db_config = {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': 'manager_utils',
                'USER': 'travis',
                'PORT': '5433',
            }
            # db_config = {
            #     'ENGINE': 'django.db.backends.postgresql',
            #     'NAME': 'manager_utils',
            #     'USER': 'postgres',
            #     'PASSWORD': '',
            #     'HOST': 'db',
            # }
        elif test_db == 'sqlite':
            db_config = {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': 'manager_utils',
            }
        else:
            raise RuntimeError('Unsupported test DB {0}'.format(test_db))

        if os.environ.get('DB_SETTINGS'):
            db_config = json.loads(os.environ.get('DB_SETTINGS'))

        installed_apps = [
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.admin',
            'manager_utils',
            'manager_utils.tests',
        ]

        settings.configure(
            DATABASES={
                'default': db_config,
            },
            MIDDLEWARE_CLASSES={},
            INSTALLED_APPS=installed_apps,
            ROOT_URLCONF='manager_utils.urls',
            DEBUG=False,
            NOSE_ARGS=['--nocapture', '--nologcapture', '--verbosity=1'],
            TEST_RUNNER='django_nose.NoseTestSuiteRunner',
            SECRET_KEY='*',
            USE_DEPRECATED_PYTZ=True,
        )
