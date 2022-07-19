from ..base import ConfigSection

class Default(ConfigSection):
    __name__ = 'RESOURCES'
    __header__ = 'RESOURCE FILES FOR COMPILED PROGRAMS'
    __template__ = \
"""
# DVR3DRJZ resources.
{dvr3drjz_build_script}
{dvr3drjz_executable}
{dvr3drjz_input_template}

# ROTLEV3 resources.
{rotlev3_build_script}
{rotlev3_executable}
{rotlev3_input_template}

# ROTLEV3B resources.
{rotlev3b_build_script}
{rotlev3b_executable}
{rotlev3b_input_template}

# ROTLEV3Z resources.
{rotlev3z_build_script}
{rotlev3z_executable}
{rotlev3z_input_template}
"""
    dvr3drjz_build_script = 'build_dvr3drjz.sh'
    dvr3drjz_executable = 'dvr3drjz.x'
    dvr3drjz_input_template = 'dvr3drjz.inp'
    rotlev3_build_script = 'build_rotlev3.sh'
    rotlev3_executable = 'rotlev3.x'
    rotlev3_input_template = 'rotlev3.inp'
    rotlev3b_build_script = 'build_rotlev3b.sh'
    rotlev3b_executable = 'rotlev3b.x'
    rotlev3b_input_template = 'rotlev3b.inp'
    rotlev3z_build_script = 'build_rotlev3z.sh'
    rotlev3z_executable = 'rotlev3z.x'
    rotlev3z_input_template = 'rotlev3z.inp'
