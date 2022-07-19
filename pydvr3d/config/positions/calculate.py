from ..base import ConfigSection

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
    ncores = 10
    nnodes = 1
    memory = 10000
    walltime = 24
    script = 'job.slurm'