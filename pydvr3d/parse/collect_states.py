import re
import os,sys
import jeanny3

"""
=== VALID JOB OUTPUT slurm-*.out EXAMPLE ===:

running dvr3drjz ...
dvr3drjz ok

real	31m34.832s
user	320m48.912s
sys	4m50.213s
running rotlev3b ...
rotlev3b ok

real	0m34.503s
user	0m53.940s
sys	0m1.211s

=== INVALID JOB OUTPUT slurm-*.out EXAMPLE ===:

running dvr3drjz ...
dvr3drjz ok

real	9m37.850s
user	85m15.733s
sys	2m8.874s
running rotlev3b ...
forrtl: severe (67): input statement requires too much data, unit 26, file /home/roman/work/dvr_me/run_expmass/model_pol_jqsrt2018/pes1/test1.large/jki_0100/fort.26
Image              PC                Routine            Line        Source             
libifcoremt.so.5   00007F20D6CE6622  for__io_return        Unknown  Unknown
libifcoremt.so.5   00007F20D6D24533  for_read_seq_xmit     Unknown  Unknown
libifcoremt.so.5   00007F20D6D214CB  for_read_seq          Unknown  Unknown
rotlev3b.x         000000000041D93A  radint_                    22  radint.f90
rotlev3b.x         000000000042899D  vrmain_                    31  vrmain.f90
rotlev3b.x         00000000004201D5  select_                   189  select.f90
rotlev3b.x         000000000041E105  rotlev3b_                  55  rotlev3b.f90
rotlev3b.x         0000000000408E3F  MAIN__                      2  driver.f90
rotlev3b.x         0000000000403D1E  Unknown               Unknown  Unknown
libc-2.17.so       00007F20D47A8C05  __libc_start_main     Unknown  Unknown
rotlev3b.x         0000000000403C29  Unknown               Unknown  Unknown
rotlev3b ok

real	0m0.056s
user	0m0.004s
sys	0m0.014s

"""



""" DVR4DRJZ OUTPUT EXAMLPLE 1 (ENERGIES.OUT), WITH ZPE
   1492.92262424527     
*          #   energy (cm-1)                   j  VTET_parity VTET_symmetry
           2   700.949022793575                0           2           2
           3   1103.15319361678                0           2           2
           4   1399.25751556154                0           2           2
           5   1796.27465568947                0           2           2
           6   2057.95753829643                0           2           2
           7   2094.98519486437                0           2           2
"""


""" DVR4DRJZ OUTPUT EXAMLPLE 2 (ENERGIES.OUT), WITHOUT ZPE
*
*          #   energy (cm-1)                   j  VTET_parity VTET_symmetry
           1   2534.99843377645                0           2           1
           2   3219.45040885377                0           2           1
           3   3603.73237382429                0           2           1
           4   3900.82046867115                0           2           1
           5   4278.19702634719                0           2           1
           6   4539.02921119085                0           2           1
"""


""" ROTLEV3B OUTPUT EXAMLPLE (ENERGIES.OUT)
* energies calculated by the ROTLEV3B code
*          #   energy (cm-1)                   j  VTET_parity VTET_symmetry
           1   1495.44043477715                2           2           2
           2   1507.97500367807                2           2           2
           3   2196.37998712616                2           2           2
           4   2209.13408893425                2           2           2
           5   2540.48743844892                2           2           2
           6   2598.58981369422                2           2           2
"""




# + file "energies.out" should be non-empty

def get_job_output_filename(dir):
    filenames = jeanny3.scandir(dir,'slurm.+\.out')
    if not filenames: 
        return None
    filenames = sorted(filenames)
    filename = filenames[-1] # take the last one (can be not reliable when several runs were performed)
    return filename
    
def parse_energies(dir,j,k,i):
    """
    Parse energies.out depending on (j,k,i). See above for examples
    Return ZPE (None, if not present in file), energies and VTET parities and symmetries.
    """
    # Check if file exists
    filepath = os.path.join(dir,'energies.out')
    if not os.path.isfile(filepath):
        return None,[]
        
    ZPE = None    
    with open(filepath) as f:
        line = f.readline()
        if j==0 and (k,i) in {(0,0),(1,0),(2,0)}: 
            # Parsing dvr3drjz-outputted file,
            # ZPE is in the first line of the file.
            ZPE = float(line.strip())
        f.readline() # skip header
        energies = []
        for line in f:
            line = line.strip()
            vals = line.split()
            energy = {
                'n':int(vals[0]),
                'j':int(vals[2]),
                'p':int(vals[3]),
                's':int(vals[4]),
                'e':float(vals[1]),
                #'ZPE':ZPE,
            }
            energies.append(energy)
    return ZPE,energies

def job_failed(dir):
    """
    Try to search the signs of Fortran errors in the job output file.
    Using regular expressions.
    """
    regex = "forrtl\:([^\n]+)"
    job_output = get_job_output_filename(dir)
    if job_output is None:
        return 'no job output'
    with open(os.path.join(dir,job_output)) as f:
        data = f.read()
        res = re.search(regex,data)
        if res:
            return res.group(1)
        elif "segmentation fault" in data.lower(): # search specifically for "segmentation fault" entry
            return 'segmentation fault'
        else:
            return None
    
#if __name__=="__main__":
def test():
    jki = [0,0,0]; dir = r'/home/roman/work/dvr_me/run_expmass/model_pol_jqsrt2018/pes1/test1.large/jki_0000' # ok  
    #jki = [0,1,1]; dir = r'/home/roman/work/dvr_me/run_expmass/model_pol_jqsrt2018/pes1/test1.large/jki_0011' # ok
    #jki = [4,1,1]; dir = r'/home/roman/work/dvr_me/run_expmass/model_pol_jqsrt2018/pes1/test1.large/jki_0411' # ok
    #jki = [3,0,0]; dir = r'/home/roman/work/dvr_me/run_expmass/model_pol_jqsrt2018/pes1/test1.large/jki_0300' # fail
    ZPE,energies = parse_energies(dir,*jki)
    col = jeanny3.Collection(); col.update(energies)
    col.assign('jki',lambda v: jki)
    col.tabulate(['n','e','j','p','s','jki'])
    print('ZPE: ',ZPE)
    error_message = job_failed(dir)
    if error_message:
        print('Job failed with the following message:\n',error_message)
    else:
        print('Cannot find any signs of job failure')
        
# copy of the function from dvr3d.py suite
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
        
#if __name__=="__main__":
def collect_states(VARSPACE):
            
    #if len(sys.argv)<2:
    #    print('please supply the file containing folder list (see states.txt as a sample)\n')
    #    sys.exit()

    #states_file = sys.argv[1]
    states_file = VARSPACE['CREATE']['states']
    states = read_states(states_file)
    
    ZPEs = set()
    
    # Loop over each folder containing DVR block, and try to read all valuable info from there.  
    states_col = jeanny3.Collection()
    blocks_stat = jeanny3.Collection() 
    for s in states:
        # Fill energies collection.
        jki = [s['jrot'],s['kmin'],s['ipar']]; dir = s['name']
        ZPE,energies = parse_energies(dir,*jki)
        ZPEs.add(ZPE)
        col = jeanny3.Collection(); col.update(energies)
        col.assign('jki',lambda v: jki)
        col.assign('dir',lambda v: dir)
        states_col.update(col.getitems())
        # Fill block (state) statistics collection.
        block = {'name':dir,'jrot':s['jrot'],
            'kmin':s['kmin'],'ipar':s['ipar'],
            'N':len(energies),'error_msg':job_failed(dir)}
        blocks_stat.update(block)
        
    ZPEs = ZPEs - {None}
    if len(ZPEs)!=1:
        raise Exception('Check ZPE: %s'%ZPEs)
        
    ZPE = list(ZPEs)[0]
    
    # States already accounting for ZPE:
    # j    p    s
    # 0    2    2  [0, 0, 0]
    # 0    2    2  [0, 1, 0]
    # The rest of the stated should be normalized by ZPE.
        
    # Subtract ZPE from states (all except the ones given above)
    ids = states_col.ids(lambda v: v['jki']!=[0, 0, 0] \
        and v['jki']!=[0, 1, 0] and v['jki']!=[0, 2, 0])
    states_col.assign('e',lambda v: v['e']-ZPE,IDs=ids)
        
    # Display energies as a table.
    #states_col.tabulate(['n','e','j','p','s','jki'])
    
    n_energies = len(states_col.ids())
    n_valid_states = len(set(states_col.getcol('dir')))
    n_states = len(states)
    
    # Save energies collection.
    STATES_FILE = 'states.csv'
    states_col.order = ['n','e','j','p','s','jki','dir']
    states_col.export_csv('states.csv')
    print('\n%d energies from %d states have been saved to "%s". '
          'Total number of states considered: %d'%\
          (n_energies,n_valid_states,STATES_FILE,n_states))
    
    # Save ZPE information.
    ZPE_FILE = 'states.ZPE'
    with open(ZPE_FILE,'w') as f:
        f.write('%.8f'%ZPE)
    print('\nZPE=%f has beed saved to "%s"'%(ZPE,ZPE_FILE))
        
    # Save statistics on DVR state blocks (calc. folders)
    STAT_FILE= 'states.stat'
    blocks_stat.order = ['name','jrot','kmin','ipar','N','error_msg']
    blocks_stat.tabulate(file=STAT_FILE)
    print('\nStatistics on DVR state blocks has been saved to "%s"'%STAT_FILE)
    
    print()
