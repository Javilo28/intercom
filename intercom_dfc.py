# Implementing a Data-Flow Control algorithm.

import sounddevice as sd
import numpy as np
import struct
import sys
from intercom import Intercom
from intercom_binaural import Intercom_binaural
from intercom_binaural import Intercom_binaural

class Intercom_dfc(Intercom_binaural):

    def init(self, args):
        Intercom_binaural.init(self, args)
        self.send_packet_format = f"!HBB{self.frames_per_chunk//8}B"
        self.chunks_to_buffer = args.chunks_to_buffer
        self.cells_in_buffer = self.chunks_to_buffer * 2
        self._buffer = [self.generate_zero_chunk()] * self.cells_in_buffer
        #self.number_of_packets = [self.generate_zero_chunk()] * self.cells_in_buffer
        self.current_chunk_number = 0
        self.count = 0
        
      #Si el numero de chunk que nos llega es distinto del que tenemos, es porque ya han pasado los 32 paquetes, entonces:
	  #Si es distinto chunk y ademas el cont de paquetes que llegan es menor que el numero total de paquetes (32), actualizamos
	  #el numero de paquetes a los que han llegado que los tiene el cont.
	  #Hay que hacer otro if para si ha cambiado el chunk, es decir, ya hemos terminado con esos 32 paquetes, el cont vuelva a 0 para
	  #empezar de nuevo con la siguiente tanda
        
        #self.packetCounter = [0]*self.cells_in_buffer
        self.packetCounter = [None]*self.cells_in_buffer
        for i in range(self.cells_in_buffer):
            self.packetCounter[i] = 0
        #self.receiveCount=0
        self.cuenta = -1
        self.packetReceived=16
		
    def receive_and_buffer(self):
        message, source_address = self.receiving_sock.recvfrom(Intercom.MAX_MESSAGE_SIZE)
        chunk_number,self.packetReceived, bitplane_number, *bitplane = struct.unpack(self.send_packet_format, message)
        #count empieza a 0 y a que le vamos a asignar el valor que tiene packet couynter en el chunk a reproducir
	    self.count =self.packetCounter[self.played_chunk_number % self.cells_in_buffer]		
        #aqui vamos a actualizar el packetCounter porque al pasar por aqui es que ha recibido correctamente un chunk
        self.packetCounter[self.played_chunk_number % self.cells_in_buffer] = (self.count+1)     		    
        bitplane = np.asarray(bitplane, dtype=np.uint8)
        bitplane = np.unpackbits(bitplane)
        bitplane = bitplane.astype(np.int16)
        self._buffer[chunk_number % self.cells_in_buffer][:, bitplane_number%self.number_of_channels] |= (bitplane << bitplane_number//self.number_of_channels)
        return chunk_number
		
    def record_and_send(self, indata):
        #print(indata)
        indata = self.tc2sm(indata)     
        #print(indata)
        self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER
		#self.receiveCount = self.packetCounter[self.recorded_chunk_number % self.cells_in_buffer]
        self.cuenta=self.number_of_channels*16 - self.packetReceived - 1
        if self.cuenta < -1:
            self.cuenta=-1
        #print(self.cuenta)
        for bitplane_number in range(self.number_of_channels*16-1, self.cuenta, -1):
            bitplane = (indata[:, bitplane_number%self.number_of_channels] >> bitplane_number//self.number_of_channels) & 1
            bitplane = bitplane.astype(np.uint8)
            bitplane = np.packbits(bitplane)
            message = struct.pack(self.send_packet_format,self.recorded_chunk_number,self.packetCounter[self.played_chunk_number], bitplane_number, *bitplane)                
            self.sending_sock.sendto(message, (self.destination_IP_addr, self.destination_port))      
					
    def record_send_and_play_stereo(self, indata, outdata, frames, time, status):
        indata[:,0] -= indata[:,1]
        self.record_and_send(indata)
        self._buffer[self.played_chunk_number % self.cells_in_buffer][:,0] += self._buffer[self.played_chunk_number % self.cells_in_buffer][:,1]
        self.play(outdata)
      
    def play(self, outdata):
        chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
        self._buffer[self.played_chunk_number % self.cells_in_buffer] = self.generate_zero_chunk()
        aelf.played_chunk_number = (self.played_chunk_number + 1) % self.cells_in_buffer              
        chunk = self.sm2tc(chunk)        
        outdata[:] = chunk
        if __debug__:
            sys.stderr.write("."); sys.stderr.flush()
            
        #el valor absoluto lo que hace es poner el numero positivo, por ejemplo si x es -39, con el abs tendremos x = 39, eso en binario quiere decir cambiar el bit mas 
        #significativo de 1 a 0, mientras que si es 0 porque x fuera positivo, no cambiaria nada.           
        #por otra parte, a la izquierda de la or, hacemos una and entre x y 0x80000 para obtener el signo de x ya que 0x8000 = 1000000000 y el resultado de la and va a ser todo 0
        #menos el bit mas significativo que es justo el que nos da el signo, por tanto al hacer la or final entre la parte izq y derecha haremos que le ponga el signo negativo
        #si es que lo tenia al numero iniciar, por tanto hariamos -1 OR 39 que daria -39.
        
    def tc2sm(self, x):
        return ((x & 0x8000) | abs(x)).astype(np.int16)
    
    #la m sirve para si el numero es negativo, que m valga todo 1 ya que metera 1 por la izq y si el numero es positivo que m sea 0 ya que metera 0 por la izquierda,
    #entonces si el numero es positivo, como m vale 0, la parte derecha de la OR sera 0 ya que hace una AND con m, y en la parte izq de la OR se hara una AND entre el numero
    #que tenemos, x, y el complemento a 1 de la m que como es 0 porque x es positivo, el complemento vale todo 1 y por tanto AND con 1 la x se queda igual, basicamente que si
    #x es positivo, x se queda igual, no se hace nada
    
    #ahora si x es negativo, pasa justo al reves, ya que m es todo 1 porque mete 1 por la izq y el complemento a 1 de m sera todo 0, por tanto la parte izq de la OR no sirve de nada
    #porque es una AND con 0. Solo nos quedamos con la parte derecha de la OR, que lo que se hace es en la AND de x con 0x8000 obtenemos el signo de X, ya que 0x8000 = 1000000
    #y a eso le restamos X para obtener el complemento a 2, la AND con la m en este caso no sirve para nada porque m es todo 1, esa AND vale como hemos dicho, para cuando x es positivo
    #que m=0 y la parte derecha de la OR no se haga.
    
    def sm2tc(self, x):
        m = x >> 15
        return (~m & x) | (((x & 0x8000) - x) & m).astype(np.int16)
if __name__ == "__main__":
    intercom = Intercom_dfc()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
