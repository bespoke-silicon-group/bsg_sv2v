'''
bsg_seqgen_modules.py

This file contains the replacement functioun for generic sequential cells that
DesignCompiler will use for elaboration. During the conversion phase, if a
SEQGEN cell is found, the instance will be replaced with the AST returned from
the SEQGEN function. The configuration of the SEQGEN cell is determined based
on if the ports are tied low. Not every configuration has been implemented. If
an unknown configuration is found, and ERROR is logged.
'''

import sys
import logging
from pyverilog.vparser.ast import *

# generic sequential cell
def SEQGEN( instance, wires, regs ):

  p = __get_instance_ports(instance)

  # Get configuration booleans
  has_clock              = (p['clocked_on']   != IntConst('1\'b0'))
  has_async_reset        = (p['clear']        != IntConst('1\'b0'))
  has_async_set          = (p['preset']       != IntConst('1\'b0'))
  has_async_enable       = (p['enable']       != IntConst('1\'b0'))
  has_async_data         = (p['data_in']      != IntConst('1\'b0'))
  has_sync_reset         = (p['synch_clear']  != IntConst('1\'b0'))
  has_sync_set           = (p['synch_preset'] != IntConst('1\'b0'))
  has_sync_enable        = (p['synch_enable'] != IntConst('1\'b0'))
  has_sync_data          = (p['next_state']   != IntConst('1\'b0'))
  has_sync_toggle        = (p['synch_toggle'] != IntConst('1\'b0'))
  has_noninverted_output = ('Q' in p)
  has_inverted_output    = ('QN' in p)

  # Log configuration
  logging.debug('SEQGEN Configuration:')
  logging.debug(('\t %s: '+('\t'*3)+'%s') % ('has_clock', str(has_clock)))
  logging.debug(('\t %s: '+('\t'*2)+'%s') % ('has_async_reset', str(has_async_reset)))
  logging.debug(('\t %s: '+('\t'*2)+'%s') % ('has_async_set', str(has_async_set)))
  logging.debug(('\t %s: '+('\t'*2)+'%s') % ('has_async_enable', str(has_async_enable)))
  logging.debug(('\t %s: '+('\t'*2)+'%s') % ('has_async_data', str(has_async_data)))
  logging.debug(('\t %s: '+('\t'*2)+'%s') % ('has_sync_reset', str(has_sync_reset)))
  logging.debug(('\t %s: '+('\t'*3)+'%s') % ('has_sync_set', str(has_sync_set)))
  logging.debug(('\t %s: '+('\t'*2)+'%s') % ('has_sync_enable', str(has_sync_enable)))
  logging.debug(('\t %s: '+('\t'*2)+'%s') % ('has_sync_data', str(has_sync_data)))
  logging.debug(('\t %s: '+('\t'*2)+'%s') % ('has_sync_toggle', str(has_sync_toggle)))
  logging.debug(('\t %s: '+('\t'*1)+'%s') % ('has_noninverted_output', str(has_noninverted_output)))
  logging.debug(('\t %s: '+('\t'*2)+'%s') % ('has_inverted_output', str(has_inverted_output)))

  # Assert all assumptions before moving on to early catch unexpected configurations
  assert not ( has_async_reset and has_sync_reset )
  assert not ( has_async_set and has_sync_set )
  assert not ( has_async_enable and has_sync_enable )
  assert not ( has_async_data and has_sync_data )
  assert not ( has_clock and has_async_data )
  assert (has_noninverted_output or has_inverted_output)

  # Not sure what to do with the synchronous toggle pin (couldn't find the RTL
  # that synthesizes this configuration pin, could be rare / unused?)
  if has_sync_toggle:
    logging.error('No implementation defined for %s replacement!' % sys._getframe().f_code.co_name)
    return InstanceList(instance.module, [], [instance])

  # EN pin
  if has_sync_enable:    EN = p['synch_enable']
  elif has_async_enable: EN = p['enable']
  else:                  EN = None

  # RESET pin
  if has_sync_reset:    RESET = p['synch_clear']
  elif has_async_reset: RESET = p['clear']
  else:                 RESET = None

  # SET pin
  if has_sync_set:    SET = p['synch_preset']
  elif has_async_set: SET = p['preset']
  else:               SET = None

  # DATA pin
  DATA = p['data_in'] if has_async_data else p['next_state']

  # OUTPUT pins
  Q  = p['Q']  if has_noninverted_output else None
  QN = p['QN'] if has_inverted_output    else None

  # Main data assign block
  assigns = []
  if Q:  assigns.append(NonblockingSubstitution(Lvalue(Q),  Rvalue(DATA)))
  if QN: assigns.append(NonblockingSubstitution(Lvalue(QN), Rvalue(Unot(DATA))))
  stmt = Block(assigns)

  # Add enable if it exists
  if EN:
    stmt = IfStatement(EN, stmt, None)

  # Add set if it exists
  if SET:
    assigns = []
    if Q:  assigns.append(NonblockingSubstitution(Lvalue(Q),  Rvalue(IntConst('1\'b1'))))
    if QN: assigns.append(NonblockingSubstitution(Lvalue(QN), Rvalue(IntConst('1\'b0'))))
    stmt = IfStatement(SET, Block(assigns), stmt)

  # Add reset if it exists
  if RESET:
    assigns = []
    if Q:  assigns.append(NonblockingSubstitution(Lvalue(Q),  Rvalue(IntConst('1\'b0'))))
    if QN: assigns.append(NonblockingSubstitution(Lvalue(QN), Rvalue(IntConst('1\'b1'))))
    stmt = IfStatement(RESET, Block(assigns), stmt)

  # Create the sensitivity list
  sens = []
  if has_clock:        sens.append( Sens(p['clocked_on'], type='posedge') )
  if has_async_data:   sens.append( Sens(p['data_in'],    type='level') )
  if has_async_enable: sens.append( Sens(p['enable'],     type='level') )
  if has_async_reset:  sens.append( Sens(p['clear'],      type='level') )
  if has_async_set:    sens.append( Sens(p['preset'],     type='level') )

  # Convert the outputs from wires to regs
  if has_noninverted_output: __convert_pin_to_reg(p['Q'],  wires, regs)
  if has_inverted_output:    __convert_pin_to_reg(p['QN'], wires, regs)

  # Return always block AST
  return Always(SensList(sens), Block([stmt]))
  
################################################################################
# Utility function that will take a port and make sure that it is declared as a
# reg. By default, everything is a wire because the elaborated netlist is just
# a bunch of module instantiations. Here we will swap those wires to regs.
################################################################################

def __convert_pin_to_reg( pin, wires, regs ):

  if type(pin) == Pointer:
    name = pin.var.name
  else:
    name = pin.name

  # We first check if it is already a reg. Typically, the reg list is much
  # smaller than the wire list and it is very common that the net is already a
  # reg (most common for large multibit registers) therefore this actually has
  # a significant speedup!
  for i,reg in enumerate(regs):
    if name == reg.name:
      return

  for i,wire in enumerate(wires):
    if name == wire.name:
      wires.pop(i)
      regs.append(Reg(wire.name, wire.width, wire.signed))
      return

################################################################################
# Utility function that get's all the ports from an instance and creates a
# simple dictionary where the key is the name of the port and the value is the
# AST for that port.
################################################################################

def __get_instance_ports( instance ):
  ports = {}
  for port in instance.portlist:
    ports[port.portname] = port.argname
  return ports

