import ply.yacc as yacc
import sys, os, os.path
import traceback

# Get the token map from the lexer.  This is required.
from js_global import glob

from js_ast import *
from js_lex import tokens, StringLit, HexInt
from ply.lex import LexToken, Lexer
from js_ast_match_lex import *
from js_cc import js_parse

class AstNotNode(Node):
  pass

class AstStarNode(Node):
  pass
  
class AstExprListNode(ExprListNode):
  cur = 0

class AstSetNode(Node):
  cur = 0

class AstSpecialNode(Node):
  def __init__(self, string):
      super(AstSpecialNode, self).__init__()
      self.val = string
      
  def extra_str(self):
    return self.val
    
class AstWordNode(Node):
  def __init__(self, string):
      super(AstWordNode, self).__init__()
      self.val = string
      
  def extra_str(self):
    return self.val
    
class AstCodeNode(AstWordNode):
  pass
  
def p_ast_match(p):
  '''ast_match : ast_expr
  '''
  if _debug: print("match", [str(type(t)).replace("__main__.", "").replace("<class ", "").replace("'", "").replace(">", "") for t in p])
  p[0] = p[1]
  
def p_ast_set(p):
  '''ast_set : LBK ast_exprlist RBK
  
  '''
  if _debug: print("set", [str(type(t)).replace("__main__.", "").replace("<class ", "").replace("'", "").replace(">", "") for t in p])
  p[0] = AstSetNode()
  p[0].add(p[2])
  
def p_ast_exprlist(p):
  '''ast_exprlist : ast_expr
                  | ast_exprlist COMMA ast_expr
                  |
  '''
  if _debug: print("exprlist", [str(type(t)).replace("__main__.", "").replace("<class ", "").replace("'", "").replace(">", "") for t in p])
  
  if len(p) == 1:
    p[0] = AstExprListNode([])
  elif len(p) == 2:
    p[0] = AstExprListNode([])
    p[0].add(p[1])
  else:
    p[0] = p[1]
    p[0].add(p[3])

def p_ast_noderef(p):
  '''ast_special : SPECIAL WORD
  '''
  if _debug: print("special", [str(type(t)).replace("__main__.", "").replace("<class ", "").replace("'", "").replace(">", "") for t in p])
  p[0] = AstSpecialNode(p[2])
  
def p_ast_expr(p):
  '''ast_expr : ast_expr CODE
              | ast_expr ast_special
              | ast_expr ast_set
              | ast_expr OR ast_expr
              | ast_expr NOT ast_expr
              | ast_expr ast_expr STAR
              |
  '''
  
  if _debug: print("expr", [str(type(t)).replace("__main__.", "").replace("<class ", "").replace("'", "").replace(">", "") for t in p])
  
  if len(p) == 1:
    p[0] = AstExprListNode([])
  else:
    p[0] = p[1]
  
  if len(p) == 3:
    if type(p[2]) == str:
      p[0].add(AstCodeNode(p[2]))
    else:
      p[0].add(p[2])
  elif len(p) == 4:
    if p[2] == "$^":
      n = AstNotNode()
      n.add(p[3])
      p[0].add(n)
    elif p[3] == "$*":
      n = AstStarNode()
      n.add(p[2])
      p[0].add(n)
  elif len(p) == 5:
    p[0].add(BinOpNode(p[2], p[4], p[3]))
  
# Build the parser
ast_match_parser = yacc.yacc(start='ast_match', tabmodule="parsetab_astmatch")

class MatchError (Exception):
  pass

class mref:
  def __init__(self, type, lexpos):
    self.type = type
    self.lexpos = lexpos
    self.ident = None
    
  def __str__(self):
    return "%s(%d)"%(self.type, self.lexpos)
  def __repr__(self):
    return str(self)

def node_structures_match(n1, n2):
  s1 = [n1]
  s2 = [n2]
  
  while len(s1) > 0 and len(s2) > 0:
    n1 = s1.pop(-1)
    n2 = s2.pop(-1)
    if type(n1) != type(n2): return False
    for c in n1.children:
      s1.append(c)
    for c in n2.children:
      s2.append(c)
  
  if len(s1) > 0 or len(s2) > 0: return False
  return True
  
class AstMatcher:
  def __init__(self, data=""):
    self.input(data)
    self.variants = {}
    self.smap = {}
    self.gen_special_map()
  
  def gen_special_map(self):
    for attr in dir(self):
      if attr.startswith("__") and attr.endswith("_code__"):
        k = attr[2:].replace("_code__", "")
        self.smap[k] = getattr(self, attr)

  def input(self, data):
    self.data = data
    self.variants = {}
  
  def is_right_node(self, n, ref):
      
    r1 = (type(n) in [IdentNode, VarDeclNode] and n.val == ref.ident)
    r2 = hasattr(n, "type") and n.type == ref.ident
    r3 = hasattr(n, "name") and n.name == ref.ident
    
    if not r1 and not r2: return False
    if _debug: print(n.lexpos, ref.lexpos)
    
    return n.lexpos == ref.lexpos
  
  __class_code__ = """${$class, $class<x>, $class<x,x>, $class<x,x,x,x>, $class.prototype}$"""
  
  
  def do_class(self, n, ref):
    if not self.is_right_node(n, ref): return False
    
    return True
  
  def gen_class(self, lexpos, n, ref):
    ref.ident = "__MATCH_CLASS"
    return "__MATCH_CLASS"
    
  def do_class_ident(self, n, ref):
    if not self.is_right_node(n, ref): return False

    return True
  
  def gen_class_ident(self, lexpos, n, ref):
    ref.ident = "__MATCH_CLASS_IDENT"
    return "__MATCH_CLASS_IDENT"
    
  def gen_special(self, lexpos, node):
    if not hasattr(self, "gen_"+node.val):
      raise MatchError("Invalid match code")
    
    ref = mref(node.val, lexpos)
    return getattr(self, "gen_"+node.val)(lexpos, node, ref), [ref]
    
  def handle_special(special, node):
    pass
  
  def basic_output(self, ret):
    s = ""
    refs = []
    
    if type(ret) == AstCodeNode:
      s = ret.val
    elif type(ret) == AstSpecialNode:
      s, refs = self.gen_special(len(s), ret)      
    elif type(ret) == AstSetNode:
      return self.basic_output(ret[0][ret.cur])
      
    for c in ret:
      s2, refs2 = self.basic_output(c)
      
      for r in refs2:
        r.lexpos += len(s)
      s += s2
      refs += refs2
    
    return [s, refs]
  
  def build(self, s, refs):
    if s not in self.variants:
      self.variants[s] = refs
      
  def process(self, ret, root=None, output=True):
    if root == None: root = ret
    
    if output:
      s, refs = self.basic_output(root)
      self.build(s, refs)
      output = False
      
    ret2 = ret
    if type(ret) == AstSetNode:
      ret2 = ret[0]
      
    for i, c in enumerate(ret2):
      if type(ret) == AstSetNode:
        ret.cur = i
      
      s, refs = self.basic_output(root)
      self.build(s, refs)
      
      self.process(c, root, output)
  
  def flatten_setnodes(self, node):
    if type(node) == None: return
    
    cs = list(node.children)
    if type(node) == AstExprListNode and type(node.parent) == AstSetNode and\
       len(node) == 1 and type(node[0]) == AstExprListNode:
      
      ni = node.parent.children.index(node)
      node.parent.children.remove(node)
      
      cs.reverse()
      for c in cs:
        node.parent.insert(ni, c)
      cs.reverse()
      
    for c in cs:
      self.flatten_setnodes(c)
      
  def match(self, matchdata, data=None, start_node=None):
    if data != None:
      self.input(data)
    else:
      data = self.data[:]
    
    for k in self.smap:
      repl = self.smap[k]
      
      k = "$" + k
      f = data.find(k)
      while f >= 0:
        lastf = f
        
        if f < len(data) - len(k):
          if _debug: print(f, data[f+len(k)])
          if is_word_char(data[f+len(k)]):
            lastf = f
            f = data[f+len(k):].find(k)
            
            if f < 0: 
              break
            else: 
              f += lastf + len(k)    
              continue
        
        
        data = data[:f] + repl + data[f+len(k):]
        
        lastf = f
        f = data[f+len(repl):].find(k)
        
        if f < 0: break
        else: f += lastf + len(repl)
    
    match_lexer.input(data)
    """
    t = match_lexer.token()
    while t != None:
      print(t)
      t = match_lexer.token()
    #"""
    ret = ast_match_parser.parse(data, lexer=match_lexer)
    if ret == None: raise MatchError("parse error")
    self.flatten_setnodes(ret)
    
    if _debug: print("\n")
    if _debug: print(data)
    if _debug: print(ret)
    
    def find_mref(n, mref, func):
      if func(n, mref): return True
      
      for c in n:
        ret = find_mref(c, mref, func)
        if ret: return True
      
      return False
    
    def do_mref(n, mref, func):
      ret = True
      try:
        ret = find_mref(n, mref, func)
      except MatchError:
        return False
      
      if ret == False:
        raise RuntimeError("Couldn't find special handler")
        
      return True
    
    self.process(ret)
    if type(matchdata) == str:
      node = js_parse(matchdata, start_node=start_node)
    else:
      node = matchdata
      
    for k in self.variants:
      n = js_parse(k, exit_on_err=False, validate=True)
      refs = self.variants[k]
      
      #print(k)
      if not node_structures_match(node, n): continue
      
      found = True
      for r in refs:
        rfunc = getattr(self, "do_"+r.type)
        if not do_mref(n, r, rfunc):
          found = False
          break
      
      if found: return True
    return False

_debug = 0 #False
if __name__ == "__main__":
  _debug = True
  data = """inherit($class);"""
  m = AstMatcher(data=data)

  data = """inherit(Array<x>);"""
  print("ret: ", m.match(data  ))

def ast_match(pattern, node_or_str, start_node=None):
  m = AstMatcher(data=pattern)
  return m.match(node_or_str, start_node=start_node)
  
  
