from asm_global import glob

class ASTNode (list):
  def __init__(self, type, children=[], value=None):
    self.type = type
    self.value = value
    
    self.file = glob.file
    self.line = glob.line
    self.lexpos = glob.lexpos
    self.parent = None
    
    for c in children:
      self.add(c)
  
  def add(self, c):
    if c is None:
      c = ASTNode('None')
    elif type(c) in [int, float]:
      c = ASTNode("ID", value=c)
    elif type(c) == str:
      c = ASTNode("NUM", value=c)
    elif type(c) == None:
      c = ASTNode("None");
    
    c.parent = self
    self.append(c)

  def __str__(self, tlevel=0):
    t = ""
    for i in range(tlevel):
      t += "  "
    
    s = ""
    s += t + self.type + (" value=%s { \n" % self.value)
    for c in self:
      if not isinstance(c, ASTNode):
        s += t + "  " + str(c) + "\n"
      else:
        s += c.__str__(tlevel+1)
    s += t + "}" + "\n"
    
    return s