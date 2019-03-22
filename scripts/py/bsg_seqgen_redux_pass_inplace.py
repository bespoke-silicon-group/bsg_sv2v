'''
bsg_seqgen_redux_pass_inplace.py

TODO
'''

import logging

from pyverilog.vparser.ast import *

#def __get_if_depth( ifstmt ):
#  if type(ifstmt.false_statement) == IfStatement:
#    return 1 + __get_if_depth(ifstmt.false_statement)
#  else:
#    return 1

def __if_statement_eq( ifstmt1, ifstmt2 ):

  ### CHECK CONDITION
  if ifstmt1.cond != ifstmt2.cond:
    return False

  ### CHECK FALSE STATEMENT
  if type(ifstmt1.false_statement) == IfStatement and type(ifstmt2.false_statement) == IfStatement:
    if not __if_statement_eq(ifstmt1.false_statement, ifstmt2.false_statement):
      return False
  else:
    if not type(ifstmt1.false_statement) == type(ifstmt1.false_statement):
      return False

  ### CHECK TRUE STATEMENT (FOR SEQGEN SHOULD NOT BE IF STATEMENT)
  if not type(ifstmt1.true_statement) == type(ifstmt1.true_statement):
    return False

  ### IF WE GOT HERE WE ARE GOOD!
  return True



def __merge_if_statements( ifstmt1, ifstmt2 ):

  if   type(ifstmt1.false_statement) == IfStatement:            merged_false = __merge_if_statements(ifstmt1.false_statement, ifstmt2.false_statement)
  elif ifstmt1.false_statement and ifstmt2.false_statement:     merged_false = ifstmt1.false_statement.statements + ifstmt2.false_statement.statements
  elif not ifstmt1.false_statement and ifstmt2.false_statement: merged_false = ifstmt2.false_statement.statements
  elif ifstmt1.false_statement and not ifstmt2.false_statement: merged_false = ifstmt1.false_statement.statements
  else:                                                         merged_false = None

  ### True statement not an IF for SEQGEN

  if   ifstmt1.true_statement and ifstmt2.true_statement:     merged_true = ifstmt1.true_statement.statements + ifstmt2.true_statement.statements
  elif not ifstmt1.true_statement and ifstmt2.true_statement: merged_true = ifstmt2.true_statement.statements
  elif ifstmt1.true_statement and not ifstmt2.true_statement: merged_true = ifstmt1.true_statement.statements
  else:                                                       merged_true = None

  return IfStatement( ifstmt1.cond
                    , (Block(merged_true)  if merged_true  else None)
                    , (Block(merged_false) if merged_false else None) )



def __squash_block( block ):

  new_block = []

  block_stmts = block.statements.copy()
  while len(block_stmts) != 0:

    bs = block_stmts.pop(0)

    if type(bs.left.var) != Pointer:
      new_block.append(bs)
      continue

    lconcat = [bs.left.var]
    rconcat = [bs.right.var]

    bot_index = 0
    while bot_index < len(block_stmts):
      bbs = block_stmts[bot_index]
      if type(bbs.left.var) == Pointer and bbs.left.var.var == bs.left.var.var:
        lconcat.append(bbs.left.var)
        rconcat.append(bbs.right.var)
        block_stmts.pop(bot_index)
      else:
        bot_index += 1

    lconcat, rconcat = zip(*sorted(zip(lconcat, rconcat), key=lambda x: int(x[0].ptr.value), reverse=True))

    max_idx = int(lconcat[0].ptr.value)
    min_idx = int(lconcat[-1].ptr.value)

    lconcat_indexed = [None for i in range(min_idx, max_idx+1)]
    rconcat_indexed = [None for i in range(min_idx, max_idx+1)]

    for l,r in zip(lconcat,rconcat):
      i = int(l.ptr.value) - min_idx
      lconcat_indexed[i] = l
      rconcat_indexed[i] = r

    none_index = [i for i,v in enumerate(lconcat_indexed) if not v]
    none_index.append(len(lconcat_indexed))

    i = 0
    for j in none_index:
      if j != i:
        lval = Lvalue(Partselect(lconcat_indexed[i].var, lconcat_indexed[j-1].ptr, lconcat_indexed[i].ptr))
        rval_list = []

        ptr_var = None
        ptr_start = None
        ptr_end = None
        for r in rconcat_indexed[i:j][::-1]:
          if type(r) == Pointer:
            if not ptr_var:
              ptr_var   = r.var
              ptr_start = r.ptr
            else:
              if ptr_var == r.var:
                ptr_end = r.ptr
              else:
                if ptr_var and ptr_start:
                  if ptr_end:
                    rval_list.append(Partselect(ptr_var, ptr_start, ptr_end))
                  else:
                    rval_list.append(Pointer(ptr_var, ptr_start))
                ptr_var = r.var
                ptr_start = r.ptr
                ptr_end = None
          else:
            if ptr_var and ptr_start:
              if ptr_end:
                rval_list.append(Partselect(ptr_var, ptr_start, ptr_end))
              else:
                rval_list.append(Pointer(ptr_var, ptr_start))
            ptr_var = None
            ptr_start = None
            ptr_end = None
            rval_list.append(r)

        if ptr_var and ptr_start:
          if ptr_end:
            rval_list.append(Partselect(ptr_var, ptr_start, ptr_end))
          else:
            rval_list.append(Pointer(ptr_var, ptr_start))

        rval = Rvalue(Concat(rval_list))
        new_block.append(NonblockingSubstitution(lval, rval))
      i = j + 1

  return Block(new_block)


def __squash_if_statement( ifstmt ):

  if type(ifstmt.false_statement) == IfStatement:
    F = __squash_if_statement( ifstmt.false_statement )
  elif type(ifstmt.false_statement) == Block:
    F = __squash_block( ifstmt.false_statement )
  else:
    F = ifstmt.false_statement

  if type(ifstmt.true_statement) == Block:
    T = __squash_block( ifstmt.true_statement )
  else:
    T = ifstmt.true_statement

  return IfStatement(ifstmt.cond, T, F)


# seqgen_redux_pass_inplace
#
# TODO
def seqgen_redux_pass_inplace( node ):

  if type(node) == ModuleDef:

    dont_touch_items = list()
    always_blocks    = list()

    ### Get all the always blocks
    for item in node.items:
      if type(item) == Always:
        always_blocks.append(item)
      else:
        dont_touch_items.append(item)

    ### Combine like sens lists

    top_index = 0
    while top_index < len(always_blocks):
      a = always_blocks[top_index]
      bot_index = top_index + 1
      while bot_index < len(always_blocks):
        if a.sens_list == always_blocks[bot_index].sens_list:
          a.statement.statements.extend(always_blocks.pop(bot_index).statement.statements)
        else:
          bot_index += 1
      top_index += 1

    ### Combine like if statemets

    for a in always_blocks:
      top_index = 0
      while top_index < len(a.statement.statements):
        bot_index = top_index + 1
        while bot_index < len(a.statement.statements):
          top_ifstmt = a.statement.statements[top_index]
          bot_ifstmt = a.statement.statements[bot_index]
          if __if_statement_eq(top_ifstmt, bot_ifstmt):
            a.statement.statements[top_index] = __merge_if_statements(top_ifstmt,bot_ifstmt)
            a.statement.statements.pop(bot_index)
          else:
            bot_index += 1
        a.statement.statements[top_index] = __squash_if_statement(a.statement.statements[top_index])
        top_index += 1

    node.items = dont_touch_items + always_blocks

  ### Recursivly walk down all other nodes

  else:
    for c in node.children():
      seqgen_redux_pass_inplace(c)

