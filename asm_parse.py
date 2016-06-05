import ply, sys
from ply import *

from asm_global import glob
from asm_ast import *

reserved = [
  'int32', 'float64'
]

tokens = [
  'ID', 'NUM', 'STRLIT', 'COMMA', 'LPAREN', 'RPAREN', 'COLON', 'CHARLIT', 'COMMENT', 'NL', 'WS'
] + [t.upper() for t in reserved];

reserved = set(reserved)

ctrlmap = {
  't' : '\t',
  'n' : '\n',
  'r' : '\r',
  'b' : '\b',
  '0' : '\0'
};

def t_ID(t):
  r'[a-zA-Z_.]+[a-zA-Z0-9_$]*';
  
  if t.value in reserved:
    t.type = t.value.upper()
  
  return t
  
t_NUM = r'[0-9]+[0-9]*'
t_STRLIT = r'".*"'
t_COMMA = r'\,'

def t_CHARLIT(t):
  r"'(.|(\\.))'"

  t.value = t.value[1:len(t.value)-1]
  
  if len(t.value) == 2 and t.value[1] in ctrlmap:
    t.value = ctrlmap[t.value[1]]
  return t
  
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_COLON = r'\:'

def t_WS(t):
  r'[ \t]+'
  #drop token
  
def t_NL(t):
  r'[\r\n]+'
  t.lexer.lineno += t.value.count('\n')
  return t
  
def t_COMMENT(t):
  r'\;.*[\n]'
  t.lexer.lineno += t.value.count('\n')
  
  #turn into newline token
  t.type = "NL"
  return t
  
def t_error(t):
  print(t.lineno+1)
  sys.stderr.write("syntax error!\n");
  sys.exit(-1)
  
lexer = lex.lex()

def pre(p):
  if p == None: return
  if hasattr(p, 'lineno'):
    line = p.lineno
    if type(line) not in [int, float]:
      line = line(0)
  else:
    line = p.lexer.lineno
  
  glob.line = line
  
def p_typeword(p):
  '''
    typeword : INT32
             | FLOAT64
  '''
  pre(p);
  p[0] = ASTNode('typeword', value=p[1])

def p_typeword_opt(p):
  '''typeword_opt : typeword
                  |
  '''
  pre(p);
  
  if len(p) > 1:
    p[0] = p[1]
    
def p_id_opt(p):
  '''id_opt : ID
            |
  '''
  pre(p);
  
  if len(p) == 2:
    p[0] = p[1]
  else:
    p[0] = None
  print("in id_opt", len(p))
  
def p_id(p):
  '''
    id : ID
  '''
  pre(p);
  
  p[0] = ASTNode('ID', value=p[1])
  
def p_strlit(p):
  '''
    strlit : STRLIT
  '''
  p[0] = ASTNode('STRLIT', value=p[1])
  pre(p);
  
def p_arg(p):
  '''arg : id
         | NUM
         | strlit
         | CHARLIT
         | INT32
         | FLOAT64
  '''
  p[0] = p[1]
  pre(p);
  
  #if type(p[0]) in [int, float]:
  #  p[0] = ASTNode('NUM', value=p[0])

def p_arglist(p):
  '''arglist : typeword_opt arg
             | typeword_opt
             | arglist COMMA typeword_opt arg
             | arglist COMMA typeword
             |
  '''
  
  pre(p);
  
  if len(p) == 1:
    p[0] = ASTNode('arglist')
  elif len(p) == 2:
    p[0] = ASTNode('arglist', children=[p[1]])
  elif len(p) == 3:
    p[0] = ASTNode('arglist')
    if p[1] != None:
      p[0].add(ASTNode('typed', children=[p[2], p[1]]))
    else:
      p[0].add(p[2])
  elif len(p) == 4:
    p[0] = p[1]
    p[1].add(p[3])
  elif len(p) == 5:
    p[0] = p[1]
    if p[3] != None:
      p[0].add(ASTNode('typed', children=[p[4], p[3]]))
    else:
      p[0].add(p[4])
    
  print("in arglist")
  
def p_inst(p):
  '''inst : id
          | id arglist
  '''
  print("in inst")
  pre(p);
  
  if len(p) == 2:
    p[0] = p[1]
  else:
    p[0] = ASTNode("Inst", children=[p[1], p[2]])
    
def p_label(p):
  '''label : ID COLON
  '''
  
  pre(p);
  print("in label");
  
  p[0] = ASTNode('Label', children=[p[1]])
  
def p_statement(p):
  '''statement : label NL
               | inst NL
               | NL
  '''
  
  pre(p);
  print("in statement");
  
  if len(p) > 2:
    p[0] = p[1]
  else:
    p[0] = ASTNode("NL-nop")
    
def p_statementlist(p):
  '''statementlist : statement
                   | statementlist statement
                   |
  '''
  
  pre(p);
  if len(p) == 1:
    p[0] = ASTNode("StatementList", children=[])
  elif len(p) == 2:
    p[0] = ASTNode("StatementList", children=[p[1]])
  elif len(p) == 3:
    p[0] = p[1]
    p[0].add(p[2])
    
  print("in statementlist")
  
def p_error(p):
  if p == None:
    lineno = "EOF"
  elif hasattr(p, "lineno"):
    lineno = p.lineno
    if type(lineno) != int:
      lineno = lineno(0)
  else:
    lineno = p.lexer.lineno
    
  sys.stderr.write("error: %s" % (lineno+1))
  sys.exit(-1)
  
parser = yacc.yacc(start="statementlist")

