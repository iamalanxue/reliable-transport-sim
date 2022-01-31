# do not import anything else from loss_socket besides LossyUDP
from lossy_socket import LossyUDP
# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY
from struct import *


class Streamer:
    def __init__(self, dst_ip, dst_port,
                 src_ip=INADDR_ANY, src_port=0):
        """Default values listen on all network interfaces, chooses a random source port,
           and does not introduce any simulated packet loss."""
        self.socket = LossyUDP()
        self.recv_buffer = {} #creating an empty dictionary 
        self.expected_sequence_number = 0
        self.socket.bind((src_ip, src_port))
        self.dst_ip = dst_ip
        self.dst_port = dst_port

    def send(self, data_bytes: bytes) -> None:
        """Note that data_bytes can be larger than one packet."""
        #links to the code i looked at the write this function 
        #https://stackoverflow.com/questions/13517246/python-sockets-sending-string-in-chunks-of-10-bytes
        #https://www.geeksforgeeks.org/break-list-chunks-size-n-python/ 
        # Your code goes here!  The code below should be changed!
        chunks = list()
        for i in range(0, len(data_bytes), 1472):
            chunk = data_bytes[i:i+1472]
            chunks.append(chunk)
        # for now I'm just sending the raw application-level data in one UDP payload
        for chunk in chunks:
            self.socket.sendto(chunk, (self.dst_ip, self.dst_port))

    def recv(self) -> bytes:
        """Blocks (waits) if no data is ready to be read from the connection."""
        # your code goes here!  The code below should be changed!
        
        # this sample code just calls the recvfrom method on the LossySocket
        data, addr = self.socket.recvfrom()
        # For now, I'll just pass the full UDP payload to the app
        unpacked = unpack('c'*len(data), data)
        sequence_number = ''
        for i in unpacked:
            sequence_number += i.decode('utf-8')
        sequence_number = int(sequence_number)
        if sequence_number not in self.recv_buffer:
            self.recv_buffer[sequence_number] = data
        # else:
        #     self.recv_buffer.update({sequence_number: data})
        if self.expected_sequence_number in self.recv_buffer:
            value = self.recv_buffer[self.expected_sequence_number]
            self.expected_sequence_number += 1
            return value
        else:
            return b''

    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
           the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.
        pass
