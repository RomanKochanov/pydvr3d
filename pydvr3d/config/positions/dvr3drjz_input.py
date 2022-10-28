from ..base import ConfigSection
from .. import types

class Default(ConfigSection):
    __name__ = 'DVR3DRJZ_INPUT'
    __header__ = 'DVR3DRJZ AUX INPUT OPTIONS'
    __template__ = \
"""
# Mass flag: true-> use atomic masses, false-> use nuclear masses.
# This flag is ignored if user supplied masses in the MOLECULE section.
{atomic_masses}

# Coordinate system: jacobi/radau.
{coordinates}

# Namelist PRT
{prt}

# Namelist VAR
{var}

# Number of vibrational coordinates of the problem.
{ncoord}

# Number of DVR points in r2 from Gauss-(associated) Laguerre quadrature.
{npnt2}

# Number of eigenvalues and eigenvectors required.
{neval}

# Number of DVR points in θ from Gauss-(associated) Legendre quadrature.
{nalf}

# Maximum dimension of the largest intermediate 2D Hamiltonian, (ignored if IDIA = −2).
{max2d}

# Maximum dimension of the final Hamiltonian.
#   If ZCUT = F, it is the actual number of functions selected.
#   If ZCUT = T, MAX3D must be  than the number of functions selected using EMAX2.
{max3d}

# Number of DVR points in r1 from Gauss-(associated) Laguerre quadrature, (ignored if IDIA = −2).
{npnt1}

# If NCOORD = 2, RE1 is the fixed diatomic bondlength, DISS1 and WE1 ignored.
# If NCOORD = 3, RE1 = re, DISS1 = De and WE1 = ωe are Morse parameters for the r1 coordinate 
#  when ZMORS1 = T, and are spherical oscillator parameters when ZMORS1 = F.
# If IDIA = −2 RE2, DISS2, and WE2 are ignored.
{re1}
{diss1}
{we1}
{re2}
{diss2}
{we2}
"""
    # parameter types
    __atomic_masses__type__ = types.Boolean
    __coordinates__type__ = types.String
    __prt__type__ = types.String
    __var__type__ = types.String
    __ncoord__type__ = types.Integer
    __npnt2__type__ = types.Integer
    __neval__type__ = types.Integer
    __nalf__type__ = types.Integer
    __max2d__type__ = types.Integer
    __max3d__type__ = types.Integer
    __npnt1__type__ = types.Integer
    __re1__type__ = types.Float
    __diss1__type__ = types.Float
    __we1__type__ = types.Float
    __re2__type__ = types.Float
    __diss2__type__ = types.Float
    __we2__type__ = types.Float
    
    # parameter defaults
    atomic_masses = True
    coordinates = 'radau'
    prt = '&PRT ztran=.true.,  ztheta=.false., zlin=.true. &END'
    var = '&VAR meout=.false.,  &INT toler=0.000001   &END'
    ncoord = 3
    npnt2 = 40
    neval = 100
    nalf = 60
    max2d = 500
    max3d = 1000
    npnt1 = 40
    re1 = 2.87
    diss1 = 0.06
    we1 = 0.004
    re2 = 2.87
    diss2 = 0.06
    we2 = 0.004
    
class XXL(Default):
    """ Parameters for large-basis calculation """
    
    npnt2 = 100
    neval = 100
    nalf = 130
    max2d = 10000
    max3d = 20000
    npnt1 = 100
    re1 = 2.87
    diss1 = 0.06
    we1 = 0.004
    re2 = 2.87
    diss2 = 0.06
    we2 = 0.004
