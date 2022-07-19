from collections import OrderedDict

from ..base import Config
from . import general, molecule, dvr3drjz_input, \
    dvr3drjz_source, rotlev_source, pes_source, \
    build, resources, generate, create, calculate

template_modules_list = [general, molecule, dvr3drjz_input, \
    dvr3drjz_source, rotlev_source, pes_source, \
    build, resources, generate, create, calculate]

template_modules_dict = OrderedDict()
for mod in template_modules_list:
    template_modules_dict[mod.__name__.split('.')[-1]] = mod

config = Config(*[getattr(module,'Default') for module in template_modules_list])