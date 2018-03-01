from chunk import Chunk
from contextlib import closing
from enum import Enum
import numpy as np
from pprint import pprint
from struct import unpack
import os


AVI_HEADERS = [
    'MicroSecPerFrame',
    'MaxBytesPerSec',
    'PaddingGranularity',
    'Flags',
    'TotalFrames',
    'InitialFrames',
    'Streams',
    'SuggestedBufferSize',
    'Width',
    'Height'
]

STREAM_HEADERS = [
    'FccType',
    'FccHandler',
    'Flags',
    'Priority',
    'Language',
    'InitialFrames',
    'Scale',
    'Rate',
    'Start',
    'Length',
    'SuggestedBufferSize',
    'Quality',
    'SampleSize'
]

STREAM_HEADER_FCC_TYPES = [
    'auds',
    'mids',
    'txts',
    'vids'
]

BITMAP_INFO_HEADERS = [
    'Size',
    'Width',
    'Height',
    'Planes',
    'BitCount',
    'Compression',
    'SizeImage',
    'XPelsPerMeter',
    'YPelsPerMeter',
    'ClrUsed',
    'ClrImportant'
]

class BI_COMPRESSION(Enum):
    BI_RGB = 0x0000
    BI_RLE8 = 0x0001
    BI_RLE4 = 0x0002
    BI_BITFIELDS = 0x0003
    BI_JPEG = 0x0004
    BI_PNG = 0x0005
    BI_CMYK = 0x000B
    BI_CMYKRLE8 = 0x000C
    BI_CMYKREL4 = 0x000D


class RIFFChunk(Chunk):

    def __init__(self, file, align=False, bigendian=False, inclheader=False):
        super(RIFFChunk, self).__init__(file=file,
                                        align=align,
                                        bigendian=bigendian,
                                        inclheader=inclheader)
        self.__list_type = None
        if self.getname() == b'LIST':
            self.__list_type = self.read(4).decode('ASCII')

    def islist(self):
        return self.__list_type is not None

    def getlisttype(self):
        return self.__list_type


class AVIFile(object):

    def __init__(self, file_or_filename):
        self.__file = file_or_filename
        if not hasattr(self.__file, 'read'):
            self.__file = open(file_or_filename, 'rb')
        if self.__file.read(4).decode('ASCII') != 'RIFF':
            raise ValueError('Non-RIFF file detected.')
        self.length = unpack('<i', self.__file.read(4))[0]
        if self.__file.read(4).decode('ASCII') != 'AVI ':
            raise ValueError('Non-AVI file detected.')
        hdrl = RIFFChunk(self.__file)
        self.avih = self.__parse_avih(hdrl)
        self.strl = []
        while hdrl.tell() < hdrl.getsize():
            self.strl.append(self.__parse_strl(hdrl))
        self.__file.close()

    def __parse_avih(self, hdrl):
        avih_chunk = RIFFChunk(hdrl)
        avih_values = unpack('14I', avih_chunk.read(56))
        avih = {k: v for k, v in zip(AVI_HEADERS, avih_values[:10])}
        avih['Reserved'] = avih_values[10:]
        avih_chunk.close()
        return avih

    def __parse_strl(self, hdrl):
        strl_chunk = RIFFChunk(hdrl)
        strl = {}
        with closing(RIFFChunk(strl_chunk)) as strh_chunk:
            strl['strh'] = self.parse_strh(strh_chunk)
        with closing(RIFFChunk(strl_chunk)) as strf_chunk:
            strl['strf'] = self.parse_strf(strf_chunk, strl['strh'])
        try:
            with closing(RIFFChunk(strl_chunk)) as strd_chunk:
                strl['strd'] = self.parse_strd(strd_chunk, strl['strh'], strl['strf'])
        except Exception:
            pass
        try:
            with closing(RIFFChunk(strl_chunk)) as strn_chunk:
                strl['strn'] = self.parse_strn(strn_chunk)
        except Exception:
            pass
        strl_chunk.close()
        return strl

    def parse_strh(self, strh_chunk):
        strh_values = unpack('<4s4sI2H8I4h', strh_chunk.read())
        strh = {k: v for k, v in zip(STREAM_HEADERS, strh_values[:-4])}
        strh['Frame'] = strh_values[-4:]
        return strh

    def parse_strf(self, strf_chunk, strh):
        if strh['FccType'] == b'vids':
            strf_values = unpack('<I2i2H2I2i2I', strf_chunk.read(40))
            strf = {k: v for k, v in zip(BITMAP_INFO_HEADERS, strf_values)}
            strf['ColorTable'] = self.read_colortable(strf_chunk, strf)
            return strf
        return strf_chunk.read()

    def read_colortable(self, strf_chunk, strf):
        clr_ct = strf['ClrUsed']
        clr_size = clr_ct*4
        rem_size = strf_chunk.getsize() - strf_chunk.tell()
        if clr_ct > 0 and rem_size >= clr_size:
            colors = unpack('<{}B'.format(4*clr_ct), strf_chunk.read(clr_size))
            colors = [list(reversed(colors[i:i+3])) for i in range(0, len(colors), 4)]
            return colors
        return []

    def parse_strd(self, strd_chunk, strh, strf):
        return strd_chunk.read()

    def parse_strn(self, strn_chunk):
        return strn_chunk.read().decode('ASCII')
