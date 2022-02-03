# do not import anything else from loss_socket besides LossyUDP
from ssl import ALERT_DESCRIPTION_CERTIFICATE_REVOKED
from lossy_socket import LossyUDP
# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY
from struct import *
from concurrent.futures import ThreadPoolExecutor
import time

class Streamer:
    def __init__(self, dst_ip, dst_port,
                 src_ip=INADDR_ANY, src_port=0):
        """Default values listen on all network interfaces, chooses a random source port,
           and does not introduce any simulated packet loss."""
        self.socket = LossyUDP()
        self.recv_buffer = {} #creating an empty dictionary 
        self.acked = {}
        self.expected_sequence_number = 0
        self.sequence_number = 0
        self.closed = False
        self.socket.bind((src_ip, src_port))
        self.dst_ip = dst_ip
        self.dst_port = dst_port
        executor = ThreadPoolExecutor(max_workers=1)
        executor.submit(self.listener)

    def listener(self):
        while not self.closed: # a later hint will explain self.closed
            try:
                data, addr = self.socket.recvfrom()
                if(data != b''):
                    # Format: seq #, ack header, data)
                    unpacked = unpack('H'+'c'+'c'*(len(data)-3), data)
                    print(unpacked)
                    sequence = unpacked[0]
                    type = unpacked[1]
                    if type == b'a': # if packet is ACK packet
                        print("packet " + str(sequence) + " ACKED")
                        self.acked[sequence] = True
                    else: # packet is data packet
                        if sequence not in self.recv_buffer:
                            self.recv_buffer[sequence] = data[3:]
                            ack_seq = pack('H', sequence) + pack('c', b'a')
                            print("sending ACK for packet #" + str(sequence))
                            self.socket.sendto(ack_seq, (self.dst_ip, self.dst_port))
            except Exception as e:
                print("listener died!")
                print(e)

    def send(self, data_bytes: bytes) -> None:
        """Note that data_bytes can be larger than one packet."""
        #links to the code i looked at the write this function 
        #https://stackoverflow.com/questions/13517246/python-sockets-sending-string-in-chunks-of-10-bytes
        #https://www.geeksforgeeks.org/break-list-chunks-size-n-python/ 
        # Your code goes here!  The code below should be changed!
        chunks = list()
        for i in range(0, len(data_bytes), 1469):
            chunk = data_bytes[i:i+1469]
            chunks.append(chunk)
        # for now I'm just sending the raw application-level data in one UDP payload
        print("number of chunks in this transmission:" + str(len(chunks)))
        for chunk in chunks:
            print("sending packet #" + str(self.sequence_number))
            chunk = pack('H', self.sequence_number) + pack('c', b'd') + chunk
            self.socket.sendto(chunk, (self.dst_ip, self.dst_port))
            while self.sequence_number not in self.acked.keys(): time.sleep(0.01)
            self.sequence_number += 1

    def recv(self) -> bytes:
        """Blocks (waits) if no data is ready to be read from the connection."""
        # your code goes here!  The code below should be changed!
        # data, addr = self.socket.recvfrom()
        # unpacked = unpack('H'+'c'*(len(data)-2), data)
        # sequence = unpacked[0]
        # if sequence not in self.recv_buffer:
        #     self.recv_buffer[sequence] = data[2:]

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
        self.closed = True
        self.socket.stoprecv()
        return
