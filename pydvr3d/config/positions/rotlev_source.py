from ..base import ConfigSection
from .. import types

class Default(ConfigSection):
    __name__ = 'ROTLEV_SOURCE'
    __header__ = 'PATH TO THE ROTLEV SOURCE'
    __template__ = \
"""
# Root path for sources.
{rotlev_source_root}

# Pathes to the ROTLEV subprogram sources.
{rotlev3b_sources}
{rotlev3z_sources}
{rotlev3_sources}
"""
    # parameter types
    __rotlev_source_root__type__ = types.String
    __rotlev3b_sources__type__ = types.String
    __rotlev3z_sources__type__ = types.String
    __rotlev3_sources__type__ = types.String
    
    # parameter defaults
    rotlev_source_root = '/home/roman/work/dvr_me/src.2020/dvr3d/source'
    rotlev3b_sources = 'rotlev3b_segmented.f90; f02fjf.f'
    rotlev3z_sources = 'rotlev3z.f90; f02fjf.f'
    rotlev3_sources = 'rotlev3_segmented.f90; f02fjf.f'
