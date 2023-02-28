# reverse-ssh
 Golang reverse SSH client and server

## What is "reverse ssh"?
A normal SSH connection provides a shell on the *server* machine. Reverse SSH provides a shell on the *client* machine.

In other words, the machine that listens and needs port forwarding (the server) will catch a connection from the client, and then open up a shell allowing you to run commands on the client. This is "backwards" from normal SSH behavior.

This provides a full, functional shell. It's not a "run one command then quit".  
It works (both ways) on both Windows and Linux. Tested to/from Windows 10 to/from Ubuntu 18.04.

## build.bat
This is a build script provided purely for convenience. It will build 32 and 64-bit binaries for Windows and Linux.
