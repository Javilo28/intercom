from intercom import Intercom
import sounddevice as sd  # https://python-sounddevice.readthedocs.io
import numpy  # https://numpy.org/
import argparse  # https://docs.python.org/3/library/argparse.html
import socket  # https://docs.python.org/3/library/socket.html
import queue  # https://docs.python.org/3/library/queue.html
import struct

if __debug__:
    import sys
class Intercom_buffer(Intercom):
    size_buffer = 4
    number_of_chunks = 0

    def init(self, args):
        Intercom.init(self, args)

    def run(self):
        # SOCK_DGRAM quiere decir que usaremos UDP ya que no necesitamos esperar respuesta de que ha recibido el
        # mensaje el receptor. AF_INET quiere decir que usaremos ese tipo de comunicacion ya que es mas sencilla.
        sending_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiving_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Indicamos en que puertos vamos a escuchar, con 0.0.0.0 decimos que escucharemos en todos los puertos
        # Y el puerto que estemos utilizando en cada momento, se lo asignamos a self.listening_port, que es
        # nuestro puerto por el que escuchamos. En cada momento, escuchamos por 1 solo puerto (listening_port)
        # Y hay que asignarselo a esa variable. Basicamente decimos que podemos escuchar por cualquier puerto.
        listening_endpoint = ("0.0.0.0", self.listening_port)

        # Asociamos el socket al host y puerto de la variable listening_endpoint.
        receiving_sock.bind(listening_endpoint)
        mychar = numpy.zeros(
            (self.samples_per_chunk, self.number_of_channels),
            self.dtype)
        lista = [mychar] * self.size_buffer

        def receive_and_buffer():
            # El metodo recvfrom devuelve un par del tipo: string, direccion, donde string contiene los datos
            # que el receiving_sock (el socket receptor) recibe, y direccion contiene la direccion del socket
            # emisor, es decir, quien le ha enviado esos datos.
            # Estos dos valores, los almacena en message y source_address respectivamente.
            # Esto lo va a hacer con todo el paquete, es decir, hasta llegar al max packet size.
            # Cada vez que ejecuta el metodo y obtiene un mensaje, lo mete en la cola.
            # lista[modulo]=[message]

            # OBTIENE EL MENSAJE QUE LE LLEGA, COGE SU CHUNK Y HACE MODULO TAMAÑO DE BUFER, EL RESULTADO ES LA POSICION
            # DEL BUFER, ES DECIR, DE LA LISTA, DONDE SE VA A INSERTAR ESE MENSAJE

            # unpack
            message, source_address = receiving_sock.recvfrom(
                Intercom.max_packet_size)

            *packet, chunks = struct.unpack('2048hh', message)
            # print(*packet)
            posWithModule = chunks % self.size_buffer
            lista[posWithModule] = packet
            #print(lista)

        def record_send_and_play(indata, outdata, frames, time, status):
            # Envia los datos de entrada a la direccion de destino y el puerto de destino

            # if self.number_of_chunks==15:
            # self.number_of_chunks=0
            self.number_of_chunks = (self.number_of_chunks + 1) % self.size_buffer
            data = numpy.frombuffer(
                indata,
                numpy.int16)
            message = struct.pack('2048hh', *data, self.number_of_chunks)

            # CAMBIAR
            # pack struct
            sending_sock.sendto(
                message,
                (self.destination_IP_addr, self.destination_port))
            # message = lista[self.number_of_chunks]
            # En primer lugar, creamos el array outdata, y lo igualamos a numpy.frombuffer, este metodo crea un
            # array pasandole un bufer, en este caso, el message, a ese array nuevo, le hacemos reshape para
            # cambiarle la forma en la que se muestre el array, diciendole el numero de filas y columnas que
            # vienen dados por samples_per_chunk y number_of_channels respectivamente.
            outdata[:] = numpy.frombuffer(
                indata,
                numpy.int16).reshape(
                self.samples_per_chunk, self.number_of_channels)

            # Escribimos puntos cada vez que detecte el sonido, con flush, obligamos a mostrar todos los datos
            # del bufer
            if __debug__:
                sys.stderr.write(".");
                sys.stderr.flush()

        with sd.Stream(
                samplerate=self.samples_per_second,
                blocksize=self.samples_per_chunk,
                dtype=self.dtype,
                channels=self.number_of_channels,
                callback=record_send_and_play):
            print('-=- Press <CTRL> + <C> to quit -=-')
            while True:
                receive_and_buffer()

if __name__ == "__main__":
    intercom = Intercom_buffer()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
