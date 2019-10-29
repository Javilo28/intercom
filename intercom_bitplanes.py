# Adding a buffer.

import sounddevice as sd
import numpy as np
import struct
from intercom_buffer import Intercom_buffer

if __debug__:
    import sys

class Intercom_bitplanes(Intercom_buffer):

    def init(self, args):
        Intercom_buffer.init(self, args)
		
    
        def run(self):

            self.recorded_chunk_number = 0
            self.played_chunk_number = 0

            def receive_and_buffer():
                message, source_address = self.receiving_sock.recvfrom(Intercom.MAX_MESSAGE_SIZE)
                chunk_number,j,i,*(bitplane) = struct.unpack(self.packet_format, message)
				#hay que hacer lo mismo pero aladiendo la columna, le haces la or y lo desplazas para colocar bien la co.lumna mas significativa
				#en vez de hacerlo una vez lo hacemos como tantas columnas y canales haya, por ejemplo si tenemos 16 cols por cada canal habra que hacer una or de las 16(que viene 
				#en j) y juntarlo en un paquete, y se realiza el proceso tantas veces como canales
                bitplane8 = np.asarray(bitplane, dtype = np.uint8)    #Pasamos a int8
                bitplane_unpack = np.unpackbits(bitplane8)          #Descompactamos
                bitplane16 = bitplaneunpack.astype(np.int16) 		#conversion final para su interpretacion, antes no hace falta con 16.
                self._buffer[chunk_number % self.cells_in_buffer][:,i] |= (bitplane16 << j)
				#Guardamos mediante una operacion or el plano de bits en una posicion del buger y canal.
                #self._buffer[chunk_number % self.cells_in_buffer] = np.asarray(chunk).reshape(self.frames_per_chunk, self.number_of_channels)
                return chunk_number

            def record_send_and_play(indata, outdata, frames, time, status):
                for j in range(15,-1,-1):
				#obtienes el indice de la columna
                    bit_desp = (indata & (1 << j)) >> j
				#para cada canal en esa posicion j, en el plano que tengo calculado bitDesp metemos todas las columnas de esa posi j
				#de cada canal, es decir, si tengo el plano 15, para cada canal en la pos 15 metemos el indata en esa columna 15
                    for i in range(self.number_of_channels): 
                        column_array_channel = bit_desp[:,i]
                        #print(column_array_channel)
                        int8=column_array_channel.astype(np.uint8) #convertimos el canal a un entero de 8 bits
                        channelpack8=np.packbits(int8)  #Se compacta
                        message = struct.pack(self.packet_format, self.recorded_chunk_number, j, i, *(channelpack8))
                        self.sending_sock.sendto(message, (self.destination_IP_addr, self.destination_port))
                
                self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER
                #print(indata)
                chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
                self._buffer[self.played_chunk_number % self.cells_in_buffer] = self.generate_zero_chunk()
                self.played_chunk_number = (self.played_chunk_number + 1) % self.cells_in_buffer
                outdata[:] = chunk
                if __debug__:
                   sys.stderr.write("."); sys.stderr.flush()

                with sd.Stream(samplerate=self.frames_per_second, blocksize=self.frames_per_chunk, dtype=np.int16, channels=self.number_of_channels, callback=record_send_and_play):
                   print("-=- Press CTRL + c to quit -=-")
                first_received_chunk_number = receive_and_buffer()
                self.played_chunk_number = (first_received_chunk_number - self.chunks_to_buffer) % self.cells_in_buffer
                while True:
                   receive_and_buffer()

if __name__ == "__main__":
    intercom = Intercom_bitplanes()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
