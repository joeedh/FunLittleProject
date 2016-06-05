#Fun Little Project

This is a fun little project to create a (mostly) self-hosting, self-bootstrapping JavaScript JIT compiler,
suitable for operating system development.  JavaScript is totally unsuited to OS coding, which of course makes OS
development with JS a fascinating research topic.

The basic idea is to implement a small state machine in C that interprets Cesenta JaveScript V7 bytecode.
A JIT compiler is then written in JS to compile the bytecode to native assembly, which will then (probably)
be assembled with (compiled-in) NASM.

I plan on extending Cesenta's object model to include byte-addressed typed arrays (shouldn't be hard).

The only annoying thing is that V7's bytecode is difficult to disassemble (the one that comes with V7 doesn't work),
so for now I'm using my own compiler.  I probably won't keep it.
