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

# DIPOLE3B INPUT FILE EXAMPLE
"""
&PRT ZSTART=.TRUE., ZPRINT=.TRUE. &END
dms_surface2_q_rrt_666.par
ATTEMPT OZONE
   10   20   20
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
                raise Exception('Variable "%s" has unexpected type'%buf)
        
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

DIPOLE3B_HEAVY = dict(
    prt = {'zstart':True, 'zprint':True},
    parfile = 'dms_surface2_q_rrt_666.par',
    title = 'DVR DIPOLE CALC',
    npot = 20,
    nv1 = None,
    nv2 = None,
    ibase1 = None,
    ibase2 = None,
    ezero = 0.0
)

DIPOLE3B_LITE = dict(
    prt = {'zstart':True, 'zprint':True},
    parfile = 'dms_surface2_q_rrt_666.par',
    title = 'DVR DIPOLE CALC',
    npot = 10,
    nv1 = 20,
    nv2 = 20,
    ibase1 = None,
    ibase2 = None,
    ezero = 0.0
)

SPECTRA_HEAVY = dict(
    # ???
)

SPECTRA_LITE = dict( # !!! spectra input file format is different from the one in the DVR paper (2003) !!!
    prt = {}, # namelist
    title = 'DVR SPECTRA CALC',
    ge = 1, # nuclear-spin times symmetry-degeneracy factors for AB2 molecule (i.e., |IDIA| = 2) for the even (IPAR = 0)
    go = 3, # nuclear-spin times symmetry-degeneracy factors for homonuclear AB2 molecule (i.e., |IDIA| = 2) for the odd (IPAR = 1)
    temp = 296.0,
    xmin = 1.0e-35, # Intensity cutoff
    wmin = 0.0, # minimum transition frequency required in cm−1
    wmax = 12000.0, # maximum transition frequency required in cm−1
    dwl = 00, # profile half-width [cm-1] used if ZPROF=T
    q = 3483.8, # partition function,
    spe = {}, # namelist
)

def open_dir(dirname):
    # create sub folder recursively
    if dirname!='./':
        if not os.path.isdir(dirname):
            os.makedirs(dirname)

class SLURM():
    """
    Starts the commands one after another
    inside the slurm batch file.    
    """    
   
    def __init__(self,title):
        self.title = title
        
        # Job parameters.
        self.nnodes = 1
        self.ncores = 8 
        self.memory = 8000 # total memory, MB
        self.walltime = 24 # hours
    
        # List of commands to run in batch mode.
        self.commands = None
    
        # Name of the job file.
        self.job_file = 'job.slurm'
        
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
            '#SBATCH --partition {PARTITION}'
            ]
        )\
        .format(JOBNAME=self.title,NCORES=self.ncores,
            NNODES=self.nnodes,WALLTIME=self.walltime,MEMORY=self.memory,
            PARTITION=self.partition)
                   
        for command in commands:
            body += '\n' + command
            
        return body
    
    def save_job(self,commands=[],dirname='./'):
        open_dir(dirname)
        with open(os.path.join(dirname,self.job_file),'w') as f:
            f.write(self.get_job())
            
    def submit_job(self,dirname):
        curdir = os.getcwd()
        os.chdir(dirname)
        subprocess.run(['sbatch',self.job_file])
        os.chdir(curdir)
        
    def __repr__(self):
        return self.get_job()        
            
DIPOLE3B_DEFAULT = DIPOLE3B_LITE
SPECTRA_DEFAULT = SPECTRA_LITE

#def dvr_label(prefix,jrot,kmin,ipar,postfix):
#    return '%sjki%02d%d%d%s'%(prefix,jrot,kmin,ipar,postfix)

def make_executable(fullpath):
    # http://stackoverflow.com/questions/12791997/how-do-you-do-a-simple-chmod-x-from-within-python
    st = os.stat(fullpath)
    os.chmod(fullpath,st.st_mode|stat.S_IEXEC)
    
class DIPOLE3B():
    """
    Class for encapsulating DIPOLE3B functional.
    """

    def __init__(self,path_bra,path_ket,jki_bra,jki_ket,fort_bra,fort_ket,**argv):   
        # GENERAL PARAMETERS
        
        # pathes to bra and ket energies
        self.path_bra = path_bra
        self.path_ket = path_ket
        
        # save Jki for bra and ket states
        self.jki_bra = jki_bra
        self.jki_ket = jki_ket

        # save fort/parity for bra and ket states
        self.fort_bra = fort_bra
        self.fort_ket = fort_ket
        
        # path to executable
        self.exefile = argv.get('exefile','./dipole3b.x')
            
        # Starter file name
        self.starter_file = argv.get('starter_file','dipole3b.sh')

        # parameter file and model
        self.parfile = argv.get('parfile','dms_surface2_q_rrt_666.par.par') # surface2 by default    
        self.model = argv.get('model','surface2')
    
        # input and output file names
        self.input_file = argv.get('input_file','dipole3b.inp')
        self.output_file = argv.get('output_file','dipole3b.out')
        
        DEFAULT = DIPOLE3B_DEFAULT
        
        # CALCULATION PARAMETERS.
        
        # Line 1:
        self.prt = argv.get('prt',DEFAULT['prt'])
        
        # Line 2:
        self.parfile = argv.get('parfile',DEFAULT['parfile'])
        
        # Line 3:
        self.title = argv.get('title',DEFAULT['title']) 
            
        # Line 4: (FORMAT: 11I5).
        self.npot = argv.get('npot',DEFAULT['npot']) # Number of Gauss–Legendre quadrature points.
        self.nv1 = argv.get('nv1',DEFAULT['nv1']) # Number of ket eigenfunctions considered.
        self.nv2 = argv.get('nv2',DEFAULT['nv2']) # Number of bra eigenfunctions considered.
        self.ibase1 = argv.get('ibase1',DEFAULT['ibase1']) # Number of lowest ket eigenfunctions skipped.
        self.ibase2 = argv.get('ibase2',DEFAULT['ibase2']) # Number of lowest bra eigenfunctions skipped.

        # Line 5: (FORMAT: F20.0) 
        self.ezero = argv.get('ezero',DEFAULT['ezero']) # The ground state of the system in cm-1 relative to the energy zero.
                                        # Optional and only read when IDIA=+=2, IPAR=1, and JROT=0
                                        
        # JOB MANAGER
        self.job_name = argv.get('job_name','dipole3b')
        self.job_file = argv.get('job_file','dipole3b.slurm')
        self.job_manager = SLURM( self.job_name )
                
    def get_input(self):
        keys = [self.npot]
        if self.nv1 is not None: keys.append(self.nv1)
        if self.nv2 is not None: keys.append(self.nv2)
        if self.ibase1 is not None: keys.append(self.ibase1)
        if self.ibase2 is not None: keys.append(self.ibase2)
        return \
        dict_to_namelist('PRT',self.prt) + '\n' + \
        self.parfile + '\n' + \
        self.title + '\n' + \
        uniform('%5d',keys) + '\n' + \
        '%.11f'%self.ezero
        
    def save_input(self,dirname='./'):
        open_dir(dirname)
        with open(os.path.join(dirname,self.input_file),'w') as f:
            f.write(self.get_input())
   
    def load_input(self,filename,dirname='./'):
        with open(os.path.join(dirname,filename)) as f:
            # read PRT namelist
            line = f.readline().strip()
            self.prt = read_fortran_namelist(line)
            # read parfile name
            self.parfile = f.readline().strip()
            # read title
            self.title = f.readline().rstrip()
            # read main control keys        
            line = f.readline().rstrip()
            pieces = slice(line,[5,5,5,5,5,5,5,5,5,5])
            self.npot = int(pieces[0])
            self.nv1 = int(pieces[1]) if pieces[1] else None
            self.nv2 = int(pieces[2]) if pieces[2] else None
            self.ibase1 = int(pieces[3]) if pieces[3] else None
            self.ibase2 = int(pieces[4]) if pieces[4] else None
            # read ezero
            line = f.readline().strip()
            if line:
                self.ezero = float(line)
            else:
                self.ezero = 0.0
                
    def get_starter(self):
        text = \
        '#!/bin/sh' + '\n\n' + \
        'echo running dipole3b ...\n\n' + \
        'ln -sf %s/%s fort.11'%(self.path_bra,self.fort_bra) + '\n\n' + \
        'ln -sf %s/%s fort.12'%(self.path_ket,self.fort_ket) + '\n\n' + \
        self.exefile + ' < ' + \
        self.input_file + ' > ' + \
        self.output_file + '\n\n' + \
        'echo dipole3b ok'
        return text
        
    def save_starter(self,dirname='./'):
        open_dir(dirname)
        fullpath = os.path.join(dirname,self.starter_file)
        with open(fullpath,'w') as f:
            f.write(self.get_starter())
        make_executable(fullpath)
            
    def get_job(self):
        commands = []
        commands.append('rm -f %s'%LABEL_DONE)
        commands.append('touch %s'%LABEL_RUNNING)
        commands.append('time ./'+self.starter_file)
        commands.append('rm -f %s'%LEVEL_RUNNING)
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
            
            
# SPECTRA INPUT FILE EXAMPLE (NEW FORMAT)
"""
 &PRT zsort=.true., zout=.false., zpfun=.false., GZ=3481.50, smin=1.0d-40, 
      emin=0.0d0, emax=1.8d4, wsmax=9000.0d0, wsmin=0.0d0 /
Spectra for dipole moment of HCN
     1.0     1.0
 2000.0     1.0d-40       0.0   18000.0    1.0       20285.9
 &SPE  zplot=.true., zlist=.true., zemit=.false., emax1=60000.0d6,
       emax2=60000.0d6, zprof=.true. /
""";
                                
class SPECTRA():
    """
    Class for encapsulating spectra functional.
    """
    
    def __init__(self,**argv):
        # GENERAL PARAMETERS
        
        # path to executable
        self.exefile = argv.get('exefile','./spectra.x')

        # Starter script name
        self.starter_file = argv.get('starter_file','spectra.sh')
    
        # input and output file names
        self.input_file = argv.get('input_file','spectra.inp')
        self.output_file = argv.get('output_file','spectra.out')
    
        # CALCULATION PARAMETERS
        
        DEFAULT = SPECTRA_DEFAULT
            
        # Line 1: 
        self.prt = argv.get('prt',DEFAULT['prt']) # namelist
        
        # Line 2: 
        self.title = argv.get('title',DEFAULT['title'])

        # Line 3:
        self.ge = argv.get('ge',DEFAULT['ge']) # nuclear-spin times symmetry-degeneracy factors for AB2 molecule (i.e., |IDIA| = 2) for the even (IPAR = 0)
        self.go = argv.get('go',DEFAULT['go']) # nuclear-spin times symmetry-degeneracy factors for homonuclear AB2 molecule (i.e., |IDIA| = 2) for the odd (IPAR = 1)

        # Line 4:
        self.temp = argv.get('temp',DEFAULT['temp']) # temperature
        self.xmin = argv.get('xmin',DEFAULT['xmin']) # Intensity cutoff
        self.wmin = argv.get('wmin',DEFAULT['wmin']) # minimum transition frequency required in cm−1
        self.wmax = argv.get('wmax',DEFAULT['wmax']) # maximum transition frequency required in cm−1
        self.dwl = argv.get('dwl',DEFAULT['dwl']) # profile half-width [cm-1] used if ZPROF=T
        self.q = argv.get('q',DEFAULT['q']) # partition function

        # Line 13:
        self.spe = argv.get('spe',DEFAULT['spe']) # namelist
        
        # JOB MANAGER
        self.job_name = argv.get('job_name','spectra')
        self.job_file = argv.get('job_file','job_spectra.slurm')
        self.job_manager = SLURM( self.job_name )
    
    def get_input(self):        
        return \
        dict_to_namelist('PRT',self.prt) + '\n' + \
        self.title + '\n' + \
        '%10.2f%10.2f\n'%(self.ge,self.go) + \
        '%10.3f%10.3E%10.3f%10.3f%10.3f%10.3f\n'%(self.temp,self.xmin,self.wmin,self.wmax,self.dwl,self.q) + \
        dict_to_namelist('SPE',self.spe)
            
    def save_input(self,dirname='./'):
        open_dir(dirname)
        with open(os.path.join(dirname,self.input_file),'w') as f:
            f.write(self.get_input())
   
    def load_input(self,filename,dirname='./'):
        with open(os.path.join(dirname,filename)) as f:
            # Line 1: PRT namelist
            line = f.readline().strip()
            self.prt = read_fortran_namelist(line)  
            # Line 2: title
            self.title = f.readline().rstrip()
            # Line 3: ge, go
            line = f.readline().rstrip()
            self.ge,self.go = [float(_) for _ in line.split()[:2]]
            # Line 3: temp, xmin, wmin, wmax, dwl, q
            line = f.readline().rstrip()
            self.temp,self.xmin,self.wmin,self.wmax,self.dwl,self.q = \
              [float(_) for _ in line.split()[:6]]
            # Line 4: SPE namelist
            line = f.readline().strip()
            self.spe = read_fortran_namelist(line)
                
    def get_starter(self):
        text = \
        '#!/bin/sh' + '\n\n' + \
        'echo running spectra ...\n\n' + \
        self.exefile + ' < ' + \
        self.input_file + ' > ' + \
        self.output_file + '\n\n' + \
        'echo spectra ok'
        return text
        
    def save_starter(self,dirname='./'):
        open_dir(dirname)
        fullpath = os.path.join(dirname,self.starter_file)
        with open(fullpath,'w') as f:
            f.write(self.get_starter())
        make_executable(fullpath)
            
    def get_job(self):
        commands = []
        commands.append('rm -f %s'%LABEL_DONE)
        commands.append('touch %s'%LABEL_RUNNING)
        commands.append('time ./'+self.starter_file)
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
            
       
class DIPSPECTRA():
    """
    Class for the full spectra energy calculation based on bra- and ket- energies.
    """
    
    def __init__(self,**argv):
        # GENERAL PARAMETERS

        # create/assign dipole3b
        self.dipole3b = argv.get('dipole3b',None)
        if self.dipole3b: 
            if self.dipole3b.__class__ != DIPOLE3B:
                raise Exception('wrong class for dipole3b')
        else:
            self.dipole3b = DIPOLE3B(**argv)
            
        # create/assign spectra
        self.spectra = argv.get('spectra',None)
        if self.spectra: 
            if self.spectra.__class__ != SPECTRA:
                raise Exception('wrong class for spectra')
        else:
            self.spectra = SPECTRA(**argv)
            
        # JOB MANAGER
        self.job_name = argv.get('job_name','dipspectra')
        self.job_file = argv.get('job_file','job.slurm')
        self.job_manager = SLURM( self.job_name )
                   
    def get_job(self):        
        commands = []
        commands.append('rm -f %s'%LABEL_DONE)
        commands.append('touch %s'%LABEL_RUNNING)
        commands.append('time ./' + self.dipole3b.starter_file)
        commands.append('time ./' + self.spectra.starter_file)
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
        self.dipole3b.save_input(dirname)
        self.dipole3b.save_starter(dirname)
        self.spectra.save_input(dirname)
        self.spectra.save_starter(dirname)
        self.save_job(dirname)
                
    def __repr__(self):
        # return info on starters and input files
        body = '/////////////////////////////////////////////////////////////////////\n' + \
               '///////////////// RO-VIBRATIONAL TRANS:   ///////////////////////////\n' + \
               '/////////////BRA  jrot=%d, kmin=%d, ipar=%d ////////////////////////////\n' % \
               tuple(self.dipole3b.jki_bra) + \
               '/////////////KET  jrot=%d, kmin=%d, ipar=%d ////////////////////////////\n' % \
               tuple(self.dipole3b.jki_ket) + \
               '/////////////////////////////////////////////////////////////////////\n' + \
               '\n' + \
               '///////////////// DIPOLE3B INPUT FILE: %s ////////////////\n'%self.dipole3b.input_file + \
               self.dipole3b.get_input() + \
               '\n\n' + \
               '///////////////// DIPOLE3B STARTER SCRIPT: %s /////////////\n'%self.dipole3b.starter_file + \
               self.dipole3b.get_starter() + \
               '\n\n'
        
        body += \
               '///////////////// SPECTRA INPUT FILE: %s ////////////////\n'%self.spectra.input_file + \
               self.spectra.get_input() + \
               '\n\n' + \
               '///////////////// SPECTRA STARTER SCRIPT: %s ////////////\n'%self.spectra.input_file + \
               self.spectra.get_starter() + '\n\n'
               
        body += \
               '///////////////////// JOB SCRIPT: %s ////////////////////////\n'%self.job_file + \
               self.get_job()
               
        return body
        
def parse_config(ini):
    config = ConfigParser.ConfigParser(allow_no_value=True)
    config.read(ini)
    sections = config.sections()
    # create raw dictionary
    VARSPACE = {}
    for section in sections:
        VARSPACE[section] = dict(config.items(section))
    return VARSPACE

def init(VARSPACE):
    root = VARSPACE['INIT']['root']
    model_name = VARSPACE['INIT']['model']
    dipole3b_exe = VARSPACE['INIT']['dipole3b']
    root_energies = VARSPACE['INIT']['root_energies']
    states_file = VARSPACE['INIT']['states']
    if not os.path.isfile(states_file):
        try:
            states_file_path = os.path.join(root_energies,states_file)
            shutil.copy(states_file_path,states_file)
            print('INIT: %s states file is copied successfully from %s.'%(states_file,root_energies))
        except:
            print('ERROR: cannot find %s . Copy it manually to the current directory.'%states_file_path)
            sys.exit(1)
    else:
        print('INIT: file "%s" already exists (skipped copying).'%states_file)
    if not os.path.isfile(dipole3b_exe):
        try:
            dipole3b_exe_path = os.path.join(root,'exe',model_name,dipole3b_exe)
            shutil.copy(dipole3b_exe_path,dipole3b_exe)
            print('INIT: %s executable is copied successfully. DOUBLE CHECK THE MODEL!!!'%dipole3b_exe_path)
        except:
            print('ERROR: cannot find %s executable. Copy it manually to the current directory.'%dipole3b_exe_path)
            sys.exit(1)
    else:
        print('INIT: file "%s" already exists (skipped copying).'%dipole3b_exe)
    spectra_exe = VARSPACE['INIT']['spectra']
    if not os.path.isfile(spectra_exe):
        try:
            spectra_exe_path = os.path.join(root,'exe','common',spectra_exe)
            shutil.copy(spectra_exe_path,spectra_exe)
            print('INIT: %s executable is copied successfully.'%spectra_exe_path)
        except:
            print('ERROR: cannot find %s executable. Copy it manually to the current directory.'%spectra_exe_path)
            sys.exit(1)
    else:
        print('INIT: file "%s" already exists (skipped copying).'%spectra_exe)
    dipole3b_template = VARSPACE['INIT']['dipole3b_template']
    dipole3b = DIPOLE3B(None,None,None,None,None,None,input_file=dipole3b_template,parfile='TEMPLATE')
    if not os.path.isfile(dipole3b.input_file):
        print('INIT: saving sample input file for the first step (DIPOLE3B)')
        dipole3b.save_input()
    else:
        print('INIT: file "%s" already exists (skipped copying).'%dipole3b.input_file)
    spectra_template = VARSPACE['INIT']['spectra_template']
    spectra = SPECTRA(input_file=spectra_template)
    if not os.path.isfile(spectra.input_file):
        print('INIT: saving sample input file for the second step (SPECTRA)')
        spectra.save_input()
    else:
        print('INIT: file "%s" already exists (skipped copying).'%spectra.input_file)
    print('!!!!! Make sure that you have the DIPOLE parameter file in the current directory.')
    print('INIT: complete successful.')

def get_case_params(state):
    """
    Get all case parameters (j,k,i,f...) from state.
    """
    name = state['name']
    jrot = state['jrot']
    kmin = state['kmin']
    ipar = state['ipar']    
    
    # get the lost of files containing wave functions
    if jrot==0:
        frts = ['fort.26']
    elif jrot==1 and kmin==0:
        frts = ['fort.26']
    elif jrot==1 and kmin==1:
        frts = ['fort.8']
    elif jrot>1 and kmin in [0,1]:
        frts = ['fort.8']
    elif jrot>=1 and kmin==2:
        frts = ['fort.8','fort.9']
    else:
        raise Exception('unknown combination of jrot and kmin: %d %d'%(jrot,kmin))
        
    return name,jrot,kmin,ipar,frts        

def create_transition_folder_name(name,fort,name_,fort_):
    fort = '%7s'%fort; fort = fort.replace(' ','_')
    fort_ = '%7s'%fort_; fort_ = fort_.replace(' ','_')
    return '%s_%s__%s_%s'%(name,fort,name_,fort_)
    
def generate(VARSPACE): # generate transitions
    states = read_states(VARSPACE['INIT']['states'])
    outfile = VARSPACE['GENERATE']['output']
    project_name = VARSPACE['INIT']['project']
    filter = eval('lambda jrot,kmin,ipar,jrot_,kmin_,ipar_,fort,fort_,name,name_: %s'%\
        VARSPACE['GENERATE']['filter'])
    if os.path.isfile(outfile):
        print('ERROR: file "%s" already exists.'%outfile)
        sys.exit(1)
    J_min = int(VARSPACE['GENERATE']['j_min'])
    J_max = int(VARSPACE['GENERATE']['j_max'])
    J_diff_min = int(VARSPACE['GENERATE']['j_diff_min'])
    J_diff_max = int(VARSPACE['GENERATE']['j_diff_max'])
    fmt_head = '%10s  %34s   %2s %1s %1s   %2s %1s %1s   %7s %7s   %8s  %8s\n'
    fmt = '%10s  %34s   %02d %1d %1d   %02d %1d %1d   %7s %7s   %8s  %8s\n'
    count = 0
    with open(outfile,'w')as f:
        f.write(fmt_head%('id','name','J','k','i','J','k','i','fort','fort','state','state'))
        for state_bra in states:
            name,jrot,kmin,ipar,frts = get_case_params(state_bra)
            for state_ket in states:
                name_,jrot_,kmin_,ipar_,frts_ = get_case_params(state_ket)
                # test for selection rules
                if jrot<J_min: continue
                if jrot>J_max: continue
                if jrot-jrot_<J_diff_min: continue
                if jrot-jrot_>J_diff_max: continue
                for fort in frts:
                    for fort_ in frts_:
                        pars = (jrot,kmin,ipar,jrot_,kmin_,ipar_,fort,fort_,name,name_)
                        if not filter(*pars): continue
                        # all selection rules are passed - save case
                        count += 1
                        id = '%s%s'%(project_name,count)
                        #tname = '%s_%s__%s_%s'%(name,fort,name_,fort_)
                        tname = create_transition_folder_name(name,fort,name_,fort_)
                        f.write(fmt%(id,tname,*pars))
    print('%d transitions were generated and saved to %s'%(count,outfile))
                    
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
            if not line.strip(): continue
            if line.strip()[0]=='#': continue
            vals = line.split()
            states.append({
                'name':vals[0],
                'jrot':int(vals[1]),
                'kmin':int(vals[2]),
                'ipar':int(vals[3])
                })
    return states

def read_transitions(filename):
    """
    Read transition labels of the form:
#       id                                name    J k i    J k i      fort    fort      state     state                              
      spe1  jki_0020_fort.26__jki_0020_fort.26   00 2 0   00 2 0   fort.26 fort.26   jki_0020  jki_0020
      spe2  jki_0020_fort.26__jki_0021_fort.26   00 2 0   00 2 1   fort.26 fort.26   jki_0020  jki_0021
    """
    transitions = []
    with open(filename) as f:
        # skip header
        f.readline();
        for line in f:
            if not line.strip(): continue
            if line.strip()[0]=='#': continue
            vals = line.split()
            transitions.append({
                'id':vals[0],
                'name':vals[1],
                'jrot':int(vals[2]),
                'kmin':int(vals[3]),
                'ipar':int(vals[4]),
                'jrot_':int(vals[5]),
                'kmin_':int(vals[6]),
                'ipar_':int(vals[7]),
                'fort':vals[8],
                'fort_':vals[9],
                'state':vals[10],
                'state_':vals[11],
                })
    return transitions
    
def create(VARSPACE):
    # read states and derived transitions
    states = read_states(VARSPACE['INIT']['states'])
    transitions = read_transitions(VARSPACE['CREATE']['transitions'])
    root_energies = VARSPACE['INIT']['root_energies']
    # setup templates for dipole3b and spectra files
    params = VARSPACE['INIT']['parfile']
    model_name = VARSPACE['INIT']['model']
    dipole3b_exe = VARSPACE['INIT']['dipole3b']
    spectra_exe = VARSPACE['INIT']['spectra']
    ezero = VARSPACE['INIT']['ezero']; ezero = float(ezero)
    partfun = VARSPACE['INIT']['partfun']; partfun = float(partfun)
    dipole3b = DIPOLE3B(None,None,None,None,None,None,model=model_name)
    dipole3b.load_input(VARSPACE['INIT']['dipole3b_template'])
    dipole3b.parfile = os.path.join('../',params)
    dipole3b.exefile = os.path.join('../',dipole3b_exe)
    dipole3b.ezero = ezero
    spectra = SPECTRA() 
    spectra.load_input(VARSPACE['INIT']['spectra_template'])
    spectra.exefile = os.path.join('../',spectra_exe)
    spectra.q = partfun
    spectra.prt['gz'] = ezero # !!! required by new version of spectra
    summary_file = VARSPACE['CREATE']['summary']
    fout = open(summary_file,'w')
    # job details
    ncores = VARSPACE['CALCULATE']['ncores']
    nnodes = VARSPACE['CALCULATE']['nnodes']
    memory = VARSPACE['CALCULATE']['memory']
    walltime = VARSPACE['CALCULATE']['walltime']
    for trans in transitions: 
        print('Creating inputs for ',trans['name']) # for slow-reacting systems
        # actualize parameters
        dirname = trans['name']
        #state_bra,state_ket = dirname.split('__')
        state_bra = trans['state']
        state_ket = trans['state_']
        jki_bra = [trans['jrot'],trans['kmin'],trans['ipar']]
        jki_ket = [trans['jrot_'],trans['kmin_'],trans['ipar_']]
        fort_bra = trans['fort']
        fort_ket = trans['fort_']
        dipole3b.path_bra = os.path.join(root_energies,state_bra)
        dipole3b.path_ket = os.path.join(root_energies,state_ket)
        dipole3b.jki_bra = jki_bra
        dipole3b.jki_ket = jki_ket
        dipole3b.fort_bra = fort_bra
        dipole3b.fort_ket = fort_ket
        # create job files for dipole+spectra
        dipspect = DIPSPECTRA(dipole3b=dipole3b,spectra=spectra)
        dipspect.job_manager.ncores = ncores
        dipspect.job_manager.nnodes = nnodes
        dipspect.job_manager.memory = memory
        dipspect.job_manager.walltime = walltime  
        dipspect.job_manager.title = trans['id']
        dipspect.save(dirname)
        # create job files for spectra only
        spectra.job_manager = dipspect.job_manager
        spectra.save(dirname)
        # write summary
        fout.write('\n\ndirname=%s'%dirname+'\n')
        fout.write(str(trans)+'\n')
    print('%d subfolders were created. Summary is saved to %s'%(len(transitions),summary_file))

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
    transitions = read_transitions(VARSPACE['CREATE']['transitions'])
    print('INITIAL DIR: %s'%os.getcwd())
    for trans in transitions:
        curdir = trans['name']
        print('\nCD TO %s'%curdir)
        os.chdir(curdir)
        status, message = check_job_status(curdir)
        if status in {1,3}:
            print(message+' ===> SKIPPING SUBMIT')
        else:
            subprocess.run(['sbatch','job.slurm']) # system-specific
        print('CD TO UPPER LEVEL')
        os.chdir('..')

def submit_spectra(VARSPACE):
    transitions = read_transitions(VARSPACE['CREATE']['transitions'])
    print('INITIAL DIR: %s'%os.getcwd())
    for trans in transitions:
        curdir = trans['name']
        print('\nCD TO %s'%curdir)
        os.chdir(curdir)
        status, message = check_job_status(curdir)
        if status in {1,3}:
            print(message+' ===> SKIPPING SUBMIT')
        else:
            subprocess.run(['sbatch','job_spectra.slurm']) # system-specific
        print('CD TO UPPER LEVEL')
        os.chdir('..')
        
def clear(VARSPACE):
    raise NotImplementedError
    
def cancel(VARSPACE):   
    raise NotImplementedError
    
def check(VARSPACE): # check the status of running jobs
    transitions = read_transitions(VARSPACE['CREATE']['transitions'])
    print('CHECKING THE JOBs STATUS IN %s'%os.getcwd())
    for trans in transitions:
        curdir = trans['name']
        print('\nCD TO %s'%curdir)
        os.chdir(curdir)
        status, message = check_job_status(curdir)
        print('Status %d: %s'%(status,message))
        print('CD TO UPPER LEVEL')
        os.chdir('..')
