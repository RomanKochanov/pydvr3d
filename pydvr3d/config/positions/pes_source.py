from ..base import ConfigSection
from .. import types

class Default(ConfigSection):
    __name__ = 'PES_SOURCE'
    __header__ = 'PATH TO THE PES SOURCE'
    __template__ = \
"""
# Root path.
{pes_source_root}

# Pathes to common PES source codes
{pes_sources_common}

# Pathes to model-specific PES source codes
{pes_sources_model}

# Additional pathes to PES source codes (root path is not used)
{pes_sources_aux}

# Path to PES parameters file
{pes_parameters_path}
"""
    # parameter types
    __pes_source_root__type__ = types.String
    __pes_sources_common__type__ = types.String
    __pes_sources_model__type__ = types.String
    __pes_sources_aux__type__ = types.String
    __pes_parameters_path__type__ = types.String
    
class PES_EXPMASS(Default):
    """ Generic template for the expmass-formatted PES """
    pes_source_root = '/home/roman/work/pes_expmass'
    pes_sources_common = 'common/pes_par.f90; common/pots.f90; common/read_pes_par.f90; common/pes_noadifor.f90'
    
class OZONE_JCP2013_NR_PES(PES_EXPMASS):
    """ 'Non-reef' ozone PES published in JCP (2013) """
    pes_sources_model = 'model_mep_4test/pes_.f'
    pes_parameters_path = 'model_mep_4test/JCP_2013_PARAMS/ozone_abini_NR_PES_vt_JCP_2013.par'
