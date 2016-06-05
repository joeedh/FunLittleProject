#!/usr/bin/env python3.3
import os
os.environ["COLUMNS"] = "80"
os.putenv("COLUMNS", "80") #os.environ["COLUMNS"])

import js_global

delattr(js_global.Glob, "g_gen_log_code")
class TypeInferGlob (js_global.Glob):
    g_print_classes = False
    g_do_annote = True
    g_single_file = ""
    g_expand_generators = False
    g_expand_loops = False
    g_log_file = ""
    g_debug_opcode = False
    g_debug_typeinfer = False
    
js_global.glob = TypeInferGlob()
js_global.Glob = TypeInferGlob

js_global.glob_cmd_help_override["g_print_classes"] = "Print class hierarchy"
js_global.glob_cmd_help_override["g_do_annote"] = "process type annotations"
js_global.glob_cmd_help_override["g_single_file"] = "Process a single file"

js_global.glob_cmd_short_override["g_print_classes"] = "pc"
js_global.glob_cmd_short_override["g_single_file"] = "f"
js_global.glob_cmd_short_override["g_expand_generators"] = "eg"
js_global.glob_cmd_short_override["g_expand_loops"] = "el"
js_global.glob_cmd_short_override["g_log_file"] = "l"
js_global.glob_cmd_short_override["g_debug_opcode"] = "dc"
js_global.glob_cmd_short_override["g_debug_typeinfer"] = "dt"

#js_global.glob_long_word_shorten["single"] = "one"

import os, sys, os.path, traceback, gc, time, random, math, struct, io, imp, ctypes
import shelve
from js_global import glob
from js_cc import js_parse, parse
from js_ast import *
from js_lex import plexer
from js_typespace import JSTypeSpace, JSError
from js_process_ast import *
from js_opcode_emit import gen_opcode
from js_type_emit import resolve_structs, resolve_types

import argparse

if len(sys.argv) > 1 and sys.argv[1] == "clean":
  do_clean = True
else:
  do_clean = False

class LogEntry:
  def __init__(self, s):
    cs = s.split("|")
    self.vtype = cs[0]
    self.func = cs[1]
    self.file, self.line = cs[2].split(":")
    self.line = int(self.line)
    self.arg, self.type = cs[3].split(":")
    
    self.func = self.func.strip()
    self.vtype = self.vtype.strip()
    self.arg = self.arg.strip()
    self.type = self.type.strip()
    
  def __str__(self):
    vt, f, f2, l, a, t = self.vtype, self.func, self.file, self.line, self.arg, self.type
    return ("LogEntry{%s, %s ,%s, %d, %s, %s}" % (vt, f, f2, l, a, t)).replace("\n", "") + "\n"
  
  def __repr__(self):
    return str(self)
    
def parse_logfile(path):
  f = open(path, "r")
  records = []
  for l in f.readlines():
    if len(l.strip()) == 0: continue
    records.append(LogEntry(l))
  return records
  
logfile = "log.txt"

typespace = JSTypeSpace()

if os.path.exists(logfile):
  typespace.add_records(parse_logfile(logfile))
else:
  print("Could not find logfile")
  sys.exit(-1)

def main(do_clean):
  global t_stamps, db, typespace, logfile
  
  cparse = argparse.ArgumentParser(add_help=False)

  glob.add_args(cparse, js_cc_mode=False)
  cparse.add_argument("--help", action="help", help="Print this message")
    
  args = cparse.parse_args()
  glob.parse_args(cparse, args)
  
  if glob.g_log_file != None:
    logfile = glob.g_log_file
    
  if glob.g_single_file != None and glob.g_single_file != "":
    path = glob.g_single_file
    process_one_file(path)
  else:
    process_all_files()
  
def process_one_file(path):
  if not os.path.exists(path):
    sys.stderr.write("File does not exist: %s" % path)
    sys.exit(-1)
  
  file = open(path, "r")
  data = file.read()
  file.close()
  
  buf, n = parse(data, expand_loops=glob.g_expand_loops, expand_generators=glob.g_expand_generators, file=path.replace("\\", "/"))
  infer_files([n])
  
  #resolve_types(n, typespace)
  resolve_structs([n], typespace)
  #gen_opcode(n, typespace);
  
def process_all_files():
  global typespace
  files = []
  for f in os.listdir("../"):
    if f.endswith(".js"):
      files.append(f)
    
  nfiles = []
  for f in files:
    if "[Conflict]" in f: continue
    
    path = ".."+os.path.sep+f
    
    if f in t_stamps and not do_clean:
      if os.stat(path).st_mtime == t_stamps[f]:
        sys.stdout.write("Loading stored AST tree for %s...\r"%f)
        n = db[f]
        nfiles.append(n)
        
        #XXX only do one file for initial testing
        continue

    sys.stdout.write("Parsing %s...\n"%f)
    glob.reset();
    
    file = open(path, "r")
    data = file.read()
    file.close()
    
    buf, n = parse(data, expand_loops=glob.g_expand_loops, expand_generators=glob.g_expand_generators, file=path.replace("\\", "/"))
    if n == None:
      print("error!")
      break
    
    t_stamps[f] = os.stat(path).st_mtime
    db[f] = n
    nfiles.append(n)
    
  t_stamps.close()
  db.close()
  infer_files(nfiles)
  resolve_structs(nfiles, typespace)
  gen_opcode_files(nfiles, typespace)
  
def infer_files(nfiles):  
  global typespace
  
  try:
    typespace.infer_types(nfiles)
  except JSError:
    sys.exit(-1)

sp = os.path.sep + os.path.sep
dirup = ".."+sp+".."+sp+".."+sp

t_stamps = shelve.open(dirup + "type_infer_db_last")
db = shelve.open(dirup + "type_infer_db_main")
  
if __name__ == "__main__":
  try:
    main(do_clean)
  except SystemExit:
    raise sys.exc_info()[1]
  except:
    traceback.print_stack()
    traceback.print_exc()
    sys.stderr.write("error occurred; closing databases. . .")
