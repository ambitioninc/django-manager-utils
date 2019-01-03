# flake8: noqa
from .version import __version__
from .manager_utils import (
    ManagerUtilsMixin, ManagerUtilsManager, ManagerUtilsQuerySet, post_bulk_operation,
    upsert, bulk_update, single, get_or_none, bulk_upsert, bulk_upsert2, id_dict, sync,
    sync2
)

default_app_config = 'manager_utils.apps.ManagerUtilsConfig'
