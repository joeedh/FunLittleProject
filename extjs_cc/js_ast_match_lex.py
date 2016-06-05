import sys, traceback

from js_global import glob

import ply.yacc as yacc
import ply.lex as lex
from ply.lex import TOKEN, LexToken
# List of token names.   This is always required

from js_lex import LexWithPrev

from js_regexpr_parse import parser as rparser
from types import BuiltinMethodType as PyMethodType, BuiltinFunctionType as PyFunctionType
import re

reserved_list = [
]

reserved = {}
for k in reserved_list:
  reserved[k] = k.upper()

reserved_lst = []
for k in reserved_list:
  reserved_lst.append(k.upper())
  
states = [
#  ("incomment", "exclusive"),
#  ("instr", "exclusive")
]

tokens = (
  "LBK",
  "RBK",
  "WORD",
  "OR",
  "CODE",
  "NOT",
  "COMMA",
  "SPECIAL",
  "STAR",
) + tuple(reserved_lst)

re_word_pat = re.compile(r'[a-zA-Z_]+[a-zA-Z0-9_]*')
def is_word_char(cc):
  return re_word_pat.match(cc) != None

class AstMatchLexer():
  def __init__(self, data=""):
    self.lexdata = ""
    self.lineno = 0
    self.lexpos = 0
    self.bracketstates = {}
    self.tokens = []
    self.cur = 0
    
    self.input(data)
    
  def input(self, data):
    self.lexdata = data
    self.bracketstates = {"{": [0], "[": [0], "<": [0], "(": [0]}
    self.bracket_endchars = {"}": "{", "]": "[", ">": "<", ")": "("}
    self.tokens = []
    
    self.lineno = self.lexpos = 0
    self.parse()
    self.cur = 0

  def gen_token(value, type, line, lexpos):
    t = LexToken()
    t.value = value
    t.type = type
    t.line = line
    t.lexpos = lexpos
    t.lexer = self
    
    return t
   
  def get_prev(self, i, off=1):
    if i-off >= 0 and i-off < len(self.lexdata):
      return self.lexdata[i-off]
    else:
      return ""
      
  def get_next(self, i, off=1):
    if i+off >= 0 and i+off < len(self.lexdata):
      return self.lexdata[i+off]
    else:
      return ""
      
  def parse(self):
    i = 0
    data = self.lexdata
    states = self.bracketstates
    prev = self.get_prev
    next = self.get_next
          
    toks = []
    tok = LexToken()
    tok.type = None
    tok.value = ""
    stack = []
    
    def escape(i1):
      if i1 == None: i1 = i
      return prev(i1) == "\\" and prev(i1, 2) != "\\"
    
    def inc_i(i, off=1):
      for j in range(abs(off)):
        if i < 0 or i >= len(data): break
        
        if data[i] in ["\n", "\r"]:
          self.lineno += 1
        self.lexpos += 1
        
        if off < 0:
          i -= 1
        else:
          i += 1
        
      return i
        
    def push(tok):
      if tok.type == None:
        traceback.print_stack()
        print("ERROR: None token!")
        return
        
      tok.lineno = self.lineno
      tok.lexpos = self.lexpos
      tok.lexer = self
      toks.append(tok)
      self.tokens.append(tok)
      #print(tok)
    
    def newtok(tok, ttype=None):
      if tok.type != ttype and (ttype != None or tok.value != ""):
        if tok.type != None:
          push(tok)
        tok = LexToken()
        tok.type = ttype
        tok.value = ""
      return tok
    
    in_set = 0
    while i < len(data):
      cp = prev(i)
      cc = data[i]
      cn = next(i)
      
      handled = False
      if not escape(i):
        if cc == "$":
          tok = newtok(tok)
          
          if cn == "{":
            tok.type = "LBK"
            tok.value = "${"
            i = inc_i(i)
            in_set += 1
            for k in states.keys():
              states[k].append(0)
          else:
            tok.type = "SPECIAL"
            tok.value = "$"
            
          handled = True
        elif cc == "}" and cn == "$":
          tok = newtok(tok)
          tok.type = "RBK"
          tok.value = "$}"
          i = inc_i(i)
          in_set -= 1
          
          for k in states.keys():
            states[k].pop(-1)
          
          handled = True
        elif cp == "*" and cn == "$":
          tok = newtok(tok)
          tok.type = "STAR"
          tok.value = "*"
          
          i = inc_i(i)
          handled = True
        elif cp == "^" and cn == "$":
          tok = newtok(tok)
          tok.type = "NOT"
          tok.value = "^"
          
          i = inc_i(i)
          handled = True
        elif cp == "|" and cn == "$":
          tok = newtok(tok)
          tok.type = "OR"
          tok.value = "|"
          
          i = inc_i(i)
          handled = True
        elif cc == "," and in_set:
          k = 0
          
          for t in self.bracketstates.keys():
            s = self.bracketstates[t]
            
            if s[-1] < 0:
              #print(t, prev(i, 2), cp, cc, cn, "end")
              pass
              
            k += s[-1]
          
          #print(k)
          if k == 0:
            tok = newtok(tok)
            tok.type = "COMMA"
            tok.value = ","
            handled = True
        
        if not handled and in_set > 0:
          if cc in self.bracketstates:
            states[cc][-1] += 1
          elif cc in self.bracket_endchars:
            states[self.bracket_endchars[cc]][-1] -= 1
      
      def is_word_char(cc):
        return re_word_pat.match(cc) != None
        
      if not handled:
        cp = prev(i)
        if cp == "$" and tok.type not in ["WORD", "CODE"] and is_word_char(cc):
          tok = newtok(tok)
          tok.type = "WORD"
          tok.value = cc
            
          while i < len(data) and re_word_pat.match(tok.value).span() == (0, len(tok.value)):
            i = inc_i(i)
            cc = data[i]
            tok.value += cc
          
          i = inc_i(i, -1)
          tok.value = tok.value[:-1]
          tok = newtok(tok)
        else:
          tok = newtok(tok, "CODE")
          tok.value += cc
        
      i = inc_i(i)
      
    if tok.type != None:
      push(tok)
    
  def token(self):
    if self.cur >= len(self.tokens) or self.cur < 0:
      return None
    
    self.cur += 1
    return self.tokens[self.cur-1]
    
match_lexer = AstMatchLexer()
match_lexer.input("""
  inherit($class_ident, ${$class, a.b}$)
""")

t = match_lexer.token()
"""
while t != None:
  print(t)
  t = match_lexer.token()
"""