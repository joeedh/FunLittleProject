from js_global import glob

def process_generators(result, typespace):
  def visit_yields(node):
    p = node
    
    while not null_node(p) and type(p) != FunctionNode:
      p = p.parent
    
    if null_node(p):
      typespace.error("yield keyword only valid within functions")
    
    p.is_generator = True
    
  traverse(result, YieldNode, visit_yields)
  
  def node_has_yield(node):
    if type(node) == YieldNode:
      return True
      
    for c in node.children:
      ret = node_has_yield(c)
      if ret: return True
      
    return False
  
  def visit_generators(node):
    def print_frames(frames, tlevel=0):
      tstr = tab(tlevel)
      tstr2 = tab(tlevel+1)
      
      s = ""
      for f in frames:
        if type(f) == Frame:
          if f.node != None:
            nstr = "%s %d " % (f.node.get_line_str(), f.label)
          else:
            nstr = str(f.label) + " "
            
          s += tstr + nstr + "{\n" + print_frames(f, tlevel+1)
          s += tstr + "}\n";
        else:
          s += tstr + f.get_line_str() + "\n"
      
      if tlevel == 0:
        print(s)
        
      return s
      
    if not node.is_generator: return
    
    def _remove_this(n):
      if n.val != "this": return
      if type(n.parent) != BinOpNode or n.parent.op != ".":
        #typespace.error("Can only reference members of 'this' in generators");
        n.val = "this2"
      else:
        n.parent.parent.replace(n.parent, n.parent[1])
      
    traverse(node, ForCNode, unpack_for_c_loops, exclude=[FunctionNode], copy_children=True);
    traverse(node, IdentNode, _remove_this)
    traverse(node, VarDeclNode, _remove_this)
    
    class Frame (list):
      def __init__(self, input=[], parent=None, node=None):
        super(Frame, self).__init__(input)
        self.parent = parent
        self.node = node
        self.locals = {}
        
      def append(self, item):
        if type(item) == Frame:
          item.parent = self
        
        super(Frame, self).append(item)

      def prepend(self, item):
        if type(item) == Frame:
          item.parent = self
        
        super(Frame, self).insert(0, item)
        
    frames = frame = Frame(node=node)
    
    stack = [c for c in node.children[1:]]
    stack.reverse()
    
    stypes = set([ForLoopNode, WhileNode, DoWhileNode,
                  IfNode, ElseNode, StatementList, TryNode, CatchNode])
    
    def set_cur(n):
      if type(n) in [IfNode, WhileNode, 
                     DoWhileNode, ForLoopNode, CatchNode]:
        n._cur = 1;
        n._startcur = 1;
      else:
        n._cur = 0
        n._startcur = 0
      
      n._start = True
      n._has_yield = node_has_yield(n)
      
      for c in n:
        set_cur(c)
    
    for c in stack: 
      set_cur(c)
    
    def is_stype(n):
      return type(n) in stypes and n._has_yield
     
    while len(stack) > 0:
      n = stack.pop(-1)
      
      if is_stype(n) and n._start:
        n._start = False
        if type(n) != StatementList or not is_stype(n.parent):
          frame2 = Frame(node=n)
          frame.append(frame2)
          frame = frame2
        
      if not is_stype(n):
        frame.append(n)
        
      if is_stype(n):
        if n._cur < len(n.children):
          stack.append(n)
          
          stack.append(n[n._cur])
          n._cur += 1
          
          #only do statement block on control nodes
          if type(n) != StatementList:
            n._cur = len(n.children)
        else:
          if type(n) != StatementList or not is_stype(n.parent):
            frame = frame.parent
    
    def compact_frames(frames):
      i = 0
      frm = None
      while i < len(frames):
        f1 = frames[i]
        
        if type(f1) == YieldNode:
          frm = None
          
        if type(f1) != Frame:
          if frm == None:
            frm = Frame()
            frames.insert(i, frm)
            frm.parent = frames
            i += 1
            
          frames.remove(f1)
          i -= 1
          frm.append(f1)
        else:
          compact_frames(f1)
          frm = None
        
        if type(f1) == YieldNode:
          frm = None
          
        i += 1
        
    def label_frames(frames, cur=None):
      if cur == None: cur = [0]
      
      frames.label = cur[0]
      cur[0] += 1
      
      for f in frames:
        if type(f) == Frame:
          if f.node != None:
            f.node.frame = f
          label_frames(f, cur)
        else:
          f.frame = f
    
    def prop_frame_refs(node, f):
      if hasattr(node, "frame"): f = node.frame
      else: node.frame = f
      
      for c in node.children:
        prop_frame_refs(c, f)
        
    def apply_frame_scope(n, scope, frames):
      if type(n) == IdentNode:
        if n.val in scope:
          n.val += "_%d" % scope[n.val]
      elif type(n) == VarDeclNode:
        n.local = False;
        if "local" in n.modifiers: n.modifiers.remove("local")
        
        if hasattr(n.parent, "_c_loop_node"):
          frames = n.parent._c_loop_node.frame
          #print("yay", n.parent._c_loop_node.frame.label)
          
        scope[n.val] = frames.label
        n.val += "_%d" % scope[n.val]
      for c in n.children:
        #ignore expr functions, but not nested functions?
        if type(c) == FunctionNode and type(c.parent) == AssignNode: continue
        if type(n) == BinOpNode and n.op == "." and c == n[1] and type(c) == IdentNode:
          continue
        if type(n) == FuncCallNode and type(c) == IdentNode and c == n[0]:
          continue
          
        apply_frame_scope(c, scope, frames)
          
    def frame_scope(frames, scope, depth=0):
      frames.scope = scope
      
      for f in frames:
        ss = "-"
        fstr = ""
        if type(f) == Frame:
          if f.node != None:
            fstr = f.node.get_line_str()
          else:
            if type(f[0]) == Frame: fstr = f[0].node.get_line_str()
            else: fstr = f[0].get_line_str()
          if f.node != None:
            ss = "+"
            scope2 = dict(scope)
            for i in range(f.node._startcur):
              apply_frame_scope(f.node[i], scope2, f)
            
            frame_scope(f, scope2, depth+1)
          else:
            frame_scope(f, scope, depth)
        else:
          fstr = f.get_line_str()
          apply_frame_scope(f, scope, frames)       
          
    scope = {}
    for a in node.children[0]:
      scope[a.val] = 0
    
    compact_frames(frames) 
    label_frames(frames)
    prop_frame_refs(node, frames)
    frame_scope(frames, scope)
    
    def frames_validate(frames):
      def gen_frame_validate(frames, tlevel=0):
        s = ""
        tstr = tab(tlevel+1)
        tstr2 = tab(tlevel+2)
        
        for f in frames:
          if type(f) == Frame:
            if f.node != None:
              cs = f.node.children
              f.node.children = f.node.children[:node._startcur]
              f.node.add(ExprNode([]))
              
              c = f.node.gen_js(tlevel+1).split("\n")[0].replace("{", "").replace("\n", "").replace("}", "").strip()
              
              if c.endswith(";"): c = c[:-1]
              
              s += tstr + c + " {\n"
              f.node.children = cs
              
            s += gen_frame_validate(f, tlevel+1)
            if f.node != None:
              s += tstr + "}\n"
          else:
            c = tstr + f.gen_js(tlevel+2)
            s += c
            if c.strip().endswith("}") == 0 and c.strip().endswith(";") == 0:
              s += ";"
            s += "\n"
        
        if tlevel == 0:
          c = node.gen_js(0).split("\n")[0] + "\n"
          s = c + s + "}\n"
        return s
        
      #print(node.gen_js(0))
      #print(scope)
      print_frames(frames)
      s = gen_frame_validate(frames)
      
      s2 = js_parse(s).gen_js(0).strip()
      s = node.gen_js(0).strip()
      s = js_parse(s, print_stack=False).gen_js(0).strip()
      
      print(s==s2)
      if s != s2:
        import difflib
        print(dir(difflib))
        d = difflib.ndiff(s.split("\n"), s2.split("\n"))
        ds = ""
        for l in d:
          ds += l + "\n"

        #print(ds)
        line_print(s)
        line_print(s2)
    
    #frames_validate(frames)
    
    flatframes = []
    def flatten_frames(frames):
      flatframes.append(frames)
      
      for f in frames:
        if type(f) == Frame:
          flatten_frames(f)
    
    flatten_frames(frames)
    print([f.label for f in flatframes])
    
    def frames_transform(frames, node2):
      scope = frames.scope
    node2 = FunctionNode(node.name, node.lineno)
    node2.add(ExprListNode([]))
    
    for c in node.children[0]:
      node2[0].add(IdentNode(c.val))
    
    frames2 = frames
    
    for j, frames in enumerate(flatframes[1:]):
      p = frames.parent
      f = frames
      
      frames.return_frame = 0
      frames.return_frame_parent = 0
        
      i = p.index(f)      
      while i >= len(p)-1 and p.parent != None:
        f = p
        p = p.parent
        i = p.index(f)
      
      if p.parent == None:
        frames.return_frame = 0
        frames.return_frame_parent = p.label
      else:
        frames.return_frame = p[i+1].label      
        frames.return_frame_parent = p.label
    
    def f_name(f):
      return "frame_%d" % f.label
    
    for frames in flatframes:
      fname = f_name(frames)
      if frames.label == 0:
        n = js_parse("""
             this.next = function() {
              var this2 = this;
              
              with (this) {
                with ($s1_scope) {
                }
              }
             };""", ("this.frame_0"), start_node=WithNode)
        
        n = find_node(n, WithNode, strict=True)
      else:
        n = js_parse("""
             function $s1() {
              if (_do_frame_debug) console.log("in $s1");
              with ($s1_scope) {
                if (_do_frame_debug) console.log("  in $s1's with");
              }
             };""", (fname), start_node=WithNode)
      
      if type(n[1]) != StatementList:
        n.replace(n[1], StatementList())
      n = n[1]
      
      func = n
      while type(func) != FunctionNode:
        func = func.parent
      
      if frames.label == 0:
        node2.add(func.parent)
      
      excl = (type(frames.node) == StatementList and type(frames.parent.node) == FunctionNode) 
      if frames.node != None and not excl and type(frames.node) != FunctionNode:
        f = frames
        
        if type(f.node) == StatementList:
          print(type(f.node.parent))
        
        sl = StatementList()
        f.node[f.node._startcur] = sl
        
        n.add(f.node)
        n = sl
        
      frames.funcnode = func
      frames.subnode = n
      
      def handle_yield(n, frame, in_for_c=None):
        if type(n) == YieldNode and not hasattr(n, "_y_h"):
          n._y_h = True
          if type(frame.parent.node) == ForLoopNode and type(frame.parent.node[0]) == ForCNode:
            c = n[0].gen_js(0)
            if len(c.replace(";", "").strip()) > 0:
              n2 = js_parse("var __yield_ret = %s;"%c)
              frame.subnode.add(n2)
              frame.subnode.add(js_parse(frame.parent.node[0][2].gen_js(0))[0]);
              n.replace(n[0], js_parse("[__yield_ret, 1]", start_node=ArrayLitNode)); 
          else:
            if len(n[0].gen_js(0).strip()) > 0:
              n.replace(n[0], js_parse("[$n, 1]", n[0], start_node=ArrayLitNode)); 
            else:
              n.replace(n[0], js_parse("[undefined, 1]", start_node=ArrayLitNode))
              
          n.print_return = True
            
        for c in n.children:
          handle_yield(c, frame)
      
      def handle_break(n, frame, add_to_subnode):
        if type(n) in [WhileNode, DoWhileNode, ForLoopNode] and not n._has_yield:
          return

        if add_to_subnode:
          n2 = js_parse("return [FrameBreak, 0];")[0]
          frame.subnode.add(n2)
          return
          
        if type(n) == BreakNode:
          n2 = js_parse("return [FrameBreak, 0];")[0]
          n.parent.replace(n, n2)
        
        for c in n.children:
          if type(c) not in [WhileNode, DoWhileNode, ForLoopNode]:
            handle_break(c, frame, False)
          
      def handle_continue(n, frame, add_to_subnode):
        if type(n) in [WhileNode, DoWhileNode, ForLoopNode] and not n._has_yield:
          return
          
        if add_to_subnode:
          n2 = js_parse("return [FrameContinue, 0];")[0]
          frame.subnode.add(n2)
          return
          
        if type(n) == ContinueNode:
          n2 = js_parse("return [FrameContinue, 0];")[0]
          n.parent.replace(n, n2)
        
        for c in n.children:
          handle_continue(c, frame, False)
                
      local_frames = "["
      totframes = 0
      def do_conv(f, frames):
        handle_yield(f, frames)
        
        if type(f) == BreakNode:
          handle_break(f, frames, True)
          return False
        else:
          handle_break(f, frames, False)
          
        if type(f) == ContinueNode:
          handle_continue(f, frames, True)
          return False
        else:
          handle_continue(f, frames, False)
        return True

      for i, f in enumerate(frames):
        if type(f) != Frame:
          if do_conv(f, frames):
            frames.subnode.add(f)
          frames.leaf = True
        else:
          frames.leaf = False
          if len(local_frames) > 1: local_frames += ", "
          local_frames += f_name(f)
          totframes += 1
          if f.node != None and type(f.node) != FunctionNode:
            if len(f.node.children) > f.node._startcur + 1:
              do_conv(f.node, f)
      
      local_frames = "frame_%d_frames = "%frames.label + local_frames + "];"
      frames.frames = js_parse(local_frames)
      frames.totframes = totframes
    
    def build_next(f, parent=None):
      if type(f) != Frame: 
        return
      
      for f2 in f:
        build_next(f2, f)
      
      subnode = f.subnode
      if (type(f.subnode) == CatchNode):
        raise "s"
      else:
        if f.label > 0: # and f.label < 3:
          f.parent.subnode.add(f.funcnode)
          pass
          
      if f.label != 0 and f.totframes > 0:
        subnode.add(js_parse("""
          if (first) {
            $s1;
          }""", f.frames.gen_js(0)))
          
        if f.node != None and type(f.node) in [ForLoopNode, WhileNode, DoWhileNode]:
          n = js_parse("""
          var ret = undefined;
          
          if ($s1_cur >= $s1_frames.length)
            break;
          
          if (_do_frame_debug) console.log("$s1", $s1_cur, $s1_frames.length);
          while ($s1_cur < $s1_frames.length && (ret = $s1_frames[$s1_cur]()) == undefined) {
            $s1_cur++;
            if ($s1_cur >= $s1_frames.length)
              break;
          }
          
          if (_do_frame_debug) console.log("  $s1 ret:", ret); 
          
          if (ret) {
            if (ret[0] == FrameBreak) {
              $s1_cur = $s1_frames.length;
              ret = undefined;
              if (_do_frame_debug) console.log("  $s1 breaking...");
              break;
            } else if (ret[0] == FrameContinue) {
              $s1_cur = 0;
              ret = undefined;
              if (_do_frame_debug) console.log("  $s1 continuing...");
              continue;
            } else {
              $s1_cur += ret[1];
              ret[1] = 0;
              
              if ($s1_cur >= $s1_frames.length) {
                $s1_cur = 0;
              }
              
              return ret;
            }
          } else {
            if ($s1_cur >= $s1_frames.length) {
              $s1_cur = 0;
            }
          }
          """, [f_name(f)])
        elif not f.leaf:
          n = js_parse("""
          var ret = undefined;
          
          if (_do_frame_debug) console.log("$s1", $s1_cur, $s1_frames.length);
          while ($s1_cur < $s1_frames.length && (ret = $s1_frames[$s1_cur]()) == undefined) {
            $s1_cur++;
            if ($s1_cur >= $s1_frames.length)
              break;
          }
          if (_do_frame_debug) console.log("  $s1 ret:", ret);          
        
          if ($s1_cur >= $s1_frames.length || ret == FrameContinue) {
            $s1_cur = 0;
          }
          
          if (ret != undefined) {
            $s1_cur += ret[1];
            ret[1] = 0;
                  
            return ret;
          }
          """, [f_name(f)]);
        
        subnode.add(n)
        
    build_next(flatframes[0], flatframes[0])
    
    node2.insert(1, js_parse("this.first = true;")[0]);
    node2.insert(1, js_parse("""
      this.__iterator__ = function() {
        return this;
      }
    """)[0])
    for f in flatframes:
      node2.insert(1, js_parse("this.frame_%d_frames = 0;" % f.label)[0])
      
    firstnode = js_parse("if (first) {\n}", start_node=IfNode)
    firstnode2 = js_parse("if (first) {\n}", start_node=IfNode)
    firstnode.replace(firstnode[1], StatementList())
    firstnode2.replace(firstnode2[1], StatementList())
    flatframes[0].subnode.add(firstnode);
    node2.insert(1, firstnode2[1]);

    firstnode = firstnode[1]
    firstnode2 = firstnode2[1]
    
    args = list(node.children[0])
    for i3 in range(len(args)):
      argn = args[i3]
      while type(argn) not in [IdentNode, VarDeclNode]:
        argn = argn[0]
     
      args[i3] = argn.val
      
    for f in flatframes:
      s = "{"
      j2 = 0
      for j, v in enumerate(f.scope.keys()):
        if f.parent != None and v in f.parent.scope:
          continue
        
        if j2 > 0: s += ", "
        j2 += 1
        
        if f.label == 0 and v in args:
          s += "%s:%s" % ("%s_%s"%(v, f.scope[v]), v)
        else:
          s += "%s:undefined" % ("%s_%s"%(v, f.scope[v]))
      s += "}"
      
      s = "this.%s_scope = %s;\n" % (f_name(f), s)
      firstnode2.add(js_parse(s)[0])
      firstnode2.add(js_parse("this.%s_cur = 0;" % f_name(f))[0])
      
    firstnode.add(flatframes[0].frames)
      
    flatframes[0].subnode.add(js_parse("""
        var ret;
        if (_do_frame_debug) console.log("$s1", $s1_cur, $s1_frames.length, $s1_scope);
        while ($s1_cur < $s1_frames.length && ((ret = $s1_frames[$s1_cur]()) == undefined)) {
          if (_do_frame_debug) console.log("$s1", $s1_cur);
          $s1_cur++;
        }
        if (_do_frame_debug) console.log("  $s1 ret:", $s1_cur, ret);
        
        first = false;
        if (ret != undefined && ret[0] != FrameBreak && ret[1] != FrameContinue) {
          $s1_cur += ret[1];
          
          return ret[0];
        }
        
        throw StopIteration;
    """, [f_name(flatframes[0])] ))
    
    node.parent.replace(node, node2)
    if 0:
      file = open("generator_test.html", "w")
      file.write("""
      <html><head><title>Generator Test</title></head>
      <script>
      FrameContinue = {1:1};
      FrameBreak = {2:2};
      """)
      file.write(node2.gen_js(3).replace("yield", "return"))
      file.write("""
  j = 0;
  for (var tst in new range(2, 8)) {
    console.log(tst);
    if (j > 10)
      break;
    j++;
  }
  </script>
  </html>
  """)
      file.close()
    
    #print(node2.gen_js(1))
    #print_frames(frames2)
    
  traverse(result, FunctionNode, visit_generators)
  