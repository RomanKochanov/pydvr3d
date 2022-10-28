from ..base import ConfigSection
from .. import types

class Default(ConfigSection):
    __name__ = 'CREATE'
    __header__ = 'CREATE SUBFOLDERS FOR ROTATIONAL STATES'
    __template__ = \
"""
# List of the states to prepare.
{states}

# Job script name.
{job_script}

# Job manager: Shell, Slurm, ...
{job_manager}

# Creation summary.
{summary}
"""
    # parameter types
    __states__type__ = types.String
    __job_script__type__ = types.String
    __job_manager__type__ = types.String
    __summary__type__ = types.String
    
    # parameter defaults
    states = 'states.txt'
    job_script = 'job.sh'
    job_manager = 'Shell'
    summary = 'summary.out'
