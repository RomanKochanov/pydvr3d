import re
import os,sys
import jeanny3

"""
=== DIPOLE3B SUCCESS EXAMPLE ===:

 ie1 ie2   ket energy   bra energy    frequency  z transition    x transition       dipole       s(f-i)      a-coefficient

   1   1     1515.185     1504.092      -11.093   0.576154E-05  -0.317053E-02   0.316477E-02   0.100158E-04   0.857636E-09
   1   2     1515.185     1520.009        4.824  -0.357373E-05   0.169575E-01   0.169540E-01   0.287437E-03   0.144549E-08
   1   3     1515.185     2152.334      637.149  -0.466987E-05  -0.641684E-02   0.642151E-02   0.412358E-04   0.477859E-03

=== DIPOLE3B FAILURE EXAMPLE ===:
   
selection rules violated

OR

j = 0 -> 0 not allowed: stop

OR

** fatal ** parity mismatch, spin forbidden
   
OR

???   
"""


"""
=== SPECTRA EXAMPLE ===:

     frequency  intensity   |R|^2      e_lower  p  j p    n    j p    n
     ---------- --------- ---------    -------- - ---------   ---------
        2.06056 8.138E-35 2.587E-04  3595.94690 1  3 1   15    2 1   10
        4.30985 9.421E-34 6.883E-04  3595.94690 1  3 1   16    2 1   10
        4.82380 2.430E-30 5.749E-05  1515.18503 1  3 1    2    2 1    1


=== SPECTRA FAILURE EXAMPLE ===:

** NO DATA RECEIVED FROM DIPOLE ** 

"""

def parse_dipole3b(path):
    """
    Returns a collection contains transition moments.
    """
    
    regexp_header =  '\s+ie1\s+ie2\s+ket\s+energy\s+bra\s+energy\s+frequency\s+z\s+transition\s+x\s+transition\s+dipole\s+s\(f-i\)\s+a-coefficient'
    dir = os.path.split(path)[0]
    
    with open(path) as f:

        for line in f:
            if re.match(regexp_header,line):
                break
        
        col = jeanny3.Collection()
        
        for line in f:
            vals = line.split()
            try:        
                ie1 = int(vals[0])
                ie2 = int(vals[1])
                ket_energy = float(vals[2])
                bra_energy = float(vals[3])
                frequency = float(vals[4])
                z_transition = float(vals[5])
                x_transition = float(vals[6])
                dipole = float(vals[7])
                s_fi = float(vals[8])
                a_coefficient = float(vals[9])
                
                col.update({'ie1':ie1,'ie2':ie2,'ket_energy':ket_energy,'bra_energy':bra_energy,
                    'frequency':frequency,'z_transition':z_transition,'x_transition':x_transition,
                    'dipole':dipole,'s_fi':s_fi,'a_coefficient':a_coefficient,'dir':dir})
                                        
            except (ValueError, IndexError) as e:
                pass
                
    col.order    = ['ie1','ie2','ket_energy','bra_energy','frequency','z_transition','x_transition','dipole','s_fi','a_coefficient']                
    col.floatfmt = ['d',  'd',  '.3f',       '.3f',       '.3f',      '.6e',         '.6E',         '.6E',   '.6E', '.6E']
    
    return col

"""
spectra.out: 

   0     1     2   3     4     5   6     7            8                   9             10                11             12           13

ipar    j2    p2  i2    j1    p1  i1    e2           e1                freq         s(f-i)          abs i(w)       rel i(w)        a(if) 

  1      1    0   96     0    0   58   6066.195206   6065.985090      0.210116   0.54605583E-01   0.219825E-39   0.217120E-21   0.529535E-10
  1      0    0   35     1    0   56   4923.182350   4922.779175      0.403175   0.32218272E+00   0.123620E-35   0.122099E-17   0.662194E-08
  1      1    0   85     0    0   51   5768.811037   5768.020130      0.790907   0.46341525E-02   0.112338E-38   0.110956E-20   0.239678E-09

"""
    
def parse_spectra(path):
    """
    Returns a collection contains transitions.
    """
    #regexp_header =  '\s+frequency\s+intensity\s+|R|^2\s+e_lower\sp\s+j\s+p\s+n\s+j\s+p\s+n'
    regexp_header =  'ipar\s+j2\s+p2\s+i2\s+j1\s+p1\s+i1\s+e2\s+e1\s+freq\s+s\(f-i\)\s+abs\s+i\(w\)\s+rel\s+i\(w\)\s+a\(if\)'
    dir = os.path.split(path)[0]
    
    with open(path) as f:

        for line in f:
            if re.match(regexp_header,line):
                break
        
        col = jeanny3.Collection()
        
        for line in f:
            vals = line.split()
            try:                
                frequency = float(vals[9])
                intensity = float(vals[11])
                #R2 = float(vals[ ?? ])
                e_lower = float(vals[8])
                ipar = int(vals[0])
                j = int(vals[1])
                p = int(vals[2])
                i = int(vals[3])
                j_ = int(vals[4])
                p_ = int(vals[5])
                i_ = int(vals[6])
                                
                col.update({'frequency':frequency,'intensity':intensity,'e_lower':e_lower,
                    'ipar':ipar,'j':j,'p':p,'i':i,'j_':j_,'p_':p_,'i_':i_,'dir':dir})
                    
            except (ValueError, IndexError) as e:
                pass
                
    col.order    = ['frequency','intensity',   'e_lower','ipar', 'j', 'p', 'i', 'j_', 'p_', 'i_']
    col.floatfmt = ['.5f',     '.3e',          '.5f',    'd',    'd', 'd', 'd', 'd',  'd',  'd']
                
    return col
    
def parse_single_case(path,dipole3b_out,spectra_out):
                
    dipole3b_col = parse_dipole3b(os.path.join(path,dipole3b_out))
    spectra_col = parse_spectra(os.path.join(path,spectra_out))
   
    print('===============================')
    print('DIPOLE3B OUTPUT')
    print('===============================')
    
    dipole3b_col.tabulate()
    
    print('===============================')
    print('SPECTRA OUTPUT')
    print('===============================')
    
    spectra_col.tabulate()

if __name__=='__main__':
    
    col_dipole3b = jeanny3.Collection();
    col_spectra = jeanny3.Collection();
    blocks_stat = jeanny3.Collection();

    if len(sys.argv)<2:
        print('please supply the file containing folder list (see transitions.txt as a sample)\n')
        sys.exit()

    # Read transitions file
    trans_file = sys.argv[1]
    trans_summary = []
    with open(trans_file) as f:
        print('skiping 1st line in %s'%trans_file)
        f.readline()
        for line in f:
            if not line.lstrip(): continue
            if line.lstrip()[0]=='#': continue
            vals = line.split()
            trans_summary.append({'id':vals[0],'dir':vals[1]})
        
    # Cycle through all folders given in the input file
    for t in trans_summary:
        print('reading',t)
        # parse diplole3b
        col_dip = parse_dipole3b(os.path.join(t['dir'],'dipole3b.out'))
        col_dip.assign('job_id',lambda v: t['id'])
        col_dipole3b.update(col_dip.getitems())
        # parse spectra
        col_spe = parse_spectra(os.path.join(t['dir'],'spectra.out'))    
        col_spe.assign('job_id',lambda v: t['id'])
        col_spectra.update(col_spe.getitems())
        # Fill block (state) statistics collection.
        block = {'id':t['id'],'name':t['dir'],
            'N_dip':len(col_dip.ids()),'N_spe':len(col_spe.ids())}
        blocks_stat.update(block)
    
    # Save col_dipole3b
    DIP_FILE = 'dipole3b.csv'
    col_dipole3b.export_csv(DIP_FILE)
    print('\nStatistics on DVR dipole blocks has been saved to "%s"'%DIP_FILE)
    
    # Save col_spectra
    SPE_FILE = 'spectra.csv'
    col_spectra.export_csv(SPE_FILE)
    print('\nStatistics on DVR spectra blocks has been saved to "%s"'%SPE_FILE)
    
    # Save statistics on DVR transition blocks (calc. folders)
    STAT_FILE= 'transitions.stat'
    blocks_stat.order = ['id','name','N_dip','N_spe']
    blocks_stat.tabulate(file=STAT_FILE)
    print('\nStatistics on DVR transition blocks has been saved to "%s"'%STAT_FILE)
