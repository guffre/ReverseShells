# reverse-ssh
 Golang reverse SSH client and server

Have you ever wanted to SSH in reverse?
For example, have the machine that listens (the server) be the machine that gets the shell?
Then this code is for you! A reverse ssh shell, written in Go!

This provides a full, functional shell. It's not a "run one command then quit".
It works (both ways) on both Windows and Linux. Tested to/from Windows 10 to/from Ubuntu 18.04.

# build.bat
This is a build script provided purely for convenience. It will build 32 and 64-bit binaries for Windows and Linux.
