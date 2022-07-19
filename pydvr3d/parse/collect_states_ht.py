import re
import os,sys
import jeanny3

"""
THIS SCRIPT ASSUMES THAT ALL JOBS ARE DONE WITHOUT ERRORS!!!

ENERGIES WITH ASSIGNMENTS ARE STORED IN FILES:
fort.8.hose-taylor.out
fort.9.hose-taylor.out

THE FORMAT OF SUCH FILE IS AS FOLLOWS:
J, ENERGY, KA, KC, MAX(|<PSI|PSI>|^2),  IPAR, KMIN, MOD(QUANTA OF NU3,2)

-- file begin --
 1       3.98439   1  0   1.00000  1  0  0
 1     704.71567   1  0   1.00000  1  0  0
 1    1107.10601   1  0   1.00000  1  0  0
 1    1402.85099   1  0   1.00000  1  0  0
 1    1800.08391   1  0   1.00000  1  0  0
 1    2060.76212   1  0   1.00000  1  0  0
 1    2098.38529   1  0   1.00000  1  0  0
 1    2204.90072   1  0   1.00000  1  0  0
-- file end --

"""

def parse_hose_taylor_out(dir,wfnfile):
    """
    Parse hose-taylor output file.
    Original name of th wavefunction file is stored in wfnfile.
    Allowed names for wfnfile can be:
       fort.8, fort.9, fort.26
    """
    
    # Check if wavefunction filename is correct
    if wfnfile not in {'fort.8','fort.9','fort.26'}:
        raise Exception('Incorrect wfnfile: ',wfnfile)
    
    # Get output file path. It is assumed that this file exists
    # and it is correctly formatted.
    filepath = os.path.join(dir,wfnfile+'.hose-taylor.out')
    
    # Parse output file.
    with open(filepath) as f:
        energies = []
        for line in f:
            line = line.strip()
            vals = line.split()
            energy = {
                'jrot'    :   int(vals[0]),
                'energy'  : float(vals[1]),
                'ka'      :   int(vals[2]),
                'kc'      :   int(vals[3]),
                'maxpsi2' : float(vals[4]),
                'ipar'    :   int(vals[5]),
                'kmin'    :   int(vals[6]),
                'nu3odd'  :   int(vals[7]),
                'wfnfile' : wfnfile,
            }
            energies.append(energy)
    return energies
    
def parse_energies(dir,jrot,kmin,ipar):
    """
    Parse folder according to values of jrot and kmin.
    """
    
    # Prepare a list of files to parse.
    if jrot==0:
        wfnfiles = ['fort.26']
    elif kmin==2:
        wfnfiles = ['fort.8','fort.9']
    elif kmin in [0,1]:
        wfnfiles = ['fort.8']
    else:
        raise Exception('unknown jrot,kmin configuration: %s'\
            %str([jrot,kmin]))
            
    # Gather data from all files in one list.
    energies = []    
    for wfnfile in wfnfiles:
        energies += parse_hose_taylor_out(dir,wfnfile)
        
    return energies
        

#if __name__=="__main__":
def test():
    #jki = [0,2,0]; dir = r'jki_0020' # ok  
    #jki = [0,2,1]; dir = r'jki_0021' # ok  
    jki = [4,2,1]; dir = r'jki_0421' # ok
    energies = parse_energies(dir,*jki)
    col = jeanny3.Collection(); col.update(energies)
    col.assign('jki_dir',lambda v: jki)
    col.tabulate(['jrot','energy','ka','kc','maxpsi2','ipar','kmin','nu3odd','wfnfile'])
        
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
                'ipar':int(vals[3]),
                })
    return states
        
#def test():
if __name__=="__main__":
            
    if len(sys.argv)<2:
        print('please supply the file containing folder list (see states.txt as a sample)\n')
        sys.exit()

    states_file = sys.argv[1]
    states = read_states(states_file)
    
    # Loop over each folder containing DVR block, and try to read all valuable info from there.  
    states_col = jeanny3.Collection()
    blocks_stat = jeanny3.Collection() 
    for s in states:
        # Fill energies collection.
        jki = [s['jrot'],s['kmin'],s['ipar']]; dir = s['name']
        energies = parse_energies(dir,*jki)
        col = jeanny3.Collection(); col.update(energies)
        col.assign('jki_dir',lambda v: jki)
        col.assign('dir',lambda v: dir)
        states_col.update(col.getitems())
        # Fill block (state) statistics collection.
        block = {'name':dir,'jrot':s['jrot'],
            'kmin':s['kmin'],'ipar':s['ipar'],
            'N':len(energies)}
        blocks_stat.update(block)
        
        
    # Display energies as a table.
    
    n_energies = len(states_col.ids())
    n_valid_states = len(set(states_col.getcol('dir')))
    n_states = len(states)
    
    # Save energies collection.
    STATES_FILE = 'states_ht.csv'
    states_col.order = ['jrot','energy','ka','kc','maxpsi2','kmin','ipar','nu3odd','wfnfile','dir','jki_dir']
    states_col.export_csv(STATES_FILE)
    print('\n%d energies from %d states have been saved to "%s". '
          'Total number of states considered: %d'%\
          (n_energies,n_valid_states,STATES_FILE,n_states))
            
    # Save statistics on DVR state blocks (calc. folders)
    STAT_FILE= 'states_ht.stat'
    blocks_stat.order = ['name','jrot','kmin','ipar','N']
    blocks_stat.tabulate(file=STAT_FILE)
    print('\nStatistics on DVR state blocks has been saved to "%s"'%STAT_FILE)
    
    print()