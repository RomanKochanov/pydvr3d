from ..base import ConfigSection
from .. import types

class Default(ConfigSection):
    __name__ = 'BUILD'
    __header__ = 'COMPILER AND LINKER OPTIONS'
    __template__ = \
"""
# Compiler name.
{compiler}

# Compiler options.
{compiler_options}

# Linker options.
{linker_options}
"""
    # parameter types
    __compiler__type__ = types.String
    __compiler_options__type__ = types.String
    __linker_options__type__ = types.String

class Linux_ifort_oneAPI_2021_static(Default):
    """
    MKL link line advisor output:
        advisor: 6.16
        product: oneMKL 2021
        os: Linux
        language: Fortran
        compiler: Intel(R) Fortran Classic
        architecture: Inter(R) 64
        linking: Static
        interface_layer: Fortran API with 32-bit integer
        threading_layer: OpenMP threading
        openmp_library: Intel(R) (libiomp5)
    """
    compiler = 'ifort'
    compiler_options = '-O3 -ftz -zero -ip -parallel -qopenmp -traceback -fpp -fPIC -mcmodel=large -shared-intel -I"${MKLROOT}/include"'
    linker_options = '-Wl,--start-group ${MKLROOT}/lib/intel64/libmkl_intel_lp64.a ${MKLROOT}/lib/intel64/libmkl_intel_thread.a ${MKLROOT}/lib/intel64/libmkl_core.a -Wl,--end-group -liomp5 -lpthread -lm -ldl'

class Linux_ifort_oneAPI_2021_dynamic(Default):
    """
    MKL link line advisor output:
        advisor: 6.16
        product: oneMKL 2021
        os: Linux
        language: Fortran
        compiler: Intel(R) Fortran Classic
        architecture: Inter(R) 64
        linking: Dynamic
        interface_layer: Fortran API with 32-bit integer
        threading_layer: OpenMP threading
        openmp_library: Intel(R) (libiomp5)
    """
    compiler = 'ifort'
    compiler_options = '-O3 -ftz -zero -ip -parallel -qopenmp -traceback -fpp -fPIC -mcmodel=large -shared-intel -I"${MKLROOT}/include"'
    linker_options = '-L${MKLROOT}/lib/intel64 -lmkl_intel_lp64 -lmkl_intel_thread -lmkl_core -liomp5 -lpthread -lm -ldl'

class Linux_ifort_oneAPI_2021_sdl(Default):
    """
    MKL link line advisor output:
        advisor: 6.16
        product: oneMKL 2021
        os: Linux
        language: Fortran
        compiler: Intel(R) Fortran Classic
        architecture: Inter(R) 64
        linking: Single Dynamic Library
        interface_layer: [Selected at runtime]
        threading_layer: [Selected at runtime]
    """
    compiler = 'ifort'
    compiler_options = '-O3 -ftz -zero -ip -parallel -qopenmp -traceback -fpp -fPIC -mcmodel=large -shared-intel -I"${MKLROOT}/include"'
    linker_options = '-L${MKLROOT}/lib/intel64 -lmkl_rt -lpthread -lm -ldl'
