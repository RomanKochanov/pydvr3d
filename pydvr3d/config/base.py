import re
import copy
import inspect
from collections import OrderedDict
import configparser

def __get_members_recursive__(cls,members):
    # get stuff from current class
    for attribute in cls.__dict__.keys():
        value = getattr(cls, attribute)
        if attribute[:2] != '__' and not callable(value):
            if attribute not in members:
                members[attribute] = value
    # get stuff from base class recursively
    bases = cls.__bases__
    if len(bases)>1:
        raise Exception(
            'ConfigSection instance cannot have more than one parents')
    base = bases[0]
    if base is not ConfigSection:
        __get_members_recursive__(base,members)
        
class ConfigSection:
    """ 
    Class for the config part. 
    Essential class parameters:
        __name__: config section name 
        __header__: short header telling what the section izs about
        __template__: the config representation of the section
    The parameters of the section are given within template
    """
    
    def __init__(self,**kwargs):
        # set members 
        self.__set_members__(kwargs=kwargs)
        # set defaults (absent members)
        template_keys = self.__class__.__get_keys_from_template__()
        members = self.__get_members__()
        absent_keys = set(template_keys)-set(members.keys())
        for key in absent_keys:
            setattr(self,key,None)
    
    @classmethod
    def __get_keys_from_template__(cls):
        return re.findall('{([a-zA-Z][a-zA-Z0-9_]*)}',cls.__template__)
        
    @classmethod
    def __get_members_from_class__(cls):
        members = {}
        __get_members_recursive__(cls,members)
        return members

    def __get_members_from_instance__(self):
        members = {}
        for attribute in self.__dict__.keys():
            value = getattr(self, attribute)
            if attribute[:2] != '__' and not callable(value):
                members[attribute] = value
        return members

    def __get_members__(self):
        members = copy.deepcopy(self.__get_members_from_class__())
        members.update(copy.deepcopy(self.__get_members_from_instance__()))
        return members

    def __set_members__(self,kwargs,ignore_empty_values=True):
        allowed_members = self.__get_members_from_instance__()
        allowed_members = set(self.__get_keys_from_template__()).\
            union(allowed_members.keys())
        for kwarg in kwargs:
            if kwarg in allowed_members:
                if ignore_empty_values and not kwargs[kwarg]:
                    continue
                setattr(self,kwarg,kwargs[kwarg])
            else:
                raise Exception('the key "%s" is not in dict'%kwarg)

    @property
    def buffer(self):
        template_keys = self.__class__.__get_keys_from_template__()
        members = self.__get_members__()
        # add keys existing as members
        dct = {key:'{key}: {value}'.\
            format(key=key,value=members[key] if members[key] is not None else '') \
                for key in members if key in template_keys}
        # make a header part
        head = '{binding}\n# {header} #\n{binding}\n[{name}]\n'.\
            format(binding='#'*(len(self.__header__)+4),
                header=self.__header__,name=self.__name__)
        # all done
        return head + self.__class__.__template__.format(**dct) + '\n'
        
    def get(self,key,default=None):
        try:
            return getattr(self,key)
        except AttributeError:
            return default
        
    def print(cls):
        print(cls.buffer)
        
    def __getitem__(self,key):
        return getattr(self,key)

    def __setitem__(self,key,value):
        allowed_members = self.__get_members__()
        if key in allowed_members:
            setattr(self,key,value)
        else:            
            raise Exception('the key "%s" is not in dict'%key)

class Config:
    """ Class for the config. """
    
    def __init__(self,*sections):
        self.__sections__ = OrderedDict()
        for section in sections:
            if type(section) is type:
                if issubclass(section,ConfigSection):
                    section = section()
                else:
                    raise Exception(
                        'wrong class supplied: %s'%str(section))
            self.__sections__[section.__name__] = section
    
    def setpars(self,pars,ignore_empty_values=True):
        for section_name in pars:
            pp = pars[section_name]
            self.__sections__[section_name].__set_members__(
                kwargs=pp,ignore_empty_values=ignore_empty_values)
            
    def merge_section(self,section,ignore_empty_values=True):
        if type(section) is type:
            section = section()
        dct = {section.__name__:section.__get_members__()}
        self.setpars(dct,ignore_empty_values=ignore_empty_values)
        
    def merge_config(self,config,ignore_empty_values=True):
        for section_name in config.__sections__:
            section = config.__sections__[section_name]
            if section_name not in self.__sections__:
                self.__sections__[section_name] = section.__class__()
            self.merge_section(section,ignore_empty_values=ignore_empty_values)
    
    @property
    def buffer(self):
        buf = ''
        for name in self.__sections__:
            section = self.__sections__[name]
            buf += section.buffer
        return buf
        
    def print(self):
        print(self.buffer)

    def __getitem__(self,section_name):
        return self.__sections__[section_name]
        
    def save(self,filename):
        with open(filename,'w') as f:
            f.write(self.buffer)
        
    def load(self,filename,ignore_empty_values=False):
        conf_ = configparser.ConfigParser(allow_no_value=True)
        conf_.read(filename)
        sections = conf_.sections()
        for section in sections:
            pardict = dict(conf_.items(section))
            self[section].__set_members__(kwargs=pardict,
                ignore_empty_values=ignore_empty_values)
 
def print_help(modules,more=False):
    """ 
    Explore modules with the config section templates, 
    and print their docstrings 
    """
    print(r'||||||||||||||||||||||||||||||||')
    print(r'||   AVAILABLE TEMPLATES:     ||')
    print(r'||||||||||||||||||||||||||||||||')

    for module_name in modules:
                
        module = modules[module_name]
                
        if more: print('\n==============================================')
        print(module.__name__)
        if more: print('==============================================\n')
        
        for obj_name in dir(module):
            obj = getattr(module,obj_name)
            if type(obj) is type and \
                obj is not ConfigSection and \
                issubclass(obj,ConfigSection):
                
                if more: print('///////////////////////////////////')
                print('   ',obj.__name__)
                if more: print(obj.__doc__)
                if more: print()