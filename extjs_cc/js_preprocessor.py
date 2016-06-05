import os, sys, traceback, struct, random, math, time, io, imp, os.path
import ply_preprocessor_parse as ppp

def preprocess_text_intern(data, filename, working_dir=None):
  #kill \r's
  data = data.replace("\r", "")
  
  lexer = ppp.lexer
  p = ppp.Preprocessor(lexer)
  p.parse(data, filename);
  
  s = ""
  s2 = ""
  while True:
    tok = p.token()
    if not tok: break
    
    if tok.type == "CPP_WS" and "\n" in tok.value:
      s2 += str(tok.lineno)
      pass
      
    #print(tok.type)
    if 1: #tok.type != "CPP_COMMENT":
      s += tok.value
      s2 += tok.value
    
  #ensure trailing newline
  if not s.endswith("\n"):
    s += "\n"
  
  #smap = p.sourcemap
  #print(smap.map)
  
  #smap.invert(s)
  #print(s)
  
  """
  out = ""
  for i, c in enumerate(s):
    if c == "\n":
      line = smap.lookup(i)
      out += " -> "+str(line[0])+":"+line[1]
      
    out += c 
  
  print(out)
  print("\n====\n\n", s2)
  #"""
  
  return s
  
def preprocess_text(data, filename, working_dir=None):
  oldcwd = None
  if working_dir != None:
    oldcwd = os.getcwd()
    try:
      os.chdir(oldcwd);
    except OSError:
      sys.stderr.write("Warning: could not change working directory")

  ret = preprocess_text_intern(data, filename, working_dir)

  if working_dir != None:
    try:
      os.chdir(oldcwd);
    except OSError:
      sys.stderr.write("Warning: could not restore working directory")

  return ret
