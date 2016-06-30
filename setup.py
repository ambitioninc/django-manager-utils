# import multiprocessing to avoid this bug (http://bugs.python.org/issue15881#msg170215_
import multiprocessing
assert multiprocessing
import re
from setuptools import setup, find_packages


def get_version():
    """
    Extracts the version number from the version.py file.
    """
    VERSION_FILE = 'manager_utils/version.py'
    mo = re.search(r'^__version__ = [\'"]([^\'"]*)[\'"]', open(VERSION_FILE, 'rt').read(), re.M)
    if mo:
        return mo.group(1)
    else:
        raise RuntimeError('Unable to find version string in {0}.'.format(VERSION_FILE))


setup(
    name='django-manager-utils',
    version=get_version(),
    description='Model manager utilities for Django',
    long_description=open('README.rst').read(),
    url='http://github.com/ambitioninc/django-manager-utils/',
    author='Wes Kendall',
    author_email='opensource@ambition.com',
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Framework :: Django',
    ],
    install_requires=[
        'django>=1.7',
        'django-query-builder>=0.11.2',
    ],
    tests_require=[
        'coverage',
        'mock',
        'psycopg2',
        'django-nose>=1.3',
        'django-dynamic-fixture',
        'pytz',
        'django-timezone-field',
    ],
    test_suite='run_tests.run_tests',
    include_package_data=True,
)
