# Using the Discrete Wavelet Transform, convert the chunks of samples
# intro chunks of Wavelet coefficients (coeffs).
#
# The coefficients require more bitplanes than the original samples,
# but most of the energy of the samples of the original chunk tends to
# be into a small number of coefficients that are localized, usually
# in the low-frequency subbands:
#
# (supposing a chunk with 1024 samples)
#
# Amplitude
#     |       +                      *
#     |   *     *                  *
#     | *        *                *
#     |*          *             *
#     |             *       *
#     |                 *
#     +------------------------------- Time
#     0                  ^        1023 
#                |       |       
#               DWT  Inverse DWT 
#                |       |
#                v
# Amplitude
#     |*
#     |
#     | *
#     |  **
#     |    ****
#     |        *******
#     |               *****************
#     +++-+---+------+----------------+ Frequency
#     0                            1023
#     ^^ ^  ^     ^           ^
#     || |  |     |           |
#     || |  |     |           +--- Subband H1 (16N coeffs)
#     || |  |     +--------------- Subband H2 (8N coeffs)
#     || |  +--------------------- Subband H3 (4N coeffs)
#     || +------------------------ Subband H4 (2N coeffs)
#     |+-------------------------- Subband H5 (N coeffs)
#     +--------------------------- Subband L5 (N coeffs)
#
# (each channel must be transformed independently)
#
# This means that the most-significant bitplanes, for most chunks
# (this depends on the content of the chunk), should have only bits
# different of 0 in the coeffs that belongs to the low-frequency
# subbands. This will be exploited in a future issue.
#
# The straighforward implementation of this issue is to transform each
# chun without considering the samples of adjacent
# chunks. Unfortunately this produces an error in the computation of
# the coeffs that are at the beginning and the end of each subband. To
# compute these coeffs correctly, the samples of the adjacent chunks
# i-1 and i+1 should be used when the chunk i is transformed:
#
#   chunk i-1     chunk i     chunk i+1
# +------------+------------+------------+
# |          OO|OOOOOOOOOOOO|OO          |
# +------------+------------+------------+
#
# O = sample
#
# (In this example, only 2 samples are required from adajact chunks)
#
# The number of ajacent samples depends on the Wavelet
# transform. However, considering that usually a chunk has a number of
# samples larger than the number of coefficients of the Wavelet
# filters, we don't need to be aware of this detail if we work with
# chunks.

import struct
import numpy as np
import math
from intercom import Intercom
from intercom_empty import Intercom_empty
import matplotlib.pyplot as plt
import numpy as np
import pywt as wt



# Number of levels of the DWT
levels = 4
# Wavelet used
wavelet = 'bior3.5'
padding = "periodization"

# Get the number of wavelet coefficients to get the number of samples
#shapes = wt.wavedecn_shapes((samples,), wavelet)

if __debug__:
    import sys

class Intercom_DWT(Intercom_empty):

    def init(self, args):
        Intercom_empty.init(self, args)
        zeros = np.zeros(self.frames_per_chunk)
        
        coeffs = wt.wavedec(zeros, wavelet=wavelet, level=levels, mode=padding)
        
        arr,self.coeffs_slices = wt.coeffs_to_array(coeffs)
        
        
    def send(self,indata):
        #el canal derecho no hace falta transformarlo
        canal_L=indata[:,0]
        coeffs=wt.wavedec(canal_L, wavelet=wavelet, level=levels, mode=padding)
        arr, self.coeffs_slices = wt.coeffs_to_array(coeffs)
        arr=arr.astype(np.int16)
        indata[:,0]=arr
        Intercom_empty.send(self,indata)      
       

    def play(self, outdata):
        chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
        self._buffer[self.played_chunk_number % self.cells_in_buffer] = self.generate_zero_chunk()
        self.played_chunk_number = (self.played_chunk_number + 1) % self.cells_in_buffer
        #chunk = np.asarray(chunk, dtype=np.float64)
        canal_L=chunk[:,0]
        coeffs_from_arr = wt.array_to_coeffs(canal_L,self.coeffs_slices, output_format="wavedec")
        print(coeffs_from_arr[4].shape)
        self.samples = wt.waverec(coeffs_from_arr, wavelet=wavelet, mode=padding)
        #self.samples=np.asarray(self.samples,dtype=np.int16)
        chunk[:,0]=self.samples
        outdata[:] = chunk
        if __debug__:
            self.feedback()
                                 
                                      
    


if __name__ == "__main__":
    intercom = Intercom_DWT()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
