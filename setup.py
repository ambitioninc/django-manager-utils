import os
from setuptools import setup


setup(
    name='django-manager-utils',
    version=open(os.path.join(os.path.dirname(__file__), 'manager_utils', 'VERSION')).read().strip(),
    description='Model manager utilities for Django',
    long_description=open('README.md').read(),
    url='http://github.com/ambitioninc/django-manager-utils/',
    author='Wes Kendall',
    author_email='wesleykendall@gmail.com',
    packages=[
        'manager_utils',
    ],
    classifiers=[
        'Programming Language :: Python',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Framework :: Django',
    ],
    dependency_links=[
        'http://github.com/wesokes/django-query-builder/tarball/0.5#egg=django-query-builder-0.5.2',
    ],
    install_requires=[
        'django>=1.6',
        'django-query-builder>=0.5.2',
    ],
    include_package_data=True,
)
