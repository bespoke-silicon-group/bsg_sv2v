'''
usage: bsg_elab_to_rtl.py [-h] -i file -o file
                          [-loglvl {debug,info,warning,error,critical}]
                          [-no_wire_reg_decl_opt]
                          [-no_seqgen_opt] [-no_concat_opt]

This script takes an elaborated netlest from Synopsys DesignCompiler and
converts it back into a RTL verilog netlist.

optional arguments:
  -h, --help            show this help message and exit
  -i file               Input file
  -o file               Output file
  -loglvl {debug,info,warning,error,critical}
                        Set the logging level
  -no_wire_reg_decl_opt
                        Prevent the wire and reg declaration optimization
                        pass.
  -no_seqgen_opt        Turns off the seqgen redux optimization pass
  -no_concat_opt        Turns off the concat redux optimization pass
'''

import sys
import argparse
import logging

from pyverilog.vparser import parser as vparser
from pyverilog.ast_code_generator.codegen import ASTCodeGenerator

from bsg_ast_walk_and_swap_inplace import ast_walk_and_swap_inplace 
from bsg_ast_wire_reg_decl_opt_inplace import ast_wire_reg_decl_opt_inplace
from bsg_seqgen_redux_pass_inplace import seqgen_redux_pass_inplace 
from bsg_concat_redux_pass_inplace import concat_redux_pass_inplace 

# Update recursion depth (default 1000)
sys.setrecursionlimit(1500)

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

# Turn on/off optimization passes
wire_reg_decl_opt_help = 'Prevent the wire and reg declaration optimization pass.'
parser.add_argument('-no_wire_reg_decl_opt', dest='wire_reg_decl_opt', action='store_false', help=wire_reg_decl_opt_help)

parser.add_argument('-no_seqgen_opt', dest='seqgen_opt', action='store_false', help='Turns off the seqgen redux optimization pass')
parser.add_argument('-no_concat_opt', dest='concat_opt', action='store_false', help='Turns off the concat redux optimization pass')

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
(gtech, synth, seqgen) = ast_walk_and_swap_inplace( ast )
total = gtech + synth + seqgen
logging.info('Total Number of Replacements = %d' % total)
logging.info("\t GTECH swap Count: %d (%d%%)" % (gtech, (gtech/total)*100))
logging.info("\t SYNTHETIC swap Count: %d (%d%%)" % (synth, (synth/total)*100))
logging.info("\t SEQGEN swap Count: %d (%d%%)" % (seqgen, (seqgen/total)*100))

### Perform seqgen redux optimization pass

### Perform various optimization passes

# Wire / Reg Declartion Optimization
if args.wire_reg_decl_opt:
  logging.info('Performing wire/reg declartion optimizations.')
  ast_wire_reg_decl_opt_inplace( ast )

if args.seqgen_opt:
  logging.info('Performing SEQGEN redux optimization.')
  seqgen_redux_pass_inplace( ast )
  # TODO: Stats?
else:
  logging.info( 'SEQGEN redux optimization has been turned off.')

### Perform concat redux optimization pass

if args.concat_opt:
  logging.info('Performing Concat redux optimization.')
  concat_redux_pass_inplace( ast )
  # TODO: Stats?
else:
  logging.info( 'Concat redux optimization has been turned off.')

### Output RTL

logging.info('Writting RTL to output file: %s' % args.outfile)
with open(args.outfile, 'w') as fid:
  fid.write( ASTCodeGenerator().visit( ast ) )
  
### Finish

logging.info('Finished!')
sys.exit()

