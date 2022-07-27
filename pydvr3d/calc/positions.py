#!/usr/bin/env python

import os
import re
import sys
import stat
import argparse
import configparser as ConfigParser # python 3
import shutil
import subprocess

LABEL_DONE = '===DONE==='
LABEL_RUNNING = '===RUNNING==='

# SERIALIZATION FRAMEWORK
class Serial():
    """
    Smart serialization.
    Searches for the __class__ attribute
    to launch serialization of attributes.
    """

    __keys__ = () # serialization

    def dump(self):
        """
        Dump serialized keys given in __keys__
        field to the dictionary object.
        """
        return {key:getattr(self,key) for key in self.__keys__}

    def load(self,dct):
        """
        Load object fields from a dictionary.
        For a consistency reasons all serialized keys must be 
        presented in the input dictionary otherwise 
        an exception will be raised.
        """
        for key in self.__keys__:
            setattr(self,key,dct[key])    
# /SERIALIZATION FRAMEWORK

# DVR3DRJZ INPUT FILE EXAMPLE
"""
 &PRT ztran=.true., ztheta=.false., &END
 &VAR meout=.false. &END
dv6_sfit_nowall_mod1a.par
    3
   70    3  150   50 2000 5000   -2    2   70    0
OZONE: USING RADAU COORDINATES

 29156.9455997        29156.9455997         29156.9455997
 29156.9455997        29156.9455997         29156.9455997
    12000.             12000.
       2.87                0.06                0.004
       2.87                0.06                0.004
1443.58613558344
""";

# PAPER:
# DVR3D: A program suite for the calculation of rotation-vibration spectra of triatomic molecules
# 10.1016/j.cpc.2003.10.003

def fortran_bool(boolvar):
    if boolvar:
        return '.true.'
    else:
        return '.false.'

def serialize_var(var):
    if type(var) is bool:
        return fortran_bool(var)
    else:
        return str(var)

def deserialize_var(buf):
    buf = buf.lower()
    if buf in ['.true.','t']: 
        return True
    elif buf in ['.false.','f']:
        return False
    else:
        try:
            return int(buf)
        except ValueError:
            try:
                return float(buf)
            except ValueError:
                raise Exception('Variable "%s" has unexpected type'%name)
        
def dict_to_namelist(name,dict):
    return '&%s '%name.upper() + \
           ', '.join(['%s=%s'%(key,serialize_var(dict[key])) for key in dict]) + \
           ' &END'

def uniform(fmt,lst):
    return fmt.join(['' for _ in range(len(lst)+1)])%tuple(lst)

def read_fortran_namelist(buf):
    lookup = re.search('&([^\s]+)(.+)&end',buf,re.IGNORECASE)
    if not lookup:
        raise Exception('cannot read namelist')
    name = lookup.group(1)
    body = lookup.group(2)
    pairs = body.split(',')
    NAMELIST = {}
    for pair in pairs:
        pair = pair.strip()
        if not pair:
            continue
        name,val = pair.split('=')
        val = val.strip()
        val = deserialize_var(val)
        NAMELIST[name] = val
    return NAMELIST   

def slice(buf,lengths):
    """
    Slice string to n-character pieces.
    If "lengths" is scalar, then n = lengths.
    Last piece can contain number of characters
    less than the one given in "lengths".
    """
    if type(lengths) not in [list,tuple]:
        tail = 1 if len(buf)%lengths else 0
        npieces = int(len(buf)/lengths) + tail
        lengths = [lengths for _ in range(npieces)]
    else:
        npieces = len(lengths)
    pos = 0
    pieces = []
    for i in range(npieces):
        piece = buf[pos:pos+lengths[i]]
        pos += lengths[i]
        pieces.append(piece)
    return pieces

def to_int(val):
    if val:
        return int(val)
    else:
        return None

DVR3DRJZ_HEAVY = dict(
    prt = {'ztran':True, 'ztheta':False},
    var = {'meout':False},
    parfile = 'dv6_sfit_nowall_mod1a.par',
    ncoord = 3,  
    npnt2 = 80, 
    jrot = 0, 
    neval = 150, 
    nalf = 75, 
    max2d = 7000,
    max3d = 10000,
    idia = -2,
    kmin = 2,
    npnt1 = 80,
    ipar = 0,
    max3d2 = None,
    title = 'DVR POSITIONS CALC',
    fixcos = None,
    xmass = [29156.9455997,29156.9455997,29156.9455997],
    xmassr = [29156.9455997,29156.9455997,29156.9455997],
    emax1 = 12000.,
    emax2 = 12000.,
    re1 = 2.87,
    diss1 = 0.06,
    we1 = 0.004,
    re2 = None,
    diss2 = None,
    we2 = None,
    ezero = 0.0
)

DVR3DRJZ_LITE = dict(
    prt = {'ztran':True, 'ztheta':False},
    var = {'meout':False},
    parfile = 'dv6_sfit_nowall_mod1a.par',
    ncoord = 3,  
    npnt2 = 25, 
    jrot = 0, 
    neval = 150, 
    nalf = 35, 
    max2d = 200,
    max3d = 400,
    idia = -2,
    kmin = 2,
    npnt1 = 25,
    ipar = 0,
    max3d2 = None,
    title = 'DVR POSITIONS CALC',
    fixcos = None,
    xmass = [29156.9455997,29156.9455997,29156.9455997],
    xmassr = [29156.9455997,29156.9455997,29156.9455997],
    emax1 = 9000.,
    emax2 = 9000.,
    re1 = 2.87,
    diss1 = 0.06,
    we1 = 0.004,
    re2 = None,
    diss2 = None,
    we2 = None,
    ezero = 0.0
)

def open_dir(dirname):
    # create sub folder recursively
    if dirname!='./':
        if not os.path.isdir(dirname):
            os.makedirs(dirname)

class JobManager:
    """
    Base class for job manager.
    """
    def get_job(self,commands):
        raise NotImplementedError

    def submit_job(self,dirname):
        raise NotImplementedError
    
    def save_job(self,commands=[],dirname='./'):
        open_dir(dirname)
        with open(os.path.join(dirname,self.job_file),'w') as f:
            f.write(self.get_job())
            
    def __repr__(self):
        return self.get_job()        

class Slurm(JobManager):
    """
    Starts the commands one after another
    inside the slurm batch file.    
    """    
    def __init__(self,title,job_file='job.sh'):
        self.title = title
        
        # Job parameters.
        self.nnodes = 1
        self.ncores = 8 
        self.memory = 8000 # total memory, MB
        self.walltime = 24 # hours
    
        # List of commands to run in batch mode.
        self.commands = None
    
        # Name of the job file.
        self.job_file = job_file
        
        # Name of the partition
        self.partition = 'short'

    def get_job(self,commands=[]):
        body = ''.join(
            [\
            '#!/bin/sh\n\n',
            '#SBATCH -J {JOBNAME}\n',
            '#SBATCH -c {NCORES}\n',
            '#SBATCH -N {NNODES}\n',
            '#SBATCH --mem {MEMORY}\n',
            '#SBATCH --time={WALLTIME}:00:00\n',
            '#SBATCH --partition {PARTITION}\n'
            ]
        )\
        .format(JOBNAME=self.title,NCORES=self.ncores,
            NNODES=self.nnodes,WALLTIME=self.walltime,MEMORY=self.memory,
            PARTITION=self.partition)
               
        if self.ncores:
            commands = ['export OMP_NUM_THREADS=%d\n'%self.ncores] \
                + commands
               
        for command in commands:
            body += '\n' + command
            
        return body
                
    #def submit_job(self,dirname):
    def submit_job(self):
        #curdir = os.getcwd()
        #os.chdir(dirname)
        subprocess.run(['sbatch',self.job_file])
        #os.chdir(curdir)

class Shell(Slurm):
    """ Calling jobs through shell scripts (Linux)."""
    
    #def submit_job(self,dirname):
    def submit_job(self):
        #curdir = os.getcwd()
        #os.chdir(dirname)
        subprocess.run(os.path.join('./',self.job_file))
        #os.chdir(curdir)
    
def get_job_manager(jobman,jobscript):
    jobman_ = jobman.lower()
    if jobman_ in ['slurm']:
        return Slurm(title='job',job_file=jobscript)
    elif jobman_ in ['shell']:
        return Shell(title='job',job_file=jobscript)
    else:
        raise Exception('unknown mode "%s"'%jobman)

DVR3DRJZ_DEFAULT = DVR3DRJZ_LITE

def dvr_label(prefix,jrot,kmin,ipar,postfix):
    return '%sjki%02d%d%d%s'%(prefix,jrot,kmin,ipar,postfix)

def make_executable(fullpath):
    # http://stackoverflow.com/questions/12791997/how-do-you-do-a-simple-chmod-x-from-within-python
    st = os.stat(fullpath)
    os.chmod(fullpath,st.st_mode|stat.S_IEXEC)

# type conversions minding the None value
to_type = lambda val,typ: typ(val) if val is not None else None
to_int = lambda val: to_type(val,int)
to_float = lambda val: to_type(val,float)
to_bool = lambda val: to_type(val,bool)

class DVR3DRJZ:
    """
    Class for encapsulating dvr3drjz functional.
    """

    def __init__(self,**argv):   
        # GENERAL PARAMETERS
        
        # path to executable
        self.exefile = argv.get('exefile','./dvr3drjz.x')
            
        # Starter file name
        self.starter_file = argv.get('starter_file','dvr3drjz.sh')

        # parameter file and model
        self.parfile = argv.get('parfile','dv6_sfit_nowall_mod1a.par') # model_mep_1a by default    
        self.model = argv.get('model','model_mep_1a')
    
        # input and output file names
        self.input_file = argv.get('input_file','dvr3drjz.inp')
        self.output_file = argv.get('output_file','dvr3drjz.out')
        
        DEFAULT = DVR3DRJZ_DEFAULT
        
        # CALCULATION PARAMETERS.
        
        # Line 1:
        #self.prt = argv.get('prt',DEFAULT['prt'])
        prt = argv.get('prt')
        self.prt = read_fortran_namelist(prt) if prt else DEFAULT['prt']
    
        # Line 2:
        #self.var = argv.get('var',DEFAULT['var'])
        var = argv.get('var')
        self.var = read_fortran_namelist(var) if var else DEFAULT['var']
    
        # Line 3:
        self.parfile = argv.get('parfile',DEFAULT['parfile'])
    
        # Line 4: (FORMAT: I5).
        self.ncoord = to_int( argv.get('ncoord',DEFAULT['ncoord']) ) # the number of vibrational coordinates of the problem
                                           # = 2 for an atom-rigid diatom system,
                                           # = 3 for a full triatomic.
    
        # Line 5: (FORMAT: 11I5).
        self.npnt2 = to_int( argv.get('npnt2',DEFAULT['npnt2']) ) # number of DVR points in r2 from Gauss-(associated) Laguerre quadrature.
        self.jrot = to_int( argv.get('jrot',DEFAULT['jrot']) ) # total angular momentum quantum number of the system, J.
        self.neval = to_int( argv.get('neval',DEFAULT['neval']) ) # number of eigenvalues and eigenvectors required.
        self.nalf = to_int( argv.get('nalf',DEFAULT['nalf']) ) # number of DVR points in theta from Gauss-(associated) Legendre quadrature.
        self.max2d = to_int( argv.get('max2d',DEFAULT['max2d']) ) # maximum dimension of the largest intermediate 2D Hamiltonian, (ignored if IDIA=?2).
        self.max3d = to_int( argv.get('max3d',DEFAULT['max3d']) ) # maximum dimension of the final Hamiltonian.
                                        # If ZCUT=F, it is the actual number of functions selected.
                                        # If ZCUT=T, MAX3D must be >= than the number of functions selected using EMAX2.
        self.idia = to_int( argv.get('idia',DEFAULT['idia']) )   # =1 for scattering coordinates with a heteronuclear diatomic,
                                        # =2 for scattering coordinates with a homonuclear diatomic, 
                                        # =-1 for Radau coordinates with a heteronuclear diatomic,              
                                        # =-2 for Radau coordinates with a homonuclear diatomic.
        self.kmin = to_int( argv.get('kmin',DEFAULT['kmin']) ) # =k for JROT>0and ZROT=F,
                                   # =(1?p) for JROT>0and ZROT=T. 
                                   # Note:
                                   # For IDIA>0, KMIN must be 1 in DVR3DRJ if KMIN=2 in ROTLEV3. 
                                   # For ZBISC=T, setting KMIN=2 performs p=0 and 1 calculations. 
                                   # For ZPERP=T and ZROT=T, use KMIN=1.
        self.npnt1 = to_int( argv.get('npnt1',DEFAULT['npnt1']) ) # number of DVR points in r2 from Gauss-(associated) Laguerre quadrature, (ignored if IDIA=-2)
        self.ipar = to_int( argv.get('ipar',DEFAULT['ipar']) )  # parity of basis for the AB2 molecule (i.e., |IDIA|= 2) case:
                                    # IPAR=0 for even parity and =1 for odd.
        self.max3d2 = to_int( argv.get('max3d2',DEFAULT['max3d2']) ) # maximum dimension of odd parity final Hamiltonians.
                                            # (IDIA=?2, ZROT=T only).
                                            # =max3d, if None
                  
        # Line 6:
        self.title = argv.get('title',DEFAULT['title']) 

        # Line 7: (FORMAT: F20.0).
        self.fixcos = argv.get('fixcos',DEFAULT['fixcos']) # If ZTWOD=T, FIXCOS is the fixed value of cos? for the run.
                                            # If ZTWOD = F, this line is read but ignored.
                                            # None => nothing is printed
    
        # Line 8: (XMASS(I),I=1,3) (3F20.0)
        # XMASS(I) contains the (vibrational) mass of atom I in atomic mass units.
        self.xmass = argv.get('xmass',DEFAULT['xmass'])
    
        # Line 9: (XMASSR(I),I=1,3) (3F20.0)
        #XMASSR(I) contains the rotationalmass of atom I in atomic mass units. 
        #If XMASSR(1) is not set, XMASSR is set equal to XMASS.
        self.xmassr = argv.get('xmassr',self.xmass)
    
        # Line 10: (FORMAT: 2F20.0)
        self.emax1 = to_float( argv.get('emax1',DEFAULT['emax1']) ) # is the first cut-off energy in cm-1 with the same energy zero as the potential. 
                                        # This determines the truncation of the 1D solutions (IDIA>-2 only).
        self.emax2 = to_float( argv.get('emax2',DEFAULT['emax2']) ) # is the second cut-off energy in cm-1 with the same energy zero as the potential.
                                        # This controls the truncation of the 2D solutions (i.e., the size of the final basis). 
                                        # If ZCUT = Fit is ignored and the size of the final Hamiltonian is MAX3D.
                   
        # Line 11: RE1,DISS1,WE1 (3F20.0)
        # If NCOORD =2, RE1 is the fixed diatomic bondlength, DISS1 and WE1 ignored.
        # If NCOORD = 3, RE1 = r_e, DISS1 = D_e and WE1 =  omega_e are Morse parameters for the r1 coordinate when 
        # ZMORS1=T, and are spherical oscillator parameters when ZMORS1=F.
        self.re1 = to_float( argv.get('re1',DEFAULT['re1']) )
        self.diss1 = to_float( argv.get('diss1',DEFAULT['diss1']) )
        self.we1 = to_float( argv.get('we1',DEFAULT['we1']) )
    
        # Line 12: RE2,DISS2,WE2 (3F20.0)
        # If ZMORS2=T, RE2=r_e, DISS2=D_e, and WE2=omega_e are Morse parameters for the r2 coordinate. 
        # If ZMORS2=F, RE2 is ignored; DISS2=alpha and WE2=omega_e are spherical oscillator parameters for the r2 coordinate.
        # If IDIA =-2 line read but ignored.
        self.re2 = to_float( argv.get('re2',DEFAULT['re2']) )
        self.diss2 = to_float( argv.get('diss2',DEFAULT['diss2']) )
        self.we2 = to_float( argv.get('we2',DEFAULT['we2']) )
    
        #Line 11: (FORMAT: F20.0) 
        self.ezero = to_float( argv.get('ezero',DEFAULT['ezero']) ) # The ground state of the system in cm-1 relative to the energy zero.
                                        # Optional and only read when IDIA=+=2, IPAR=1, and JROT=0
                                        
        ## JOB MANAGER
        #self.job_file = argv.get('job_file','dvr3drjz.slurm')
        #self.job_manager = Slurm(dvr_label('',self.jrot,self.kmin,self.ipar,'d'))        
                
    def get_input(self):
        keys = [self.npnt2,self.jrot,self.neval,
                self.nalf,self.max2d,self.max3d,
                self.idia,self.kmin,self.npnt2,self.ipar]
        if self.max3d2: keys.append(self.max3d2)
        fixcos = '%f'%self.fixcos if self.fixcos else ''
        re2 = self.re2 if self.re2 else self.re1
        diss2 = self.diss2 if self.diss2 else self.diss1
        we2 = self.we2 if self.we2 else self.we1
        return \
        dict_to_namelist('PRT',self.prt) + '\n' + \
        dict_to_namelist('VAR',self.var) + '\n' + \
        (self.parfile if self.parfile else 'dummy') + '\n' + \
        '%5d'%self.ncoord + '\n' + \
        uniform('%5d',keys) + '\n' + \
        self.title + '\n' + \
        fixcos + '\n' + \
        uniform('%20.7f',self.xmass) + '\n' + \
        uniform('%20.7f',self.xmassr) + '\n' + \
        uniform('%20f',[self.emax1,self.emax2]) + '\n' + \
        uniform('%20f',[self.re1,self.diss1,self.we1]) + '\n' + \
        uniform('%20f',[re2,diss2,we2]) + '\n' + \
        '%.11f'%float(self.ezero)
        
    def save_input(self,dirname='./'):
        open_dir(dirname)
        with open(os.path.join(dirname,self.input_file),'w') as f:
            f.write(self.get_input())
   
    def load_input(self,filename,dirname='./'):
        with open(os.path.join(dirname,filename)) as f:
            # read PRT namelist
            line = f.readline().strip()
            self.prt = read_fortran_namelist(line)
            # read VAR namelist
            line = f.readline().strip()
            self.var = read_fortran_namelist(line)
            # read parfile name
            self.parfile = f.readline().strip()
            # read number of coordinates            
            line = f.readline().rstrip()
            if line:
                self.ncoord = int(line)
            else:
                self.ncoord = 3
            # read main control keys        
            line = f.readline().rstrip()
            pieces = slice(line,[5,5,5,5,5,5,5,5,5,5])
            self.npnt2,self.jrot,self.neval, \
            self.nalf,self.max2d,self.max3d, \
            self.idia,self.kmin,self.npnt2, \
            self.ipar = [to_int(piece) for piece in pieces]
            # read title
            self.title = f.readline().rstrip()
            # read fixcos
            line  = f.readline().rstrip()
            if line: self.fixcos = float(line)
            # read vibrational masses
            line = f.readline().rstrip()
            pieces = slice(line,20)
            self.xmass = [float(piece) for piece in pieces]
            # read rotational masses
            line = f.readline().rstrip()
            pieces = slice(line,20)
            self.xmassr = [float(piece) for piece in pieces]
            # read emax1 and emax2
            line = f.readline().rstrip()
            pieces = slice(line,20)
            self.emax1,self.emax2 = [float(piece) for piece in pieces]
            # read re1, diss1, and we1
            line = f.readline().rstrip()
            pieces = slice(line,20)
            self.re1,self.diss1,self.we1 = [float(piece) for piece in pieces]
            # read re2, diss2, and we2
            line = f.readline().rstrip()
            pieces = slice(line,20)
            self.re2,self.diss2,self.we2 = [float(piece) for piece in pieces]
            # read ezero
            line = f.readline().strip()
            if line:
                self.ezero = float(line)
            else:
                self.ezero = 0.0
                
    def get_starter(self):
        text = \
        '#!/bin/sh' + '\n\n' + \
        'echo running dvr3drjz ...\n\n' + \
        self.exefile + ' < ' + \
        self.input_file + ' > ' + \
        self.output_file + '\n\n' + \
        'echo dvr3drjz ok'
        return text
        
    def save_starter(self,dirname='./'):
        open_dir(dirname)
        # save dummy pes.par file
        with open(os.path.join(dirname,'pes.par'),'w') as f:
            f.write(
                '*\n* DUMMY\n*\n           0           0           0  1.00000000000000                 1'
            )
        fullpath = os.path.join(dirname,self.starter_file)
        with open(fullpath,'w') as f:
            f.write(self.get_starter())
        make_executable(fullpath)
            
    #def get_job(self):
    #    commands = []
    #    commands.append('rm -f %s'%LABEL_DONE)
    #    commands.append('touch %s'%LABEL_RUNNING)
    #    commands.append('time ./'+self.starter_file)
    #    commands.append('rm -f %s'%LEVEL_RUNNING)
    #    commands.append('touch %s'%LABEL_DONE)
    #    return self.job_manager.get_job(commands)
        
    def save_job(self,dirname='./'):
        open_dir(dirname)
        fullpath = os.path.join(dirname,self.job_file)
        with open(fullpath,'w') as f:
            f.write(self.get_job())  
        make_executable(fullpath)      

    def save(self,dirname='./'):
        open_dir(dirname)
        self.save_input(dirname)
        self.save_starter(dirname)
        self.save_job(dirname)
        
    def __repr__(self):
        return \
        '///////////////////// INPUT FILE: %s /////////////////////\n'%self.input_file + \
        self.get_input() + '\n\n' + \
        '///////////////////// STARTER SCRIPT: %s /////////////////\n'%self.starter_file + \
        self.get_starter() + '\n\n' + \
        '///////////////////// JOB SCRIPT: %s /////////////////////\n'%self.job_file + \
        self.get_job()
            
# ROTLEV3B INPUT FILE EXAMPLE
"""
 &PRT zdcore=.true., ztran=.true., meout=.false. &END
 9999 9999    2
OZONE: USING RADAU COORDINATES
1443.58613558344
""";
                                
class ROTLEV3B:
    """
    Class for encapsulating rotlev (base).
    """
    
    def __init__(self,DVR3DRJZ_INSTANCE,**argv):
        # GENERAL PARAMETERS
        
        self.stem = self.__class__.__name__.lower()
        
        # path to executable
        self.exefile = argv.get('exefile','./rotlev3b.x')

        # Starter script name
        self.starter_file = argv.get('starter_file',self.stem+'.sh')
    
        # input and output file names
        self.input_file = argv.get('input_file',self.stem+'.inp')
        self.output_file = argv.get('output_file',self.stem+'.out')
    
        # CALCULATION PARAMETERS
    
        # Line 1:
        #self.prt = argv.get('prt',{'zdcore':True, 'ztran':True, 'meout':False})
        prt = argv.get('prt')
        self.prt = read_fortran_namelist(prt) if prt else\
            {'zdcore':True, 'ztran':True, 'meout':False}    
    
        # Line 2: (FORMAT: I5)
        self.nvib = argv.get('nvib',9999) # number of vibrational levels from DVR3DRJZ for each k to be read, 
                # and perhaps selected from, in the second variational step.
        self.neval = argv.get('neval',9999) # the number of eigenvalues required for the first set.
        self.kmin = argv.get('kmin',2) # =0, f or p=1 parity calculation. 
             # =1, e or p =0 parity calculation. 
             # =2, do both e and f parity calculation.
        self.ibass = argv.get('ibass',None) # =0 or >NVIB*(JROT+KMIN), use all the vibrational levels. 
                 # Otherwise, select IBASS levels with the lowest energy.
                 # None => 0 (internal ROTLEV default)
        self.neval2 = argv.get('neval2',None) # The number of eigenvalues required for the second set.
                  # None => neval (internal ROTLEV default)
        self.npnt = argv.get('npnt',None) # Number of quadrature points for angular integrals.
                # None => nalf (internal ROTLEV default)
                
        # Line 3: 
        self.title = argv.get('title','ROTLEV POSITIONS CALC')
        if DVR3DRJZ_INSTANCE:
            self.jrot = DVR3DRJZ_INSTANCE.jrot
            self.kmin = DVR3DRJZ_INSTANCE.kmin
            self.ipar = DVR3DRJZ_INSTANCE.ipar
            self.ezero = DVR3DRJZ_INSTANCE.ezero
            
        ## JOB MANAGER
        #self.job_file = argv.get('job_file','rotlev3b.slurm')
        #self.job_manager = Slurm(dvr_label('',self.jrot,self.kmin,self.ipar,'r'))        
    
    def get_input(self):
        keys = [self.nvib,self.neval,self.kmin]
        if self.ibass: keys.append(self.ibass)
        if self.neval2: keys.append(self.neval2)
        if self.npnt: keys.append(self.npnt)
        return \
        dict_to_namelist('PRT',self.prt) + '\n' + \
        uniform('%5d',keys) + '\n' + \
        self.title + '\n' + \
        '%.11f'%float(self.ezero)
            
    def save_input(self,dirname='./'):
        open_dir(dirname)
        with open(os.path.join(dirname,self.input_file),'w') as f:
            f.write(self.get_input())
   
    def load_input(self,filename,dirname='./'):
        with open(os.path.join(dirname,filename)) as f:
            # read PRT namelist
            line = f.readline().strip()
            self.prt = read_fortran_namelist(line)
            # read main control keys        
            line = f.readline().rstrip()
            pieces = slice(line,[5,5,5,5,5,5])
            self.nvib,self.neval,self.kmin, \
            self.ibass,self.neval2, \
            self.npnt = [to_int(piece) for piece in pieces]
            # read title
            self.title = f.readline().rstrip()
            # read ezero
            line = f.readline().strip()
            if line:
                self.ezero = float(line)
            else:
                self.ezero = 0.0     
                
    def get_starter(self):
        # "ln -s fort.26 fort.4" is more space-efficient than "cp fort.26 fort.4"
        text = \
        '#!/bin/sh' + '\n\n' + \
        'echo running %s ...\n\n'%self.stem + \
        'ln -s fort.26 fort.4' + '\n\n' + \
        self.exefile + ' < ' + \
        self.input_file + ' > ' + \
        self.output_file + '\n\n' + \
        'echo %s ok'%self.stem
        return text
        
    def save_starter(self,dirname='./'):
        open_dir(dirname)
        fullpath = os.path.join(dirname,self.starter_file)
        with open(fullpath,'w') as f:
            f.write(self.get_starter())
        make_executable(fullpath)
            
    #def get_job(self):
    #    commands = []
    #    commands.append('rm -f %s'%LABEL_DONE)
    #    commands.append('touch %s'%LABEL_RUNNING)
    #    commands.append('time ./'+self.starter_file)
    #    commands.append('rm -f %s'%LABEL_RUNNING)
    #    commands.append('touch %s'%LABEL_DONE)
    #    return self.job_manager.get_job(commands)
        
    def save_job(self,dirname='./'):
        open_dir(dirname)
        fullpath = os.path.join(dirname,self.job_file)
        with open(fullpath,'w') as f:
            f.write(self.get_job())  
        make_executable(fullpath)
        
    def save(self,dirname='./'):
        open_dir(dirname)
        self.save_input(dirname)
        self.save_starter(dirname)
        self.save_job(dirname)

    def __repr__(self):
        return \
        '///////////////////// INPUT FILE: %s /////////////////////\n'%self.input_file + \
        self.get_input() + '\n\n' + \
        '///////////////////// STARTER SCRIPT: %s /////////////////\n'%self.starter_file + \
        self.get_starter() + '\n\n' + \
        '///////////////////// JOB SCRIPT: %s /////////////////////\n'%self.job_file + \
        self.get_job()

class ROTLEV3(ROTLEV3B):
    """
    Class for encapsulating rotlev3.
    """
    pass

class ROTLEV3Z(ROTLEV3B):
    """
    Class for encapsulating rotlev3z.
    """
    pass

class ROVIB_STATE():
    """
    Class for the full ro-vibrational energy calculation.
    """
    
    def __init__(self,**argv):
        # GENERAL PARAMETERS

        # create/assign dvr3drjz
        self.dvr3drjz = argv.get('dvr3drjz',None)
        if self.dvr3drjz: 
            if self.dvr3drjz.__class__ != DVR3DRJZ:
                raise Exception('wrong class for dvr3drjz')
        else:
            self.dvr3drjz = DVR3DRJZ(**argv)
            
        # create/assign rotlev
        if self.dvr3drjz.jrot>0:
            self.rotlev = argv.get('rotlev',None)
            if not self.rotlev: 
                self.rotlev = ROTLEV3B(self.dvr3drjz)
            
        # JOB MANAGER
        self.job_file = argv.get('job_script','job.sh')
        self.job_manager = Slurm(dvr_label('',
            self.dvr3drjz.jrot,
            self.dvr3drjz.kmin,
            self.dvr3drjz.ipar,'f'))

    #def positions_subdir_name(OPTIONS):
    #    jrot = self.dvr3drjz.jrot
    #    kmin = self.dvr3drjz.kmin
    #    ipar = self.dvr3drjz.ipar
    #    return 'J=%d_kmin=%d_ipar=%d'%[jrot,kmin,ipar]
                   
    def get_job(self):        
        commands = []
        commands.append('rm -f %s'%LABEL_DONE)
        commands.append('touch %s'%LABEL_RUNNING)
        commands.append('time ./' + self.dvr3drjz.starter_file)
        if self.dvr3drjz.jrot>0:
            commands.append('time ./' + self.rotlev.starter_file)
        commands.append('rm -f %s'%LABEL_RUNNING)
        commands.append('touch %s'%LABEL_DONE)
        return self.job_manager.get_job(commands)
        
    def save_job(self,dirname='./'):
        open_dir(dirname)
        fullpath = os.path.join(dirname,self.job_file)
        with open(fullpath,'w') as f:
            f.write(self.get_job()) 
        make_executable(fullpath)            
               
    def save(self,dirname='./'):
        open_dir(dirname)
        commands = []
        # place all input and starter files to the sub-directory
        self.dvr3drjz.save_input(dirname)
        self.dvr3drjz.save_starter(dirname)
        if self.dvr3drjz.jrot>0:
            self.rotlev.save_input(dirname)
            self.rotlev.save_starter(dirname)
        self.save_job(dirname)
                
    def __repr__(self):
        # return info on starters and input files
        body = '/////////////////////////////////////////////////////////////////////\n' + \
               '///////////////// RO-VIBRATIONAL STATE:   ///////////////////////////\n' + \
               '////////////////  jrot=%d, kmin=%d, ipar=%d ////////////////////////////\n' % \
               (self.dvr3drjz.jrot,self.dvr3drjz.kmin,self.dvr3drjz.ipar) + \
               '/////////////////////////////////////////////////////////////////////\n' + \
               '\n' + \
               '///////////////// DVR3DRJZ INPUT FILE: %s ////////////////\n'%self.dvr3drjz.input_file + \
               self.dvr3drjz.get_input() + \
               '\n\n' + \
               '///////////////// DVR3DRJZ STARTER SCRIPT: %s /////////////\n'%self.dvr3drjz.starter_file + \
               self.dvr3drjz.get_starter() + \
               '\n\n'
        
        if self.dvr3drjz.jrot>0: # NEEDS VERIFICATION!!!
            body += \
               '///////////////// %s INPUT FILE: %s ////////////////\n'%\
                                        (self.rotlev.__class__.__name__,self.rotlev.input_file) + \
               self.rotlev.get_input() + \
               '\n\n' + \
               '///////////////// %s STARTER SCRIPT: %s ////////////\n'%\
                                        (self.rotlev.__class__.__name__,self.rotlev.input_file) + \
               self.rotlev.get_starter() + '\n\n'
               
        body += '///////////////////// JOB SCRIPT: %s ////////////////////////\n'%self.job_file + \
                self.get_job()
               
        return body

def get_dvr_masses(VARSPACE):
    """ 
    Calculate the masses of isotopes based on config data:
        [mass_center, mass_left, mass_right]
    If atomic_masses==True, include electrons.
    """
    
    def getmass(isotope,atomic_masses):
        
        # The atomic weights data: R. D. Vocke, Jr.1 in Atomic Weights of the Elements 1997
        MASSES = {

            # Hydrogen
            'H': {'atomic_number':1,'atomic_mass':1837.1526406},
            'D': {'atomic_number':1,'atomic_mass':3671.4829282},
            'T': {'atomic_number':1,'atomic_mass':5497.9214642},
            
            # Oxygen
            '16O': {'atomic_number':8,'atomic_mass':29156.9455997},
            '17O': {'atomic_number':8,'atomic_mass':30987.520976},
            '18O': {'atomic_number':8,'atomic_mass':32810.46214},
            
            # Sulfide
            '32S': {'atomic_number':16,'atomic_mass':58281.51933},
            '33S': {'atomic_number':16,'atomic_mass':60103.29186},
            '34S': {'atomic_number':16,'atomic_mass':61919.63312},
            '36S': {'atomic_number':16,'atomic_mass':65563.97739},
        }
        
        mass = MASSES[isotope]['atomic_mass']
        
        if not atomic_masses: # subtract number of electrons to retrieve nuclear mass
            mass -=  MASSES[isotope]['atomic_number']
            
        return mass
    
    DVR3DRJZ_INPUT = VARSPACE['DVR3DRJZ_INPUT']
    MOLECULE = VARSPACE['MOLECULE']
    
    # Get parameters from config.
    atomic_masses = to_bool( DVR3DRJZ_INPUT['atomic_masses'] )
    isotope_center = MOLECULE['isotope_center']
    isotope_left = MOLECULE['isotope_left']
    isotope_right = MOLECULE['isotope_right']

    # Get masses of isotopes.
    mass_center = to_float( MOLECULE['isotope_center_mass'] )
    if not mass_center: 
        mass_center = getmass(isotope_center,atomic_masses)
    
    mass_left = to_float( MOLECULE['isotope_left_mass'] )
    if not mass_left:
        mass_left = getmass(isotope_left,atomic_masses)
    
    mass_right = to_float( MOLECULE['isotope_right_mass'] )
    if not mass_right:
        mass_right = getmass(isotope_right,atomic_masses)
    
    return [mass_left, mass_right, mass_center]

def get_rovib_state(VARSPACE):
    """ Create ROVIB_STATE object based on info from VARSPACE """
    
    # Local file with model parameters.
    params = VARSPACE['PES_SOURCE']['pes_parameters_path']
    if params:
        params = os.path.basename(params)
        
    # Model name (deprecated).
    #model_name = VARSPACE['INIT']['model']
    model_name = 'dummy'
    
    # Executable file for DVR3DRJZ
    dvr3drjz_exe = VARSPACE['RESOURCES']['dvr3drjz_executable']
    
    # Molecular parameters.
    ezero = to_float( VARSPACE['MOLECULE']['ezero'] )
    ediss = to_float( VARSPACE['MOLECULE']['ediss'] )
    ediss_offset = to_float( VARSPACE['MOLECULE']['ediss_offset'] )
    
    
    # Set up job details.
    ncores = to_int( VARSPACE['CALCULATE']['ncores'] )
    nnodes = to_int( VARSPACE['CALCULATE']['nnodes'] )
    memory = VARSPACE['CALCULATE']['memory']
    walltime = VARSPACE['CALCULATE']['walltime']
        
    # Deduce the value of IDIA parameter of the DVR3DRJZ object
    masses = get_dvr_masses(VARSPACE)
    coords = VARSPACE['DVR3DRJZ_INPUT']['coordinates']
    if coords.lower() in ['radau']:
        if masses[1]==masses[2]:
            idia = -2 # "Radau homonuclear"
        else:
            idia = -1 # "Radau heteronuclear"
    elif coords.lower() in ['scattering', 'jacobi']:
        if masses[1]==masses[2]:
            idia = 2 # "Scattering homonuclear"
        else:
            idia = 1 # "Scattering heteronuclear"
    else:
        raise Exception('invalid coordinates: "%s"'%coords)
    
    # Create dvr3drjz object.
    dvr3drjz = DVR3DRJZ(

        model   = model_name,
        parfile = os.path.join('../',params),
        exefile = os.path.join('../',dvr3drjz_exe),
        ezero   = ezero,

        xmass = masses,
        idia   = idia,

        prt    = VARSPACE['DVR3DRJZ_INPUT']['prt'],
        var    = VARSPACE['DVR3DRJZ_INPUT']['var'],
        ncoord = VARSPACE['DVR3DRJZ_INPUT']['ncoord'],
        npnt2  = VARSPACE['DVR3DRJZ_INPUT']['npnt2'],
        neval  = VARSPACE['DVR3DRJZ_INPUT']['neval'],
        nalf   = VARSPACE['DVR3DRJZ_INPUT']['nalf'],
        max2d  = VARSPACE['DVR3DRJZ_INPUT']['max2d'],
        max3d  = VARSPACE['DVR3DRJZ_INPUT']['max3d'],
        npnt1  = VARSPACE['DVR3DRJZ_INPUT']['npnt1'],
        re1    = VARSPACE['DVR3DRJZ_INPUT']['re1'],
        diss1  = VARSPACE['DVR3DRJZ_INPUT']['diss1'],
        we1    = VARSPACE['DVR3DRJZ_INPUT']['we1'],
        re2    = VARSPACE['DVR3DRJZ_INPUT']['re2'],
        diss2  = VARSPACE['DVR3DRJZ_INPUT']['diss2'],
        we2    = VARSPACE['DVR3DRJZ_INPUT']['we2'],
        
        emax1 = ediss + ediss_offset,
        emax2 = ediss + ediss_offset,

        input_file = VARSPACE['RESOURCES']['dvr3drjz_input_template']
    )
    
    # Create rotlev object.
    
    if idia==-2:
        rotlev = ROTLEV3B(dvr3drjz)
        rotlev_exe = VARSPACE['RESOURCES']['rotlev3b_executable']
        rotlev_input = VARSPACE['RESOURCES']['rotlev3b_input_template']
    elif idia==-1:
        rotlev = ROTLEV3(dvr3drjz)
        rotlev_exe = VARSPACE['RESOURCES']['rotlev3_executable']
        rotlev_input = VARSPACE['RESOURCES']['rotlev3_input_template']
    else:
        raise NotImplementedError
    
    rotlev.exefile = os.path.join('../',rotlev_exe)
    rotlev.input_file = rotlev_input

    # create rovib_state object
    rovib_state = ROVIB_STATE(dvr3drjz=dvr3drjz,rotlev=rotlev)
    rovib_state.rotlev = rotlev
    rovib_state.job_manager = get_job_manager(
        jobman=VARSPACE['CREATE']['job_manager'],
        jobscript=VARSPACE['CREATE']['job_script'])
    rovib_state.job_manager.ncores = ncores
    rovib_state.job_manager.nnodes = nnodes
    rovib_state.job_manager.memory = memory
    rovib_state.job_manager.walltime = walltime  
    
    return rovib_state
    
def startproject(VARSPACE):
    project_dir = VARSPACE['GENERAL']['project']
    if os.path.isdir(project_dir):
        print('Error: "%s" directory already exists'%project_dir)
        sys.exit()
    os.mkdir(project_dir)
    config_name = 'config.ini'
    config_path = os.path.join(project_dir,config_name)
    VARSPACE.save(config_path)
    print('Created new project: %s'%project_dir)
    print('New config file has been added: %s'%config_path)

def generate_input_templates(rovib_state,VARSPACE):
    # generate template for dvr3drjz
    rovib_state.dvr3drjz.save_input()
    # generate template for rotlev
    rovib_state.rotlev.save_input()

join_sources = lambda srcfiles: \
        '\n'.join([' %s \\'%fname for fname in srcfiles])

dvr3drjz_build_template = \
"""#!/bin/sh
{compiler} -o {exefile} \\
 {comp_flags} \\
{source_files}
{link_line_mkl}
"""
        
def generate_build_script_dvr3drjz(rovib_state,VARSPACE):
    """ Create and save build shell script for DVR3DRJZ """
    
    BUILD = VARSPACE['BUILD']
    RESOURCES = VARSPACE['RESOURCES']
    DVR3DRJZ_SOURCE = VARSPACE['DVR3DRJZ_SOURCE']
    PES_SOURCE = VARSPACE['PES_SOURCE']
    
    pes_source_root = PES_SOURCE['pes_source_root']
    pes_sources_common = PES_SOURCE['pes_sources_common']
    pes_sources_model = PES_SOURCE['pes_sources_model']
    dvr3drjz_source_root = DVR3DRJZ_SOURCE['dvr3drjz_source_root']
    dvr3drjz_sources = DVR3DRJZ_SOURCE['dvr3drjz_sources']
    
    build_file_content = dvr3drjz_build_template.format(
        compiler = BUILD['compiler'],
        exefile = RESOURCES['dvr3drjz_executable'],
        comp_flags = BUILD['compiler_options'],
        source_files = join_sources(
            [os.path.join(pes_source_root,p.strip()) for p in pes_sources_common.split(';')]+
            [os.path.join(pes_source_root,pes_sources_model)]+
            [os.path.join(dvr3drjz_source_root,p.strip()) for p in dvr3drjz_sources.split(';')]
        ),
        link_line_mkl = BUILD['linker_options'],
    )
    
    dvr3drjz_build_script = RESOURCES['dvr3drjz_build_script']
    with open(dvr3drjz_build_script,'w') as f:
        f.write(build_file_content)
     
    make_executable(dvr3drjz_build_script)
    
    return dvr3drjz_build_script

rotlev_build_template = \
"""#!/bin/sh
{compiler} -o {exefile} \\
 {comp_flags} \\
{source_files}
{link_line_mkl}
"""

def generate_build_script_rotlev(rovib_state,VARSPACE):  
    """ Create and save build shell script for ROTLEV """
    
    BUILD = VARSPACE['BUILD']
    RESOURCES = VARSPACE['RESOURCES']
    ROTLEV_SOURCE = VARSPACE['ROTLEV_SOURCE']

    rotlev_name = rovib_state.rotlev.__class__.__name__.lower()
    rotlev_source_root = ROTLEV_SOURCE['rotlev_source_root']
    rotlev_sources = ROTLEV_SOURCE['%s_sources'%rotlev_name]
    
    build_file_content = rotlev_build_template.format(
        compiler = BUILD['compiler'],
        exefile = RESOURCES['%s_executable'%rotlev_name],
        comp_flags = BUILD['compiler_options'],
        source_files = join_sources(
            [os.path.join(rotlev_source_root,p.strip()) for p in rotlev_sources.split(';')]
        ),
        link_line_mkl = BUILD['linker_options'],
    )
    
    rotlev_build_script = RESOURCES['%s_build_script'%rotlev_name]
    with open(rotlev_build_script,'w') as f:
        f.write(build_file_content)

    make_executable(rotlev_build_script)

    return rotlev_build_script

def init(VARSPACE):
    """ Perform initialization """
    
    rovib_state = get_rovib_state(VARSPACE)

    # Generate input templates.
    generate_input_templates(rovib_state,VARSPACE)
    
    # Generate build scripts
    dvr3drjz_build_script = generate_build_script_dvr3drjz(rovib_state,VARSPACE)
    rotlev_build_script = generate_build_script_rotlev(rovib_state,VARSPACE)
                
    # Launch build scripts.
    subprocess.run(os.path.join('./',dvr3drjz_build_script))
    subprocess.run(os.path.join('./',rotlev_build_script))
    
    # Copy model parameter file.
    pes_source_root = VARSPACE['PES_SOURCE']['pes_source_root']
    pes_parameters_path = VARSPACE['PES_SOURCE']['pes_parameters_path']    
    if pes_parameters_path:
        pes_parameters_path = os.path.join(pes_source_root,pes_parameters_path)
        pes_destination_file = os.path.basename(pes_parameters_path)
        shutil.copy(pes_parameters_path,pes_destination_file)

def init_BACKUP(VARSPACE):
    root = VARSPACE['INIT']['root']
    model_name = VARSPACE['INIT']['model']
    dvr3drjz_exe = VARSPACE['INIT']['dvr3drjz']
    if not os.path.isfile(dvr3drjz_exe):
        try:
            dvr3drjz_exe_path = os.path.join(root,'exe',model_name,dvr3drjz_exe)
            shutil.copy(dvr3drjz_exe_path,dvr3drjz_exe)
            print('INIT: %s executable is copied successfully. DOUBLE CHECK THE MODEL!!!'%dvr3drjz_exe_path)
        except:
            print('ERROR: cannot find %s executable. Copy it manually to the current directory.'%dvr3drjz_exe_path)
            sys.exit(1)
    else:
        print('INIT: file "%s" already exists (skipped copying).'%dvr3drjz_exe)
    rotlev3b_exe = VARSPACE['INIT']['rotlev3b']
    if not os.path.isfile(rotlev3b_exe):
        try:
            rotlev3b_exe_path = os.path.join(root,'exe','common',rotlev3b_exe)
            shutil.copy(rotlev3b_exe_path,rotlev3b_exe)
            print('INIT: %s executable is copied successfully.'%rotlev3b_exe_path)
        except:
            print('ERROR: cannot find %s executable. Copy it manually to the current directory.'%rotlev3b_exe_path)
            sys.exit(1)
    else:
        print('INIT: file "%s" already exists (skipped copying).'%rotlev3b_exe)
    hosetaylor_exe = VARSPACE['INIT']['hosetaylor']
    if not os.path.isfile(hosetaylor_exe):
        try:
            hosetaylor_exe_path = os.path.join(root,'exe','common',hosetaylor_exe)
            shutil.copy(hosetaylor_exe_path,hosetaylor_exe)
            print('INIT: %s executable is copied successfully.'%hosetaylor_exe_path)
        except:
            print('ERROR: cannot find %s executable. Copy it manually to the current directory.'%hosetaylor_exe_path)
            sys.exit(1)
    else:
        print('INIT: file "%s" already exists (skipped copying).'%hosetaylor_exe)
    dvr3drjz_template = VARSPACE['INIT']['dvr3drjz_template']
    dvr3drjz = DVR3DRJZ(input_file=dvr3drjz_template,parfile='TEMPLATE')
    if not os.path.isfile(dvr3drjz.input_file):
        print('INIT: saving sample input file for the first step (DVR3DRJZ)')
        dvr3drjz.save_input()
    else:
        print('INIT: file "%s" already exists (skipped copying).'%dvr3drjz.input_file)
    rotlev3b_template = VARSPACE['INIT']['rotlev3b_template']
    rotlev3b = ROTLEV3B(dvr3drjz,input_file=rotlev3b_template)
    if not os.path.isfile(rotlev3b.input_file):
        print('INIT: saving sample input file for the second step (ROTLEV3B)')
        rotlev3b.save_input()
    else:
        print('INIT: file "%s" already exists (skipped copying).'%rotlev3b.input_file)
    print('!!!!! Make sure that you have the PES parameter file in the current directory.')
    print('INIT: complete successful.')
    
def extract_enumerated(buf):
    """
    Extract list from compressed integer data of the form 1,2,3-10 etc...
    """
    blocks = buf.split(',')
    result = set()
    for block in blocks:
        lookup = re.search('(\d+)-(\d+)',buf)
        if lookup:
            val_lower = int(lookup.group(1))
            val_upper = int(lookup.group(2))
            vals = range(val_lower,val_upper+1)
        else:
            try:
                val = int(block)
                vals = [val]
            except ValueError:
                print('ERROR: bad format (%s)'%buf)
        result.update(set(vals))
    return sorted(result)
    
def generate(VARSPACE):
    jrot_values = extract_enumerated(VARSPACE['GENERATE']['jrot'])
    kmin_values = extract_enumerated(VARSPACE['GENERATE']['kmin'])
    ipar_values = extract_enumerated(VARSPACE['GENERATE']['ipar'])
    dirname = eval('lambda jrot,kmin,ipar: %s'%VARSPACE['GENERATE']['pattern'])
    outfile = VARSPACE['GENERATE']['output']
    if os.path.isfile(outfile):
        print('ERROR: file "%s" already exists.'%outfile)
        sys.exit(1)
    fmt = '%10s%5s%5s%5s%10s\n'
    count = 0
    with open(outfile,'w')as f:
        f.write(fmt%('name','jrot','kmin','ipar','comment'))
        for jrot in jrot_values:
            for kmin in kmin_values:
                for ipar in ipar_values:
                    count += 1
                    f.write(fmt%(dirname(jrot,kmin,ipar),jrot,kmin,ipar,''))
    print('%d states were generated and saved to %s'%(count,outfile))
                    

def read_states(filename):
    """
    Read state labels of the form:
    name jrot kmin ipar   comment
    jki_000    0    0    0          
    jki_001    0    0    1  
    #jki_010    0    1    0  commented out
    """
    states = []
    with open(filename) as f:
        # skip header
        f.readline();
        for line in f:
            if line.strip()[0]=='#':
                continue
            vals = line.split()
            states.append({
                'name':vals[0],
                'jrot':int(vals[1]),
                'kmin':int(vals[2]),
                'ipar':int(vals[3])
                })
    return states
                    
def create(VARSPACE):
    states = read_states(VARSPACE['CREATE']['states'])
    rovib_state = get_rovib_state(VARSPACE)
    
    summary_file = VARSPACE['CREATE']['summary']
    fout = open(summary_file,'w')
    
    for state in states:        
        # actualize jrot, kmin, and ipar
        dirname = state['name']
        jrot = state['jrot']
        kmin = state['kmin']
        ipar = state['ipar']
        rovib_state.dvr3drjz.jrot = jrot
        rovib_state.dvr3drjz.kmin = kmin
        rovib_state.dvr3drjz.ipar = ipar
        rovib_state.rotlev.kmin = kmin
        rovib_state.job_manager.title = dirname                
        rovib_state.save(dirname)
        # write summary
        fout.write('\n\ndirname=%s'%dirname+'\n')
        fout.write(str(rovib_state)+'\n')
    
    fout.close()
    
    print('%d subfolders were created. Summary is saved to %s'%(len(states),summary_file))

def check_job_status(curdir): # need to have a proper working dir
    flag_done = os.path.isfile(LABEL_DONE)
    flag_running = os.path.isfile(LABEL_RUNNING)
    if flag_done and not flag_running:
        status = 0; message = 'JOB IN %s IS DONE'%curdir
    elif not flag_done and flag_running:
        status = 1; message = 'JOB IN %s STILL RUNNING'%curdir
    elif not flag_done and not flag_running:
        status = 2; message = 'JOB IN %s HAS NOT BEEN LAUNCHED?'%curdir
    else:
        status = 3; message = 'ERROR: JOB IN %s HAS BOTH LABELS (SOMETHING IS WRONG)'%curdir        
    return status, message

def submit(VARSPACE):
    states = read_states(VARSPACE['CREATE']['states'])
    rovib_state = get_rovib_state(VARSPACE)
    
    print('INITIAL DIR: %s'%os.getcwd())
    for state in states:
        curdir = state['name']
        print('\nCD TO %s'%curdir)
        os.chdir(curdir)
        status, message = check_job_status(curdir)
        if status in {1,3}:
            print(message+' ===> SKIPPING SUBMIT')
        else:
            #subprocess.run(['sbatch','job.slurm']) # system-specific
            rovib_state.job_manager.submit_job()
        print('CD TO UPPER LEVEL')
        os.chdir('..')

def check(VARSPACE): # check the status of running jobs
    states = read_states(VARSPACE['CREATE']['states'])
    print('CHECKING THE JOBs STATUS IN %s'%os.getcwd())
    for state in states:
        curdir = state['name']
        print('\nCD TO %s'%curdir)
        os.chdir(curdir)
        status, message = check_job_status(curdir)
        print('Status %d: %s'%(status,message))
        print('CD TO UPPER LEVEL')
        os.chdir('..')

def hosetaylor(VARSPACE): # calculate rot. assignments with Hose-Taylor procedure
    states = read_states(VARSPACE['CREATE']['states'])
    print('CLEANING LARGE FILES IN %s'%os.getcwd())
    hosetaylor_exe = VARSPACE['INIT']['hosetaylor']
    hosetaylor_exe_path = os.path.join('..',hosetaylor_exe)
    
    def run_ht(ZPE,files):
        for file in files:
            subprocess.run([hosetaylor_exe_path,'%.11f'%ZPE,file])
    
    # try to get ZPE from file
    with open('states.ZPE') as f:
        ZPE = float(f.read().strip())
    
    for state in states:
        curdir = state['name']
        print('\nCD TO %s'%curdir)
        os.chdir(curdir)
        j,k,i = state['jrot'],state['kmin'],state['ipar']
        
        if j==0:
            files = ['fort.26']
        elif k==2:
            files = ['fort.8','fort.9']
        elif k in [0,1]:
            files = ['fort.8']
        else:
            raise Exception('unknown j,k,i configuration: %s'%str([j,k,i]))
        
        run_ht(ZPE,files)

        print('Processed: %s'%(', '.join(files)))
        print('CD TO UPPER LEVEL')
        os.chdir('..')
        
def clean(VARSPACE): # check the status of running jobs
    states = read_states(VARSPACE['CREATE']['states'])
    print('CLEANING LARGE FILES IN %s'%os.getcwd())
    for state in states:
        curdir = state['name']
        print('\nCD TO %s'%curdir)
        os.chdir(curdir)
        j,k,i = state['jrot'],state['kmin'],state['ipar']
        files = ['fort.16']
        if (j==1 and (k,i) in {(1,0),(1,1)}) or j>1:
            files.append('fort.26')            
        for file in files:
            file = os.path.join('./',file)
            if os.path.isfile(file):
                os.remove(file)
            else:
                print('skipping',file)
        print('Cleaned: %s'%(', '.join(files)))
        print('CD TO UPPER LEVEL')
        os.chdir('..')
