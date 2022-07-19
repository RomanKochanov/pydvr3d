import sys
import argparse

from .calc import positions as posit
from .calc import intensities as intens

from . import parse

from pydvr3d.config import print_help
from pydvr3d.config.positions import config as pos_config, \
    template_modules_dict as pos_template_modules_dict

def set_parameters(config,params):
    params = params.split(';')
    for param in params:
        param = param.strip()
        if not param: continue
        path,val = param.split('=')
        section,par = path.split('.')
        config[section][par] = val

def main_positions():
    """ Main driver for positions"""

    parser = argparse.ArgumentParser(description=\
        'Python interface to the DVR3D program suite.')

    parser.add_argument('positions', metavar='positions')

    parser.add_argument('--config', type=str, 
        help='Configuration file (mandatory for all steps except --startproject)')

    parser.add_argument('--startproject', type=str, 
        help='Stage 1: start empty project, create dummy config')
        
    parser.add_argument('--template', nargs='+', type=str, 
        help='_________1a: us a template for new project')

    parser.add_argument('--merge', type=str,
        help='_________1b: take defaults from a config file')

    parser.add_argument('--set', type=str,
        help='_________1c: explicitly set project parameters')

    parser.add_argument('--init', dest='init',
        action='store_const', const=True, default=False,
        help='Stage 2: setup pathes and names, build executables')

    parser.add_argument('--generate', dest='generate',
        action='store_const', const=True, default=False,
        help='Stage 3: generate list of ro-vibrational states')

    parser.add_argument('--create', dest='create',
        action='store_const', const=True, default=False,
        help='Stage 4: create DVR subfolder for each state')

    parser.add_argument('--submit', dest='submit',
        action='store_const', const=True, default=False,
        help='Stage 5: submit jobs to calculate energy states')

    parser.add_argument('--check', dest='check',
        action='store_const', const=True, default=False,
        help='Stage 6: check the status of the submitted jobs')
        
    parser.add_argument('--collect', dest='collect',
        action='store_const', const=True, default=False,
        help='Stage 7: collect energies to csv file')

    parser.add_argument('--hose-taylor', dest='hosetaylor',
        action='store_const', const=True, default=False,
        help='Stage 8: assign levels with Hose-Taylor procedure')

    parser.add_argument('--clean', dest='clean',
        action='store_const', const=True, default=False,
        help='Final: remove large fort.* files from job folders')
        
    args = parser.parse_args() 
    
    VARSPACE = pos_config
        
    if args.startproject:
        if args.template[0]=='help':
            print_help(pos_template_modules_dict)
            sys.exit()       
        if not args.template:
            args.template = []
        for template_pair in args.template:
            module_name,template_name = template_pair.split('.')
            section = getattr(pos_template_modules_dict[module_name],template_name)
            VARSPACE.merge_section(section)
        VARSPACE['GENERAL']['project'] = args.startproject
        if args.merge:
            VARSPACE.load(args.merge,ignore_empty_values=True)
        if args.set:
            set_parameters(VARSPACE,args.set)
        posit.startproject(VARSPACE)
    else:
        if not args.config:
            print('Error: config must be specified (use --config option).')
            sys.exit()
        VARSPACE.load(args.config)
    
    if args.init:
        posit.init(VARSPACE)
    elif args.generate:
        posit.generate(VARSPACE)
    elif args.create:
        posit.create(VARSPACE)
    elif args.submit:
        posit.submit(VARSPACE)
    elif args.check:
        posit.check(VARSPACE)
    elif args.collect:
        parse.collect_states(VARSPACE)
    elif args.hosetaylor:
        posit.hosetaylor(VARSPACE)
    elif args.clean:
        posit.clean(VARSPACE)

def main_intensities():
    """ Main driver for intensities"""
    
    parser = argparse.ArgumentParser(description='Extract information'
        'from the ab inition output file')

    parser.add_argument('ini', metavar='ini',
        help='Project settings file')

    parser.add_argument('-i', '--init', dest='init',
        action='store_const', const=True, default=False,
        help='Stage 1: setup pathes and names')

    parser.add_argument('-g', '--generate', dest='generate',
        action='store_const', const=True, default=False,
        help='Stage 2: generate list of rovib. states')

    parser.add_argument('-p', '--create', dest='create',
        action='store_const', const=True, default=False,
        help='Stage 3: create DVR subfolder for each state')

    parser.add_argument('-s', '--submit', dest='submit',
        action='store_const', const=True, default=False,
        help='Stage 4: submit jobs to calculate energy states')

    parser.add_argument('-t', '--submit-spectra', dest='submit_spectra',
        action='store_const', const=True, default=False,
        help='Stage 4b: submit spectra jobs to calculate energy states')

    parser.add_argument('-c', '--check', dest='check',
        action='store_const', const=True, default=False,
        help='Stage 5: check the status of the submitted jobs')

    parser.add_argument('-d', '--clear', dest='clear',
        action='store_const', const=True, default=False,
        help='Stage 6: clear job folders from large fort.* files')

    parser.add_argument('-x', '--cancel', dest='cancel',
        action='store_const', const=True, default=False,
        help='Stage 7: cancel uncommented jobs in the transition file')
        
    args = parser.parse_args()    
        
    VARSPACE = intens.parse_config(args.ini)
        
    if args.init:
        intens.init(VARSPACE)
    elif args.generate:
        intens.generate(VARSPACE)
    elif args.create:
        intens.create(VARSPACE)
    elif args.submit:
        intens.submit(VARSPACE)
    elif args.submit_spectra:
        intens.submit_spectra(VARSPACE)
    elif args.check:
        intens.check(VARSPACE)
    elif args.clear:
        intens.check(VARSPACE)
    elif args.cancel:
        intens.cancel(VARSPACE)
    else:
        print('ERROR: unknown flag (see --help)')

def get_help_and_exit():
    print('Usage: pydvr3d <positions|intensities> <config> <options>')
    print('Help: pydvr3d <positions|intensities> --help')
    sys.exit()

def main():
    
    try:
        switch = sys.argv[1]
    except IndexError:
        get_help_and_exit()
        
    if switch=='--help' or switch=='help':
        get_help_and_exit()
    elif switch=='positions':
        main_positions()
    elif switch=='intensities':
        main_intensities()
    else:
        raise Exception('Unknown switch: "%s"'%switch)
