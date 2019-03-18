'''
usage: bsg_elab_to_rtl.py [-h] -i file -o file
                          [-loglvl {debug,info,warning,error,critical}]

This script takes an elaborated netlest from Synopsys DesignCompiler and
converts it back into a RTL verilog netlist.

optional arguments:
  -h, --help            show this help message and exit
  -i file               Input file
  -o file               Output file
  -loglvl {debug,info,warning,error,critical}
                        Set the logging level
'''

import sys
import argparse
import logging

from pyverilog.vparser import parser as vparser
from pyverilog.ast_code_generator.codegen import ASTCodeGenerator
from bsg_ast_walk_and_swap_inplace import ast_walk_and_swap_inplace 

### Setup the argument parsing

desc = '''
This script takes an elaborated netlest from Synopsys DesignCompiler and converts it
back into a RTL verilog netlist. 
'''

log_levels = ['debug','info','warning','error','critical']

parser = argparse.ArgumentParser(description=desc)
parser.add_argument('-i',      metavar='file',                     dest='infile',    required=True,  type=str, help='Input file')
parser.add_argument('-o',      metavar='file',                     dest='outfile',   required=True,  type=str, help='Output file')
parser.add_argument('-loglvl', choices=log_levels, default='info', dest='log_level', required=False, type=str, help='Set the logging level')
args = parser.parse_args()

### Configure the logger

if   args.log_level == 'debug':    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
elif args.log_level == 'info':     logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
elif args.log_level == 'warning':  logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.WARNING)
elif args.log_level == 'error':    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.ERROR)
elif args.log_level == 'critical': logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.CRITICAL)

### Parse the input file

logging.info('Parsing file input file: %s' % args.infile)
ast, directives = vparser.parse([args.infile])

### Walk the AST and replace DesignCompiler constructs with RTL

logging.info('Performing AST replacements.')
ast_walk_and_swap_inplace( ast )

### Output RTL

logging.info('Writting RTL to output file: %s' % args.outfile)
with open(args.outfile, 'w') as fid:
  fid.write( ASTCodeGenerator().visit( ast ) )
  
### Finish

logging.info('Finished!')
sys.exit()

