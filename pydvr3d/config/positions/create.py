from ..base import ConfigSection

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
    states = 'states.txt'
    job_script = 'job.sh'
    job_manager = 'Shell'
    summary = 'summary.out'
