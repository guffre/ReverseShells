# git-gud-udp
A reliable UDP transfer with fairly low overhead. No dependencies, written in Python 2.7
Data can be encrypted using RC4"secure_send" and "secure_recv" for built-in data-in-transit encryption using Diffie-Hellmann + RC4.

The encryption is swappable between stream and block ciphers though. Simply change:
    GGUdp.encryption = RC4
    
to point to the encryption class of your choice. That class must have three things to be compatible:
1) A `make_key` as a class-method, that creates the key that will be used. The argument is a Python long, and it can return anything that YourEncryption.__init__() will accept as a key.
2) A class method `crypt`. For stream-ciphers, it must accept individual bytes. For block-ciphers, it must accept arbitrarily-sized data that will be between 3 and `GGUdp.MAX_DATA_SIZE` bytes.
3) In the below code snippet, where self._crypt is your encryption class, and self._crypt.crypt is BOTH the encrypt and decrypt function:

    def _encrypt(self, data):
        data = bytearray(data)
        data = self._crypt.crypt(data)
        return data


# Packet Info
 [CHECKSUM]\([PACKET_NUMBER][DATA]\)
 
 Currently, checksum is implemented as an MD5 hash of PACKET_NUMBER+DATA
 Packets are randomly sized between MIN_DATA_SIZE and MAX_DATA_SIZE.
 This defaults to data sizes between 500 and 4082
 
 NOTE: The ggudp protocol automatically handle sizes for you, so theres no need to specify size when `send()`ing or `recv()ing`. That said, a single `send()/recv()` gets stored in memory (just like with TCP) so your program should chunk data if youre sending/recieving something exceptionally large.
 
 `send()` and `recv()` will return `False` if data fails to transfer reliably.

# Example Usage

 ## Client:
     s = GGUdp("127.0.0.1", 8000)
     data = "hello world"
     s.send(data)
 
 ## Server:
      s = GGUdp("0.0.0.0", 8000)
      s.bind()
      while True:
          data = s.recv()
          if data:
              print(data)

# Known Bugs
 Currently, the server MUST be started before the client is executed. There's an issue with initial callbacks that still needs to be debugged.

# Timeout Information
 Note, TIMEOUT_REREQUEST_SAFETY * TIMEOUT_RECV_REREQUEST is roughly how much time it takes to TIMEOUT a rerequest loop
 If absolutely no packets get received. Each time a successful rerequest comes through though, TIMEOUT_REREQUEST_SAFETY gets reset
 I feel 5 seconds total is generous, but for less reliable networks you might tweak these values

# Example setup:
 For a network with roughly 5 second latency between points, this might be more appropriate:
    TIMEOUT_REREQUEST_SAFETY = 10
    TIMEOUT_SYNC = 6
    TIMEOUT_RECV_LOOP = 8
    TIMEOUT_NO_WAIT = 0.05
    TIMEOUT_SEND_REREQUEST = 15
    TIMEOUT_RECV_REREQUEST = 3.5

# RC4 Twist Variant
    
    This one is a work in progress. Debug prints are still included.
    
    * Encrypted with multiple RC4 streams. Every packet is re-keyed with a random RC4 key. This key generates multiple (by default 32) additional RC4 streams. These multiple streams are randomly hopped between to encrypt a single packet.