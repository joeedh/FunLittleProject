from http import *
from http.server import *
import os, sys, os.path, math, random, time, io
import shelve, imp, struct, ctypes, ply
import mimetypes

debug_files = [] #"triangulate.js"]

win32 = sys.platform == "win32"
if win32:
  doc_root = "C:\\Users\\JoeEagar\\Google Drive\\WebGL\\".replace("\\", os.path.sep)
else:
  doc_root = os.path.abspath(os.getcwd())
  doc_root = doc_root[:doc_root.find("WebGL")+5]
  if not doc_root.endswith(os.path.sep):
    doc_root += os.path.sep

if win32:
  ipaddr = "192.168.0.43"
else:
  ipaddr = "127.0.0.1"

def bstr(s):
  if type(s) == bytes: return s
  else: return bytes(str(s), "ascii")

def mime(path):
  return mimetypes.guess_type(path)

log_file = open("log.txt", "w")
py_bin = sys.executable
if py_bin == "":
  sys.stderr.write("Warning: could not find python binary, reverting to default\n")
  py_bin = "python"

def debug_file(path):
  for d in debug_files:
    if d in path: return True
  return False
  
def run_build(path, do_all=False, always_build_file=False):
  import subprocess
  
  base = doc_root+os.path.sep+"js_build"+os.path.sep
  
  db = shelve.open(os.path.abspath(base+"../../../jbuild.db".replace("/", os.path.sep)))
  db = shelve.open(base+"jbuild.db")
  
  f = os.path.split(path)[1]
  realpath = f
  if not always_build_file and not do_all and f in db and os.path.exists(realpath):
    stat = os.stat(realpath).st_mtime
    if stat == db[f]:
      db.close()
      return
  
  db.close()
  
  cmd = [py_bin, base+"js_build.py"]
  if always_build_file and not do_all:
    cmd.append(os.path.split(path)[1])
  elif not do_all:
    cmd.append("filter")
    cmd.append(os.path.split(path)[1])
    
  cwd = doc_root+os.path.sep+"js_build"+os.path.sep
  
  ret = subprocess.Popen(cmd, cwd=cwd, stdout=sys.stdout, stderr=subprocess.PIPE)
  ret.wait()
  
  
  if ret.returncode != 0:
    errbuf = ""
    try:
      errbuf += str(ret.communicate(timeout = 0.1)[1], "latin-1");
    except subprocess.TimeoutExpired:
      pass
    
    return errbuf
  
class ReqHandler (BaseHTTPRequestHandler):
  def format_err(self, buf):
    if type(buf) == bytes: buf = str(buf, "latin-1")
    
    header = """
      <!DOCTYPE html><html><head><title>Build Error</title></head>
      <body><h1>Build Failure</h1><h3>
    """
    footer = """
      </h3>
      </body>
    """
    
    ret = ""
    for b in buf:
      if b == "\n": ret += "<br />"
      if b == " ": ret += "&nbsp"
      if b == "\t": ret += "&nbsp&nbsp"
      ret += b
    
    return (header + ret + footer).encode()
    
  def do_GET(self):
    wf = self.wfile
    body = b"yay, tst"
    
    print(self.path)
    path = os.path.normpath(doc_root + self.path)
    
    if not os.path.exists(path):
      self.send_error(404)
      return
    
    if debug_file(path):
      always = True
      errbuf = run_build(path, always_build_file=always)
      
    if "js_build" in path and path.strip().endswith(".html"):
      errbuf = run_build(path, do_all=True)
    else:
      errbuf = None
    
    if errbuf != None:
      body = self.format_err(errbuf)
    else:
      f = open(path, "rb")
      body = f.read()
      f.close()
    
    self.gen_headers("GET", len(body), mime(path));
    
    wf.write(body);
  
  def _handle_mesh_post(self):
    buf = self.rfile.read()
    print(len(buf))
    
    body = "ok"
    self.gen_headers("POST", len(body), "text/text")
    self.wfile.write(body)
    
  def _handle_logger_post(self):
    body = b"ok"
    length = None
    for k in self.headers:
      if k.lower() == "content-length":
        length = int(self.headers[k])
        break
    
    if length == None:
      self.send_error(300)
      return
    
    buf = self.rfile.read(length)
    buf = str(buf, "ascii")
    
    log_file.write(buf + "\n")
    log_file.flush()
    
    #self.gen_headers("POST", len(body), "text/text")
    #self.wfile.write(body)
    #self.wfile.flush()
    
  def do_POST(self):
    path = self.path
    
    if path == "/webgl_helper.webpy":
      self._handle_mesh_post()
    elif path == "/logger":
      self._handle_logger_post()
    else:
      self.send_error(404)
  
  def gen_headers(self, method, length, type):
    self.wfile.write(bstr(method) + b" http/1.1\r\n")
    self.send_header("Content-Type", type)
    self.send_header("Content-Length", length)
    self.send_header("Server-Host", "joeedh.no-ip.info")
    self.end_headers()
    
  def handle_mesh_post():
    body = "ok"
    
    def bstr(s):
      return bytes(str(s), "ascii")
    
    
    wf.write(body);
    
server = HTTPServer((ipaddr, 8081), ReqHandler);
server.serve_forever()
