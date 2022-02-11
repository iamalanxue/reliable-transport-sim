# do not import anything else from loss_socket besides LossyUDP
from ssl import ALERT_DESCRIPTION_CERTIFICATE_REVOKED
from lossy_socket import LossyUDP
# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY
from struct import *
from concurrent.futures import ThreadPoolExecutor
import hashlib
import time
from threading import Timer, Lock

#interval timer 
class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


class Streamer:
    def __init__(self, dst_ip, dst_port,
                 src_ip=INADDR_ANY, src_port=0):
        """Default values listen on all network interfaces, chooses a random source port,
           and does not introduce any simulated packet loss."""
        self.socket = LossyUDP()
        self.recv_buffer = {} #creating an empty dictionary 
        self.acked = {}
        self.finack = False
        self.expected_sequence_number = 0
        self.sequence_number = 0
        self.closed = False
        self.timers = {}
        self.waiting_for_ack = {}
        self.socket.bind((src_ip, src_port))
        self.dst_ip = dst_ip
        self.dst_port = dst_port
        self.lock = Lock()
        executor = ThreadPoolExecutor(max_workers=1)
        executor.submit(self.listener)

    def listener(self):
        while not self.closed: # a later hint will explain self.closed
            try:
                data, addr = self.socket.recvfrom()
                if(len(data) > 0):
                    # Format: seq #, ack header, data)
                    unpacked = unpack('H'+'c'+'32s'+'c'*(len(data)-35), data)
                    sequence = unpacked[0]
                    packet_type = unpacked[1]
                    hash = unpacked[2]
                    packet_data = data[35:]
                    hash_check = hashlib.md5(str(sequence).encode() + packet_type + packet_data).hexdigest()
                    if hash_check.encode() == hash:
                        if packet_type == b'f': # if packet is FIN packet
                            finack_hash = hashlib.md5(str(0).encode() + b'g').hexdigest()
                            finack_seq = pack('H', 0) + pack('c', b'g') + pack('32s', finack_hash.encode())
                            self.socket.sendto(finack_seq, (self.dst_ip, self.dst_port))
                        elif packet_type == b'g': # if packet is FINACK packet
                            self.finack = True
                        elif packet_type == b'a': # if packet is ACK packet
                            self.acked[sequence] = True
                            self.timers[sequence].cancel()
                            del self.timers[sequence]
                            # print("packet " + str(sequence) + " ACKED")
                        elif packet_type == b'd': # packet is data packet
                            if sequence not in self.recv_buffer:
                                self.recv_buffer[sequence] = data[35:]
                            ack_hash = hashlib.md5(str(sequence).encode() + b'a').hexdigest()
                            ack_seq = pack('H', sequence) + pack('c', b'a') + pack('32s', ack_hash.encode())
                            self.socket.sendto(ack_seq, (self.dst_ip, self.dst_port))
                            # print("sending ACK for packet #" + str(sequence))
                    else:
                        print("Corrupted packet received")
            except Exception as e:
                print("listener died!")
                print(e)

    def send(self, data_bytes: bytes) -> None:
        """Note that data_bytes can be larger than one packet."""
        # Your code goes here!  The code below should be changed!
        with self.lock:
            chunks = list()
            for i in range(0, len(data_bytes), 1437):
                chunk = data_bytes[i:i+1437]
                chunks.append(chunk)
            for chunk in chunks:
                hash = hashlib.md5(str(self.sequence_number).encode() + b'd' + chunk).hexdigest()
                chunk = pack('H', self.sequence_number) + pack('c', b'd') + pack('32s', hash.encode()) + chunk
                while len(self.timers) > 30:
                    continue

                self.waiting_for_ack[self.sequence_number] = chunk #i need to save this chunk in case it gets lost so i can resend it using timers 
                a_timer = Timer(5, self.timer_got_timeout, [self.sequence_number])
                self.timers[self.sequence_number] = a_timer #storing my timer in a dictionary
                a_timer.start()
                self.socket.sendto(chunk, (self.dst_ip, self.dst_port)) #sending a packet for the first time 
                self.sequence_number += 1

    def timer_got_timeout(self, sequence_number):
        self.socket.sendto(self.waiting_for_ack[sequence_number], (self.dst_ip, self.dst_port))
        new_timer = Timer(5, self.timer_got_timeout, [sequence_number])
        self.timers[sequence_number] = new_timer
        new_timer.start()
        

    def recv(self) -> bytes:
        """Blocks (waits) if no data is ready to be read from the connection."""
        # your code goes here!  The code below should be changed!
        with self.lock:
            if self.expected_sequence_number in self.recv_buffer:
                value = b''
                while(self.expected_sequence_number in self.recv_buffer):
                    value += self.recv_buffer[self.expected_sequence_number]
                    self.expected_sequence_number += 1
                return value 
            else:
                return b''

    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
           the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.
        
        # I need this or else it seems the ACK wasn't actually getting sent in time before the socket closed on me
        fin_hash = hashlib.md5(str(0).encode() + b'f').hexdigest()
        fin_seq = pack('H', 0) + pack('c', b'f') + pack('32s', fin_hash.encode())
        self.socket.sendto(fin_seq, (self.dst_ip, self.dst_port))
        print("sending FIN")
        time.sleep(0.25)
        while self.finack != True:
            self.socket.sendto(fin_seq, (self.dst_ip, self.dst_port))
            print("sending FIN")
            time.sleep(0.25)
        time.sleep(2)
        self.closed = True
        self.socket.stoprecv()
        return
