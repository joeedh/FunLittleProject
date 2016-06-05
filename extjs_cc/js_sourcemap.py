#NOTE: this is NOT JS sourcemaps, it's
#for the C preprocessor code I'm using

"""
class Interval:
  def __init__(srcmin, srcmax, dstmin, dstmax):
    self.src = [srcmin, srcmax]
    self.dst = [dstmin, dstmax]
#"""
 
class SourceMap:
  def __init__(self, source, filename):
    self.source = source
    self.filename = filename
    self.ivals = [];
    
    #hrm.  its tempting to make one giant
    #map, for each character in source
    
    slen = int(len(source)*1.5 + 1.0)
    self.map = [None for x in range(slen)]
    
  def insert(self, lexpos, srcline, srcfile, dstline, dstfile, lexrange=1):
    for i in range(lexpos, lexpos+lexrange):
      self.map[i] = [srcline, srcfile, dstline, dstfile]
  
  def load(self, map2):
    self.map = map2.map
    self.source = map2.source
    
  def invert(self, destbuf):
    map2 = SourceMap(destbuf, self.filename)
    
    lineno = 0
    for i, c in enumerate(self.source):
      if c == "\n":
        lineno += 1
      
      if self.map[i] != None:
        map2.insert(i, self.map[i][0], lineno, self.map[i][1])
    
    self.load(map2)
      
  def lookup(self, lexpos):
    ret = self.map[lexpos];
    
    while ret == None and lexpos >= 0:
      lexpos -= 1
      ret = self.map[lexpos]
      
    while ret == None and lexpos < len(self.map):
      lexpos -= 1
      ret = self.map[lexpos]
    
    return ret
    
    
    