class ConfigParameterType:
    """ Abstract class for config type definition """
    
    @classmethod
    def dumps(cls,val):
        """ Dump value to string including None """
        if val is None:
            return ''
        else:
            return cls.to_str(val)
    
    @classmethod
    def loads(cls,buf):
        """ Load value from string including empty string """
        if buf=='':
            return None
        else:
            return cls.from_str(buf)
           
    @classmethod
    def to_str(cls,val):
        """ Dump value to string """
        raise NotImplementedError
        
    @classmethod
    def from_str(cls,buf):
        """ Load value from string """
        raise NotImplementedError
    
class String(ConfigParameterType):

    @classmethod
    def to_str(cls,val):
        return str(val)
    
    @classmethod
    def from_str(cls,buf):
        return buf

class Float(ConfigParameterType):

    @classmethod
    def to_str(cls,val):
        return str(val)
    
    @classmethod
    def from_str(cls,buf):
        return float(buf)
    
class Integer(ConfigParameterType):

    @classmethod
    def to_str(cls,val):
        return str(val)
    
    @classmethod
    def from_str(cls,buf):
        return int(buf)
    
class Boolean(ConfigParameterType):

    @classmethod
    def to_str(cls,val):
        return str(val)
    
    @classmethod
    def from_str(cls,buf):
        if buf.lower() in ['true','.true.','t','.t.','1']:
            return True
        elif buf.lower() in ['false','.false.','f','.f.','0']:
            return False
        else:
            raise Exception('cannot convert "%s" to Boolean'%buf)
