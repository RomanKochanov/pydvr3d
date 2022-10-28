from ..base import ConfigSection
from .. import types

class Default(ConfigSection):
    __name__ = 'DVR3DRJZ_SOURCE'
    __header__ = 'PATH TO THE DVR3DRJZ SOURCE'
    __template__ = \
"""
# Root path for sources.
{dvr3drjz_source_root}

# Pathes to the DVR3DRJZ subprogram sources.
{dvr3drjz_sources}
"""
    # parameter types
    __dvr3drjz_source_root__type__ = types.String
    __dvr3drjz_sources__type__ = types.String
    
    # parameter defaults
    dvr3drjz_source_root = '/home/roman/work/dvr_me/src.2020/dvr3d/source'
    dvr3drjz_sources = 'potv.f90; dvr3drjz_segmented.f90'
