Release Notes
=============

v3.0.1
------
* Switch to github actions

v3.0.0
------
* Add support for django 3.2, 4.0, 4.1
* Add support for python 3.9
* Drop support for python 3.6

v2.0.1
------
* Fixed docstring (alextatarinov)

v2.0.0
------
* Support django 2.2, 3.0, 3.1 only
* Support python 3.6, 3.7, 3.8 only

v1.4.0
------
* Only support django >= 2.0 and python >= 3.6
* Fix bulk upsert sql issue to distinguish fields by table

v1.3.2
------
* Fix bulk_update not properly casting fields
* Add support for returning upserts with multiple unique fields for non native

v1.3.1
------
* BAD RELEASE DO NOT USE

v1.3.0
------
* Updated version 2 interface
* Added optimizations to bulk_upsert and sync to ignore duplicate updates

v1.2.0
------
* Added a parallel version 2 interface for bulk_upsert2 and sync2

v1.1.1
------
* Fix setup version requirements

v1.1.0
------
* Use tox to support more versions

v1.0.0
------
* Drop Django 1.9
* Drop Django 1.10
* Add Django 2.0
* Drop python 2.7
* Drop python 3.4

v0.13.2
-------
* Optimize native sync

v0.13.1
-------
* Add native support for the sync method, thanks @wesleykendall

v0.13.0
-------
* Add python 3.6 support
* Drop Django 1.7 support
* Add Django 1.10 support
* Add Django 1.11 support

v0.12.0
-------
* Add python 3.5 support, drop django 1.7 support

v0.11.1
-------
* Added bulk_create override for ManagerUtilsQuerySet to emit post bulk operation signal

v0.11.0
-------
* Where default return value of bulk_upsert was None, now it is a list of lists, the first being the list of updated models, the second being the created models

v0.10.0
-------
* Add native postgres upsert support

v0.9.1
------
* Add Django 1.9 support

v0.8.4
------
* Fixed a bug when doing bulk updates on foreign key ID fields in Django 1.7

v0.8.3
------
* Added support for doing bulk updates on custom django fields

v0.8.0
------
* Dropped Django 1.6 support and added Django 1.8 support

v0.7.2
------
* Added Django 1.7 app config

v0.7.1
------
* Added multiple database support for ``bulk_upsert``

v0.6.4
------
* Fixed ``.bulk_create()`` argument error

v0.6.1
------
* Added RTD docs
* Added python3 compatibility
