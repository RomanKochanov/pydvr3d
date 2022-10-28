from ..base import ConfigSection
from .. import types

class Default(ConfigSection):
    """ Default generate the pure vibrations """
    __name__ = 'GENERATE'
    __header__ = 'OPTIONS FOR GENERATING THE ROTATIONAL STATES'
    __template__ = \
"""
# Angular moment values.
{jrot}

# Basis parameter KMIN values.
{kmin}

# Basis parameter IPAR values.
{ipar}

# Naming pattern.
{pattern}

# Stage output for DVR-labeled states.
{output}
"""
    # parameter types
    __jrot__type__ = types.String
    __kmin__type__ = types.String
    __ipar__type__ = types.String
    __pattern__type__ = types.String
    __output__type__ = types.String
    
    # parameter defaults
    jrot = '0'
    kmin = '0,1'
    ipar = '0,1'
    pattern = "'jki_{0:02d}{1:d}{2:d}f'.format(jrot,kmin,ipar)"
    output = 'states.txt'
