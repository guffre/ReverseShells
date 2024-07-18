# ReverseShells
 In CTFS, HTB challenges, and red-teaming you will sometimes need a reverse shell. This repo is a collection of reverse shells; some are written by me, some are from open-source repos

# Windows socat
This is a Windows socat compiled from cygwin executables. I essentially ran `strace socat`, and looked at what dll's it pulled in.
Windows socat is just a wrapper executable, it drops cygwin socat.exe and all required dll's into the temp directory, and then calls it.
