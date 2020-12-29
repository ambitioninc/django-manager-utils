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
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Framework :: Django :: 2.2',
        'Framework :: Django :: 3.0',
        'Framework :: Django :: 3.1',
    ],
    install_requires=[
        'Django>=2.2',
        'django-query-builder>=2.0.0',
    ],
    tests_require=[
        'coverage',
        'freezegun',
        'mock',
        'psycopg2',
        'django-nose>=1.3',
        'django-dynamic-fixture',
        'pytz',
        'django-timezone-field',
        'parameterized',
    ],
    test_suite='run_tests.run',
    include_package_data=True,
)
