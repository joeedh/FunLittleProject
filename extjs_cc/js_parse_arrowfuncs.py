import re

wsline = {' ', '\t', '\r', '\n', '\v'}
id_re = re.compile(r'[a-zA-Z$_]+[a-zA-Z_$0-9]*')
comma_re = re.compile(r'[,]')
lparen_re = re.compile(r'\(')
rparen_re = re.compile(r'\)')
arrow_re = re.compile(r'\=\>')
assign_re = re.compile(r'\=')
rest_re = re.compile(r'\.\.\.')

class ValidateException (RuntimeError):
  pass
  
def arrow_validate(lexdata, lexpos, lookahead_limit):
  global id_re, wsline
  _p = [lexpos]
  
  def skip_ws():
    while _p[0] < len(lexdata) and lexdata[_p[0]] in wsline:
      _p[0] += 1
    if _p[0] - lexpos > lookahead_limit:
      raise ValidateException()
    
  def reget(pattern, required=True):
    skip_ws()
    m = pattern.search(lexdata[_p[0]:])
    bad = m is None or m.start() != 0
    
    if bad and required:
      raise ValidateException()
    elif bad:
      return None
    
    ret = lexdata[_p[0]:_p[0]+m.end()]
    _p[0] += m.end()
    skip_ws()
    
    if _p[0] - lexpos > lookahead_limit:
      raise ValidateException()
    
    return ret
  
  def id(required=True):
    return reget(id_re, required)
  
  def comma(required=True):
    return reget(comma_re, required)
  
  def arrow(required=True):
    return reget(arrow_re, required)
  
  def lparen(required=True):
    return reget(lparen_re, required)
  def rparen(required=True):
    return reget(rparen_re, required)
  def arrow(required=True):
    return reget(arrow_re, required)
  def assign(required=True):
    return reget(assign_re, required)
  def rest_re(required=True):
    return reget(rest_re, required)
  def peek():
    tmp = _p[0]
    skip_ws()
    
    if _p[0] < len(lexdata):
      ret = lexdata[_p[0]]
    else:
      ret = None
    
    _p[0] = tmp
    return ret
  
  c = peek()
  if c == '(':
    lparen()
    
    first = 1
    c = peek()
    while c != ')':
      if not first:
        comma()
      first = 0
      
      id()
      c = peek()
        
    rparen()
    arrow()
  else:
    id()
    arrow()
  
  if _p[0] - lexpos > lookahead_limit:
    raise ValidateException()
    
  return _p[0]
  
def lex_arrow(lexdata, lexpos, lookahead_limit=256):
  #return arrow_validate(lexdata, lexpos)
  
  try:
    i = arrow_validate(lexdata, lexpos, lookahead_limit)
  except ValidateException:
    return -1
    
  return i
  #if i >= 0:
  #  #insert guard tokens at lexpos, i
  #  return i
  
def test_lexarrow():
  test = """
  
  (a, b, c) => d, e, f;
  _ => { return b };
  test => new bleh();  
  """
  
  """
  i = test.find('(')
  j = lex_arrow(test, i)
  print(j)
  return
  #"""
  
  i = -1
  while i < len(test):
    i += 1
    j = lex_arrow(test, i)
    
    if j >= 0:
      print("found an arrow func!", i, j, test[i:j])
      i = j
    
if __name__ == "__main__":
  test_lexarrow()