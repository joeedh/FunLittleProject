#!/bin/sh

rm out.asm 2> /dev/null
rm out.bin 2> /dev/null
rm *.o 2> /dev/null
rm test.exe 2> /dev/null

python3 extjs_cc/js_cc.py test.js out.asm
python3 asm.py out.asm out.bin

gcc -c -O2 -g statemachine.c disasm.c test.c object.c literal.c list.c alloc.c -Wno-int-to-pointer-cast
gcc -o test.exe test.o statemachine.o object.o literal.o alloc.o list.o disasm.o
