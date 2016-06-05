"""
okay, basic idea: 

class ObjA extends B, C {
  int i = 0;
  String str = "1";
  static_string<32> staticstr = "yay";
  
  constructor(String str=undefined) {
  }
  
  do_something(int i) {
    this.i += i;
  }
  
  get i2() : int {
    return i*i;
  }
  
  set i2(int i2) {
    this.i = Math.sqrt(i2);
  }
}

would turn into:

//multiple inheritance will probably be different
//than c++'s implementation, so we'll flatten
//manually
class ObjA: public ObjAParents {
  //all fields/methods are public
  public:
    int i;
    String str;
    char staticstr[32];
    
    ObjA() {
      this->str = ConstStrs[0];
      extjs_strncpy(this->staticstr, ConstStrs[1]->cstr, 32);
      i = 0;
    }
    
    ObjA(String str) {
      this->str = str;
      
      extjs_strncpy(this->staticstr, ConstStrs[1]->cstr, 32);
      i = 0;
    }
    
    void do_something(int i) {
      this.i += i;
    }
    
    int geti2() {
      return this.i*this.i;
    }
    
    void seti2(int i2) {
      this.i = (int)sqrt((float)i2);
    }
}
"""