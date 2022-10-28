from ..base import ConfigSection
from .. import types

class Default(ConfigSection):
    __name__ = 'CALCULATE'
    __header__ = 'MANAGE CALC RESOURCES'
    __template__ = \
"""
# Number of cores per job.
{ncores}

# Number of nodes per job.
{nnodes}

# Memory amount per job.
{memory}

# Job time limit.
{walltime}

# Default name for the job script.
{script}
"""
    # parameter types
    __ncores__type__ = types.Integer
    __nnodes__type__ = types.Integer
    __memory__type__ = types.Integer
    __walltime__type__ = types.Integer
    __script__type__ = types.String
   
    # parameter defaults
    ncores = 10
    nnodes = 1
    memory = 10000
    walltime = 24
    script = 'job.slurm'
