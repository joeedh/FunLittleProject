import ply.yacc as yacc
import sys, os, os.path
import traceback

# Get the token map from the lexer.  This is required.
from js_global import glob

from js_ast import *
from js_lex import tokens, StringLit, HexInt
from ply.lex import LexToken, Lexer

#AST nodes that are used in intermediate stages of parsing,
#but are NEVER EVER in the final AST tree.
from js_parser_only_ast import *
from js_process_ast_parser_only import *

from js_parse import *

"""
This is a special "mode" that changes
the syntax to a statically-typed language,
optimized and checked for writing high-performance
code, but can still compile into JavaScript
"""

def p_statementlist(p):
  ''' statementlist : statement
                    | statement_nonctrl
                    | statementlist statement
                    | statementlist statement_nonctrl 
                    |
  '''
  set_parse_globals(p);
  if len(p) == 1:
    p[0] = StatementList()
  elif len(p) == 2:
    n = StatementList()
    n.add(p[1])
    p[0] = n
  elif len(p) == 3:
    if type(p[1]) != StatementList:
      p[0] = StatementList()
      p[0].add(p[1])
      p[0].add(p[2])
    else:
      p[0] = p[1]
      if p[2] != None:
        p[0].add(p[2])

def p_class(p):
  '''class : CLASS ID template_opt class_tail'''
  set_parse_globals(p)
  
  tail = p[4]
  heritage = tail[0]
  cls = ClassNode(p[2], heritage)
  
  for n in tail[1]:
    cls.add(n)
  
  p[0] = cls
  if p[3] != None:
    p[0].template = p[3]
  
def p_exprclass(p):
  '''exprclass : CLASS id_opt class_tail'''
  set_parse_globals(p)
  
  tail = p[3]
  heritage = tail[0]
  
  if p[2] == None:
    p[2] = "(anonymous)"
    
  cls = ClassNode(p[2], heritage)
  
  for n in tail[1]:
    cls.add(n)
  
  p[0] = expand_harmony_class(cls)

def p_class_tail(p):
  '''class_tail : class_heritage_opt LBRACKET class_body_opt RBRACKET'''
  set_parse_globals(p)

  p[0] = [p[1], p[3]]
  
  for i in range(2):
    if p[0][i] == None:
      p[0][i] = []
  
def p_class_list(p):
  '''class_list : var_type
                | class_list COMMA var_type
  '''
  set_parse_globals(p)
  
  if len(p) == 2:
    p[0] = [p[1]];
  else:
    p[0] = p[1];
    if type(p[0]) != list:
      p[0] = [p[0]]
    p[0].append(p[3])
    
def p_class_heritage(p):
  '''class_heritage : EXTENDS class_list'''
  
  set_parse_globals(p)
  p[0] = p[2]

def p_class_heritage_opt(p):
  '''class_heritage_opt : class_heritage
                        | 
  '''
  set_parse_globals(p)
  
  if len(p) == 2:
    p[0] = p[1]
  
def p_class_body_opt(p):
  '''class_body_opt : class_element_list
                    |
  '''
  set_parse_globals(p)
 
  if len(p) == 1:
    p[0] = []
  else:
    p[0] = p[1]
    
  if p[0] == None: 
    p[0] = []

def p_class_element_list(p):
  '''class_element_list : class_element
                        | class_element_list class_element
  '''
  set_parse_globals(p)
  
  if len(p) == 2:
    p[0] = [p[1]]
  else:
    p[0] = p[1]
    p[0].append(p[2])

  
def p_class_element(p):
  '''class_element : method_def
                   | STATIC method_def
                   | class_var
  '''
  set_parse_globals(p)
  
  if len(p) == 2:
    p[0] = p[1]
  else:
    p[0] = p[2]
    p[0].is_static = True

def p_class_var(p):
  '''class_var : class_vartype ID SEMI
               | class_vartype ID ASSIGN expr SEMI
  '''
  set_parse_globals(p)
  
  p[0] =  ClassMember(p[2])
  if len(p) == 6:
    p[0].add(p[4])

def p_basic_var_type(p):
  '''
  basic_var_type : BYTE
                 | INT
                 | SHORT
                 | FLOAT
                 | DOUBLE
                 | CHAR
  '''
  p[0] = BuiltinTypeNode(p[1])

def p_var_type2(p):
  ''' var_type2 : basic_var_type 
                | ID
                | ID template_ref
  '''
  if len(p) == 2:
    if type(p[1]) == str:
      p[0] = TypeRefNode(p[1])
    else:
      p[0] = p[1]
  else:
    p[0] = TypeRefNode(p[1])
    p[0].template = p[2]
  
def p_class_vartype(p):
  '''class_vartype : var_type2
                   | prop_modifiers var_type2
  '''
  set_parse_globals(p)
  
  if len(p) == 2:
    p[0] = p[1]
  else:
    p[0] = p[2]
    p[0].modifiers = p[1]

def p_prop_modifiers(p):
  '''prop_modifiers : type_modifiers UNSIGNED
                    | type_modifiers SIGNED
                    | type_modifiers CONST
                    | STATIC
                    | UNSIGNED
                    | CONST
                    |
  '''
  set_parse_globals(p)
    
  if len(p) == 2:
    p[0] = set([p[1]])
  else:
    p[0] = p[1]
    p[0].add(p[2])

def p_method(p):
  '''method : ID LPAREN funcdeflist RPAREN func_type_opt LBRACKET statementlist_opt RBRACKET'''
  set_parse_globals(p)
  
  name = p[1]
  params = p[3]
  statementlist = p[7]
  
  if statementlist == None:
    statementlist = StatementList()
  
  p[0] = MethodNode(name)
  p[0].add(params)  
  p[0].add(statementlist)
  if p[5] != None:
    p[0].type = p[5]
    
def p_method_def(p):
  #I don't want to make get/set exclusive parse tokens,
  #so I'm going to enforce that here in the production function.
  
  '''method_def : method
                | ID ID LPAREN RPAREN func_type_opt LBRACKET statementlist_opt RBRACKET
                | ID ID LPAREN setter_param_list RPAREN func_type_opt LBRACKET statementlist_opt RBRACKET
  '''
  set_parse_globals(p)
  
  if len(p) == 2:
    p[0] = p[1]
  elif p[1] == "get" and len(p) == 9:
    name = p[2]
    p[0] = MethodGetter(name)
    if p[7] == None: p[7] = StatementList()
    p[0].add(p[7])
    if p[5] != None:
      p[0].type = p[5]
  elif p[1] == "set" and len(p) == 10:
    name = p[2]
    p[0] = MethodSetter(name)
    p[0].add(p[4])
    if p[8] == None: p[8] = StatementList()
    p[0].add(p[8])
    if p[6] != None:
      p[0].type = p[6]
  else:
    glob.g_error = True
    glob.g_error_pre = p
    print_err(p, True)
    raise SyntaxError("Expected 'get' or 'set'");
  
def p_setter_param_list(p):
  '''
    setter_param_list : ID
  '''
  set_parse_globals(p)
  
  p[0] = ExprListNode([VarDeclNode(ExprNode([]), name=p[1])])
  return

_parser = yacc.yacc()
parser = Parser(_parser);
