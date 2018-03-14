from libavifile.avi import AviFile
from libavifile.decoder import DecoderBase
import libavifile.rle
import libavifile.bmp

get_decoder_for_stream = DecoderBase.for_avi_stream
