import ply, sys, os, os.path
from asm_global import glob
from asm_parse import *
from asm_process_ast import *

if len(sys.argv) < 2:
  sys.stderr.write("error: no input file\n");
  sys.exit(-1)

def main():
  file = open(sys.argv[1], "r")
  buf = file.read()
  file.close()
  
  if len(sys.argv) > 2:
    glob.outfile = sys.argv[2]
    
  lexer.input(buf)
  for t in lexer:
    print(t)
  
  lexer.input(buf)
  lexer.lineno = 0
  
  print("\n\n")
  result = parser.parse(buf)
  result = process(result)
  
  #print(result)
  
main();
