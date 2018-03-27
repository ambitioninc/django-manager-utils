Release Notes
=============

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
