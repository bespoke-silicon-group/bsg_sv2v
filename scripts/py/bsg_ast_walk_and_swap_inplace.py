'''
ast_walk_and_swap_inplace.py

This file contains the ast_walk_and_swap_inplace function which recursivly
walks through an AST and performs any modifications that we need. The main
modification is the replacement of GTECH, SYNTHETIC and SEQGEN instances back
into RTL.
'''

import inspect
import logging

from pyverilog.vparser import ast

import bsg_gtech_modules
import bsg_synthetic_modules
import bsg_seqgen_modules

# Small utility function that helps generate a dictionary with all of the
# functions found in an imported module. This function is used to generate 3
# dicts that hold all of the replacement functions for GTECH, SYNTHETIC and
# SEQGEN modules. All utility functions begin with __ so they should not
# collide with any module instances found inside the converted verilog.
def get_all_functions( module ):
  funcs = dict()
  for n,v in inspect.getmembers( module ):
    if inspect.isfunction(v):
      funcs[n] = v
  return funcs

gtech_modules_funcs     = get_all_functions( bsg_gtech_modules )
synthetic_modules_funcs = get_all_functions( bsg_synthetic_modules )
seqgen_modules_funcs    = get_all_functions( bsg_seqgen_modules )

# ast_walk_and_swap_inplace
#
# This function recursivly walks through an AST and performs any modifications
# that we need. These modifications happen in-place (ie. it will modify the AST
# that is passed in and doesn't return a new one). The main modification is
# replacing GTECH, SYNTHETIC and SEQGEN constructrs for synthesizable RTL.
def ast_walk_and_swap_inplace( node ):

  gtech_swap_count     = 0
  synthetic_swap_count = 0
  seqgen_swap_count    = 0

  ### Handle module definitions
  if type(node) == ast.ModuleDef:
    
    number_of_items      = len(node.items)

    logging.info("Module Name: %s" % node.name)
    logging.info("\t Item Count: %d" % number_of_items)

    ports = list()  ;# List of all port declarations (input and output statements)
    wires = list()  ;# List of all wire datatype declarations
    regs = list()   ;# List of all reg datatype declarations
    asts = list()   ;# All other ast inside the module (everything else)

    # Go through every AST inside the module definition
    for item in node.items:

      # If the item is a declaration
      if type(item) == ast.Decl:
        for d in item.list:

          # Explict wire declaration for output ports
          if type(d) == ast.Output:
            wires.append(ast.Wire(d.name, d.width, d.signed))

          # Split all decl
          if type(d) == ast.Wire: wires.append(d)
          else:                   ports.append(d)

      # If the item is an instance list. For elaborated netlist, every instance
      # list has exactly 1 instantiation.
      elif type(item) == ast.InstanceList:

        assert len(item.instances) == 1   ;# Assert our assumptions are true

        instance = item.instances[0]
        modname  = instance.module.replace('*','').replace('\\','')
        modline  = instance.lineno

        # Perform a GTECH gate replacement
        if modname in gtech_modules_funcs:
          logging.debug("\t GTECH replacement found -- %s, line: %d" % (modname, modline))
          gtech_swap_count += 1
          asts.append(gtech_modules_funcs[modname]( instance ))

        # Perform a SYNTHETIC module replacement
        elif modname in synthetic_modules_funcs:
          logging.debug("\t SYNTHETIC replacement found -- %s, line: %d" % (modname, modline))
          synthetic_swap_count += 1
          asts.append(synthetic_modules_funcs[modname]( instance ))

        # Perform a SEQGEN cell replacement
        elif modname in seqgen_modules_funcs:
          logging.debug("\t SEQGEN replacement found -- %s, line: %d" % (modname, modline))
          seqgen_swap_count += 1
          asts.append(seqgen_modules_funcs[modname]( instance, wires, regs ))

        # Instance not found in replacement lists (either a DesignCompiler
        # construct we don't know about or a module that is defined earlier in
        # the file). Do nothing to this item.
        else:
          logging.debug("\t No replacement found -- %s, line: %d" % (modname, modline))
          asts.append(item)

      # Keep all other items
      else:
        asts.append(item)

    # Log some statistics
    logging.info("\t GTECH swap Count: %d (%d%%)" % (gtech_swap_count, (gtech_swap_count/number_of_items)*100))
    logging.info("\t SYNTHETIC swap Count: %d (%d%%)" % (synthetic_swap_count, (synthetic_swap_count/number_of_items)*100))
    logging.info("\t SEQGEN swap Count: %d (%d%%)" % (seqgen_swap_count, (seqgen_swap_count/number_of_items)*100))

    # Compose a new items list for the module definition
    node.items = [ast.Decl([p]) for p in ports if p]   \
                 + [ast.Decl([w]) for w in wires if w] \
                 + [ast.Decl([r]) for r in regs if r]  \
                 + [a for a in asts if a]

  ### Recursivly walk down all other nodes
  else:
    for c in node.children():
      (gtech,synth,seqgen) = ast_walk_and_swap_inplace(c)
      gtech_swap_count     += gtech
      synthetic_swap_count += synth
      seqgen_swap_count    += seqgen

  return (gtech_swap_count, synthetic_swap_count, seqgen_swap_count)

