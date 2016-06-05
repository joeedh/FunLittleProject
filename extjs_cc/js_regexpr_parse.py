import os, sys, os.path, time, random, math, io, struct, imp
import ply.yacc as yacc
import re
from ply.lex import LexToken
tokens = ["UCHAR", "ID_PART", "BACKSLASH", "DIVIDE", "LSBRACKET", "RSBRACKET", "STAR", "LT"]

re_error = False

class ReLex:
  def __init__(self, s=""):
    self.str = s
    self.cur = 0
  
  def input(self, data):
    self.str = data
    self.cur = 0
     
  def token(self):
    t = LexToken()
    
    c = self.cur
    if c >= len(self.str):
      return None
      
    c = self.str[c]
    if c == "\\": t.type = "BACKSLASH"
    elif c == "/": t.type = "DIVIDE"
    elif c == "[": t.type = "LSBRACKET"
    elif c == "]": t.type = "RSBRACKET"
    elif c == "*": t.type = "STAR"
    elif c == "\n" or c == "\r": t.type = "LT"
    elif re.match(r"[a-zA-Z0-9_$]+", c) != None:
      t.type = "ID_PART"
    else: t.type = "UCHAR"
    
    t.value = c
    t.lineno = 0
    t.lexpos = self.cur

    self.cur += 1
    
    print(t)
    return t
    
rlexer = ReLex()

def set_parse_globals(p):
  pass

def p_re_lit(p):
  '''re_lit : DIVIDE re_body DIVIDE re_flags'''
  set_parse_globals(p)
  p[0] = "/%s/%s" % (p[2], p[4])

def p_re_body(p):
  '''re_body : re_first_char re_chars'''
  set_parse_globals(p)
  p[0] = p[1] + p[2]

def p_re_chars(p):
  '''re_chars : re_chars re_char
              |
  '''
  set_parse_globals(p)
  if len(p) == 1:
    p[0] = ""
  else:
    p[0] = p[1] + p[2]

def p_re_first_char(p):
  '''re_first_char : re_non_term_restrict1
                   | re_backlash_seq
                   | re_expr_class
  '''
  set_parse_globals(p)
  p[0] = p[1]

def p_re_char(p):
  '''re_char : re_non_term_restrict2
             | re_backlash_seq
             | re_expr_class
  '''
  set_parse_globals(p)
  p[0] = p[1]

def p_re_backlash_seq(p):
  '''re_backlash_seq : BACKSLASH re_non_term'''
  set_parse_globals(p)
  p[0] = "\\" + p[2]

def p_re_non_term(p):
  '''re_non_term : UCHAR
           | LSBRACKET 
           | RSBRACKET
           | STAR
           | DIVIDE
           | BACKSLASH
           | ID_PART
  '''
  p[0] = p[1]

def p_re_non_term_restrict1(p):
  '''re_non_term_restrict1 : UCHAR
                           | RSBRACKET
                           | ID_PART
  '''
  p[0] = p[1]

def p_re_non_term_restrict2(p):
  '''re_non_term_restrict2 : UCHAR
           | RSBRACKET
           | STAR
           | ID_PART
  '''
  p[0] = p[1]
  

def p_re_non_term_restrict3(p):
  '''re_non_term_restrict3 : UCHAR
           | LSBRACKET 
           | STAR
           | DIVIDE
           | ID_PART
  '''
  p[0] = p[1]

def p_re_expr_class(p):
  '''re_expr_class : LSBRACKET re_class_chars RSBRACKET
  '''
  set_parse_globals(p)
  p[0] = "[%s]" % p[2]

def p_re_class_chars(p):
  '''re_class_chars : re_class_chars re_class_char
                    |
  '''
  set_parse_globals(p)
  if len(p) == 1:
    p[0] = ""
  else:
    p[0] = p[1] + p[2]
    
def p_re_class_char(p):
  '''re_class_char : re_non_term_restrict3
                   | re_backlash_seq
  '''
  set_parse_globals(p)
  p[0] = p[1]

def p_re_flags(p):
  '''re_flags : re_flags ID_PART
              |
  '''
  set_parse_globals(p)
  if len(p) == 1:
    p[0] = ""
  else:
    p[0] = p[1] + p[2]

def p_error(p):
  re_error = True
  print("error")
  
parser = yacc.yacc(tabmodule="parsetab_re")
