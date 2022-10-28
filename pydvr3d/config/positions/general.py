from ..base import ConfigSection
from .. import types

class Default(ConfigSection):
    __name__ = 'GENERAL'
    __header__ = 'GENERAL SETTINGS'
    __template__ = \
"""
# Name of the project.
{project}
"""
    # parameter types
    __project__type__ = types.String
