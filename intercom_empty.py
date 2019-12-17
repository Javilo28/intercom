# Don't send empty bitplanes.
#
# The sender adds to the number of received bitplanes the number of
# skipped (zero) bitplanes of the chunk sent.

# The receiver computes the first received
# bitplane (apart from the bitplane with the signs) and report a
# number of bitplanes received equal to the real number of received
# bitplanes plus the number of skipped bitplanes.

import struct
import numpy as np
from intercom import Intercom
from intercom_dfc import Intercom_DFC

if __debug__:
    import sys

class Intercom_empty(Intercom_DFC):

    def init(self, args):
        Intercom_DFC.init(self, args)
        self.countlist=[0]*self.cells_in_buffer
        self.aux=0
        
    def receive_and_buffer(self):
        message, source_address = self.receiving_sock.recvfrom(Intercom.MAX_MESSAGE_SIZE)
        received_chunk_number, received_bitplane_number, self.NORB, *bitplane = struct.unpack(self.packet_format, message)
        bitplane = np.asarray(bitplane, dtype=np.uint8)
        bitplane = np.unpackbits(bitplane)
        bitplane = bitplane.astype(np.uint16)
        self._buffer[received_chunk_number % self.cells_in_buffer][:, received_bitplane_number%self.number_of_channels] |= (bitplane << received_bitplane_number//self.number_of_channels)
        self.received_bitplanes_per_chunk[received_chunk_number % self.cells_in_buffer] += 1
        return received_chunk_number
    

    def send(self, indata):
        signs = indata & 0x8000
        magnitudes = abs(indata)
        indata = signs | magnitudes
        
        self.NOBPTS = int(0.75*self.NOBPTS + 0.25*self.NORB)
        self.NOBPTS += 1
        if self.NOBPTS > self.max_NOBPTS:
            self.NOBPTS = self.max_NOBPTS
        self.aux=self.countlist[self.played_chunk_number%self.cells_in_buffer]
        last_BPTS = self.max_NOBPTS - self.NOBPTS - 1 + self.aux
        print(last_BPTS)
        self.send_bitplane(indata, self.max_NOBPTS-1)
        self.send_bitplane(indata, self.max_NOBPTS-2)
        for bitplane_number in range(self.max_NOBPTS-3, last_BPTS, -1):        
            if np.any(indata)==True:
               self.send_bitplane(indata, bitplane_number)
            else:  
                self.countlist[self.played_chunk_number%self.cells_in_buffer]+=1
                              
        self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER

if __name__ == "__main__":
    intercom = Intercom_empty()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
