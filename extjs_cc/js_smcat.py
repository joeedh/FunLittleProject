#!/usr/bin/env python3
import sys, os.path, os, time, stat, struct, ctypes, io, subprocess, math, random, difflib
import ply, re, traceback
import argparse, base64, json
from js_global import AbstractGlob
from js_cc import concat_smaps

#source map concatenator, for
#browsers that don't support
#index maps

class LocalGlob(AbstractGlob):
  g_file = ""
  g_outfile = ""
  
glob = LocalGlob()

def main():
    cparse = argparse.ArgumentParser(add_help=False)

    glob.add_args(cparse)
    cparse.add_argument("--help", action="help", help="Print this message")
      
    args = cparse.parse_args()
    glob.parse_args(cparse, args)
    
    glob.g_outfile = args.outfile
    
    #test_regexpr()
    #return 1
        
    glob.g_file = args.infile
    
    if args.infile == None:
        print("js_smcat.py: no input files")
        return -1
    
    f = open(args.infile, "r")
    files = f.readlines()
    f.close()
    
    for i in range(len(files)):
      files[i] = os.path.abspath(os.path.normpath(files[i].strip()))
      
    ret = json.dumps(concat_smaps(files))
    
    f = open(args.outfile, "w")
    f.write(ret)
    f.close()
    
    return 0

if __name__ == "__main__":
    import io, traceback
    
    try:
      ret = main()
    except SystemExit:
      ret = -1
    except:
      traceback.print_stack()
      traceback.print_exc()
      
      ret = -1
    sys.exit(ret)

