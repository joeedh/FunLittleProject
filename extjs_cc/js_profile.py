from js_process_ast import *

def type_logger(node, typespace):
  def arg_log():
    n = js_parse("""
      var _args = "";
      for (var i=0; i<arguments.length; i++) {
        if (i > 0)
          _args += ","
        if (typeof arguments[i] == "object")
          _args += arguments[i].constructor.name;
        else if (typeof arguments[i] == "number")
          _args += "number";
        else if (typeof arguments[i] == "boolean")
          _args += "boolean";
        else if (typeof arguments[i] == "string")
          _args += "string";
        else if (arguments[i] == null)
          _args += "null";
        else if (arguments[i] == undefined)
          _args += "undefined";
        else
          _args += "[type error]";
      }
    """);
    return n
  
  def funclog(name):
    log = arg_log()
    n2 = js_parse("""
      $n;
      _profile_log("$s", _args, get_callstack());
    """, [log, name]);
    
    return n2
    
  def func(n):
    n.prepend(funclog("FUNC"))
  
  def method(n):
    n.prepend(funclog("METH"))
  
  def setter(n):
    n.prepend(funclog("SETR"))
  
  def getter(n):
    n.prepend(funclog("GETR"))

  traverse(node, FunctionNode, func)
  traverse(node, MethodNode, method)
  traverse(node, MethodSetter, setter)
  traverse(node, MethodGetter, getter)
  
def crash_logger(node, typespace):
  pass
