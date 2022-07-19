from ..base import ConfigSection

class Default(ConfigSection):
    __name__ = 'GENERAL'
    __header__ = 'GENERAL SETTINGS'
    __template__ = \
"""
# Name of the project.
{project}
"""