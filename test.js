var a=0, b=2, c=3;

if (a == 2) {
  //console.log(b);
  a=0;
} else if (a == 1) {
  //console.log(c);
  a=1;
} else if (b == 2) {
  //console.log(f);
  a=2;
} else if (b == 1) {
  //console.log("ha!")
  a=3;
} else {
  //console.log(a, "yay!");
  a=4;
}

console.log(a, "yay!");
var b=0, c=2;

function func_test_a(arg1, arg2, arg3) {
  if (b == 0) {
    return c;
  }
  
  return 0;
}

func_test_a(1, 2, 3);

/*function a() {
  console.log("yay");
}

function b() {
  console.log.debug.bleh(a);
}

var f = a() + b() + 2.2;
var t=1, d=0, h=2;

t[a] = b;

t.bleh.one = 2;
*/