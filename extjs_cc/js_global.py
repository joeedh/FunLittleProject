import argparse
import os, sys, struct, io, random, os.path, types, re

glob_cmd_help_override = {
  "g_error" : "Force error",
  "g_tried_semi" : "Internal semicolon flag, for handling EOF edge cases",
  "g_file" : "Input file",
  "g_line" : "Most recently parsed line",
  "g_lexpos" : "Most recently parsed lexical position",
  "g_gen_log_code" : "Generate type logging code",
  "g_harmony_iterators" : "expansion of es6 harmony for-loops; Python's StopIteration style will be used instead.",
  "g_log_forloops" : "add extra data for logging for loops",
  "g_es6_modules" : "generate ES6 modules",
  "g_autoglobalize" : "Make module locals (but not exports) global.  Useful during refactoring."
}
glob_cmd_short_override = {}

glob_cmd_parse_exclude = set(["infile", "outfile", "nfile"])
glob_cmd_advanced = set(["g_error", "g_line", "g_file", "g_tried_semi", "g_error_pre", "g_lexpos", "g_clear_slashr", "g_lexer"])
glob_cmd_exclude = set(["g_comment_line", "g_comment", "g_comment_id", "g_lexer", "g_error_pre", "g_outfile", "g_lines", "g_lexdata"])
glob_long_word_shorten = {"generators": "gens", "error": "err", "warnings": "warn", "production": "prod"}

gcs = glob_cmd_short_override
gcs["g_log_productions"] = "lp"
gcs["g_preprocess_code"] = "npc"
gcs["g_include_dirs"] = "I"
gcs["g_do_annote"] = "na"
gcs["g_gen_source_map"] = "gm"
gcs["g_gen_smap_orig"] = "gsr"
gcs["g_minify"] = "mn"
gcs["g_add_srcmap_ref"] = "nref"
gcs["g_expand_iterators"] = "nei"
#gcs["g_harmony_iterators"] = "nhi"
gcs["g_refactor_mode"] = "rm"
gcs["g_autoglobalize"] = "ag"
gcs["g_refactor_classes"] = "rc"
gcs["g_add_opt_initializers"] = "nao"
gcs["g_do_docstrings"] = "ds"
gcs["g_docstring_propname"] = "dsp"
gcs["g_enable_static_vars"] = "esv"
gcs["g_write_manifest"] = "wm"
gcs["g_warn_types"] = "WT"
gcs["g_debug_print_calls"] = "dpr"
gcs["g_gen_es6"] = "es6"
gcs["g_validate_classes"] = "vc"
gcs["g_require_js"] = "rj"
gcs["g_es6_modules"] = "nm"
gcs["g_log_forloops"] = "lf"
gcs["g_enable_let"] = "lt"
gcs["g_compile_statics_only"] = "sn"

def argv_to_argline():
  s = ""
  for i in range(len(sys.argv)-1):
    s += sys.argv[i] + " "
  return s

glob_defaults = {}
dont_set = set(["expand", "generate", "destroy", "add", "force", 
                "print", "process", "pre", "do", "exit"])

class AbstractGlob:
    __arg_map = {}
    
    def reset(self):
      self.load(Glob(), _debug=False)
      for attr in glob_defaults:
        setattr(self, attr, glob_defaults[attr])
      
    def copy(self):
      g = Glob()
      for attr in dir(self):
        if attr.startswith("__"): continue
        p = getattr(self, attr)
        if type(p) == type(self.copy): continue
        
        setattr(g, attr, p)

      return g
      
    def load(self, g, _debug=True):
      for attr in dir(self):
        if attr.startswith("__"): continue
        
        p = getattr(g, attr)
        if type(p) == type(self.load): continue
        
        setattr(self, attr, p)
      return g
    
    def add_args(self, cparse, js_cc_mode=True):
      global glob_cmd_exclude, glob_cmd_advanced, glob_cmd_help_override
      
      def gen_cmd(attr):
        s = attr[2:].replace("_", "-")
        
        for k in glob_long_word_shorten.keys():
          v = glob_long_word_shorten[k]
          s = re.sub(k, v, s)
          
        if attr in glob_cmd_help_override:
          arg_help = glob_cmd_help_override[attr]
        else: 
          arg_help = s.replace("_", " ").replace("-", " ")
        
        val = getattr(self, attr)
        atype = None
        metavar = None
        act = "store"
        if type(val) == bool:
          if getattr(self, attr) == True:
            act = "store_false"
            found = False
            for d in dont_set:
              if s.startswith(d):
                arg_help = "don't " + arg_help
                found = True
                break
                
            if not found:
              arg_help = "no " + arg_help
              
            s = "no-"+s 
          else:
            act = "store_true"
        else:
          if type(val) == int:
            act = "store"
            atype = int
            metavar = 'i'
          elif type(val) == str:
            act = "store"
            atype = str
            
        arg_help = arg_help[0].upper() + arg_help[1:]
        
        if attr in glob_cmd_short_override:
          short = glob_cmd_short_override[attr]
        else:
          short = gen_short(s)
        
        self.__arg_map[s] = attr
        self.__arg_map[short] = attr
        return short, s, act, atype, metavar, arg_help
        
      def gen_short(string):
        cmps = string.split("-")
        s2 = ""
        i = 0
        while i < len(cmps) and (s2 == "" or s2 in shortset):
          if len(cmps[i]) == 0: 
            i += 1
            continue
            
          s2 += cmps[i][0]
          i += 1
        
        s3 = s2
        i = 1
        while s2 in shortset:
          s2 = "%s%d" % (s3, i)
          i += 1
          
        shortset.add(s2)
        return s2
      
      if js_cc_mode:
        cparse.add_argument("infile", help="input files")
        if len(sys.argv) > 2 and not sys.argv[2].startswith("-"):
          cparse.add_argument("outfile", default="", help="input files")
        else:
          cparse.add_argument("outfile", default="", nargs="?", help="input files")
      
      shortset = set('a')
      adv_attrs = []
      for attr in dir(self):
        if not attr.startswith("g_"): continue
        if attr.startswith("__"): continue
        if attr in glob_cmd_exclude: continue
        if attr in glob_cmd_advanced:
          adv_attrs.append(attr)
          continue
          
        short, long, action, ctype, metavar, help = gen_cmd(attr)
        if ctype != None:
          cparse.add_argument("-"+short, "--"+long, action=action, type=ctype, metavar=metavar, help=help)
        else:
          cparse.add_argument("-"+short, "--"+long, action=action, help=help)
          
      if "adv" in argv_to_argline():
        subparsers = cparse.add_subparsers(title="Advanced Commands")
        adv_parse = subparsers.add_parser('adv', add_help = False)
      
        for attr in adv_attrs:
          short, long, action, ctype, metavar, help = gen_cmd(attr)
          
          if ctype != None:
            adv_parse.add_argument("-"+short, "--"+long, action=action, type=ctype, metavar=metavar, help=help)
          else:
            adv_parse.add_argument("-"+short, "--"+long, action=action, help=help)

        adv_parse.add_argument("--help", action="help", help="Print this message")
          
    def parse_args(self, cparse, args):
      for k in args.__dict__:
        if k in glob_cmd_parse_exclude: continue
        
        attr = self.__arg_map[k.replace("_", "-")]
        val = getattr(args, k)
        if val != None and val != getattr(self, attr):
          setattr(self, attr, val)
          glob_defaults[attr] = val

class Glob(AbstractGlob):
    g_gen_source_map = False;
    g_add_srcmap_ref = True
    g_semi_debug = False;
    g_gen_smap_orig = False;
    g_minify = False;
    g_error = False
    g_smap_file = 0;
    g_line = 0
    g_log_productions = False
    g_production_debug = False
    g_print_stack = True
    g_file = ""
    g_error_pre = None
    g_tried_semi = False
    g_lexpos = 0
    g_clear_slashr = False
    g_print_warnings = True
    g_gen_log_code = False
    g_msvc_errors = False
    g_exit_on_err = True
    g_do_annote = True
    g_print_classes = False
    g_outfile = ""
    g_lexer = None
    g_print_nodes = False
    g_print_tokens = False
    g_validate_mode = False
    g_lex_templates = True
    g_lexdata = None
    g_comment_id = -1
    g_comment_line = -1
    g_comment = ""
    g_lines = None
    g_gen_v7_bytecode = True
    g_emit_code = False
    g_include_dirs=None
    g_preprocess_code = True
    g_combine_ifelse_nodes = False
    g_add_newlines = False
    g_force_global_strict = False
    g_autoglobalize = False
    g_expand_iterators = True
    #g_harmony_iterators = True
    g_refactor_mode = False
    g_refactor_classes = False
    g_add_opt_initializers = True
    g_replace_instanceof = True
    g_instanceof_func = "__instance_of"
    g_do_docstrings = False
    g_docstring_propname = "__doc__"
    g_enable_static_vars = True
    g_write_manifest = False
    g_warn_types = False
    g_debug_print_calls = False
    g_gen_es6 = False
    g_validate_classes = False
    g_require_js = False
    g_es6_modules = False
    g_log_forloops = False
    g_enable_let = True
    g_compile_statics_only = False
    
glob = Glob()
