from ..base import ConfigSection

class Default(ConfigSection):
    __name__ = 'MOLECULE'
    __header__ = 'MOLECULE DEFINITION'
    __template__ = \
"""
# Isotopes forming the molecule.
{isotope_left}
{isotope_center}
{isotope_right}

# Isotopic masses in a.u. (optional).
{isotope_left_mass}
{isotope_center_mass}
{isotope_right_mass}

# Dissociation energy, cm-1.
{ediss}

# Dissociation energy offset, cm-1.
{ediss_offset}

# Zero point energy, cm-1
{ezero}
"""
    ezero = 0.0
    ediss_offset = 5000.0
        
class OZONE_666(Default):
    """ Settings for the ozone principle isotopologue.
        Masses from R. D. Vocke, Jr.1 in Atomic Weights of the Elements 1997 """
    
    isotope_left = '16O'
    isotope_center = '16O'
    isotope_right = '16O'
    isotope_left_mass = 29156.9455997
    isotope_center_mass = 29156.9455997
    isotope_right_mass = 29156.9455997
    ediss = 8600.0
    
class OZONE_668(Default):
    """ Settings for the ozone 668 isotopologue.
        Masses from R. D. Vocke, Jr.1 in Atomic Weights of the Elements 1997 """
    
    isotope_left = '16O'
    isotope_center = '16O'
    isotope_right = '18O'
    isotope_left_mass = 29156.9455997
    isotope_center_mass = 29156.9455997
    isotope_right_mass = 32810.46214
    ediss = 8600.0

class S2O_226(Default):
    """ Settings for the ozone 668 isotopologue.
        Masses from R. D. Vocke, Jr.1 in Atomic Weights of the Elements 1997 """
    
    isotope_left = '32S'
    isotope_center = '32S'
    isotope_right = '16O'
    isotope_left_mass = 58281.51933
    isotope_center_mass = 58281.51933
    isotope_right_mass = 29156.9455997
    ediss = 30000.0
