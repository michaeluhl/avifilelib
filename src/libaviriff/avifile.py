import os
from struct import unpack


class RIFFChunk(object):

    def __init__(self, chunk_type, length, offset):
        self.__type = chunk_type
        self.__length = length
        self.__offset = offset
        self.chunks = []

    @property
    def type(self):
        return self.__type

    @property
    def length(self):
        return self.__length

    @property
    def offset(self):
        return self.__offset

    @property
    def data_offset(self):
        return self.offset + 8

    @staticmethod
    def read_chunk_header(riff_file):
        offset = riff_file.tell()
        data = riff_file.read(8)
        chunk_type = data[:4].decode('ASCII')
        length = unpack('<i', data[4:])
        return offset, chunk_type, length

    @classmethod
    def parse_chunk(cls, riff_file, **kwargs):
        offset, chunk_type, length = cls.read_chunk_header(riff_file)
        chunk = None
        for scls in cls.__subclasses__():
            if hasattr(scls, 'CHUNK_TYPE') and scls.CHUNK_TYPE == chunk_type:
                chunk = scls.parse_chunk(riff_file,
                                         chunk_type=chunk_type,
                                         length=length,
                                         offset=offset)
        if not chunk:
            chunk = cls(chunk_type=chunk_type,
                        length=length,
                        offset=offset)
            riff_file.seek(length, whence=os.SEEK_CUR)
        return chunk


class RIFFList(RIFFChunk):

    CHUNK_TYPE = 'LIST'

    def __init__(self, chunk_type, length, offset, list_type):
        super(RIFFList, self).__init__(chunk_type=chunk_type,
                                       length=length,
                                       offset=offset)
        self.__list_type = list_type

    @property
    def list_type(self):
        return self.__list_type

    @classmethod
    def parse_chunk(cls, riff_file, **kwargs):
        list_type = riff_file.read(4).decode('ASCII')
        chunk = None
        for scls in cls.__subclasses__():
            if hasattr(scls, 'LIST_TYPE') and scls.LIST_TYPE == list_type:
                chunk = scls.parse_chunk(riff_file, list_type=list_type, **kwargs)
        if not chunk:
            chunk = cls(list_type=list_type, **kwargs)
            riff_file.seek(kwargs['length'] - 4, os.SEEK_CUR)
        return chunk


class AVIHeaderChunk(RIFFChunk):

    CHUNK_TYPE = 'avih'

    def __init__(self, chunk_type, length, offset):
        super(AVIHeaderChunk, self).__init__(chunk_type=chunk_type,
                                             length=length,
                                             offset=offset)
        self.headers = {}

    @classmethod
    def parse_chunk(cls, riff_file, **kwargs):


class AVIHeaderList(RIFFList):

    LIST_TYPE = 'hdrl'

    def __init__(self, chunk_type, length, offset, list_type):
        super(AVIHeaderList, self).__init__(chunk_type=chunk_type,
                                            length=length,
                                            offset=offset,
                                            list_type=list_type)
        self.avih = {}
        self.strl = []

    @classmethod
    def parse_chunk(cls, riff_file, **kwargs):
        chunk = cls(**kwargs)




class RIFFAviFile(object):

    def __init__(self, avifilename):
        self.__filename = avifilename
        self.__chunks = []
        with open(avifilename, 'rb') as avifile:
            self.__riff, self.__size, self.__type = self.__read_riff_header(avifile)
            if self.__riff != 'RIFF' or self.__type != 'AVI ':
                raise ValueError('Missing RIFF magic or non-AVI RIFF file.')

    def __parse_chuck_header(self, avifile):
        data = avifile.read(8)
        fourcc = data[:4].decode('ASCII')
        size = unpack('<i', data[4:])
        if fourcc == 'LIST':
            list_type = avifile.read(4).decode('ASCII')
        return fourcc, size

    def __read_riff_header(self, avifile):
        data = avifile.read(12)
        riff = data[:4].decode('ASCII')
        filesize = unpack('<i', data[4:8])
        filetype = data[8:].decode('ASCII')
        return riff, filesize, filetype

    def __read_list(self, avifile):
        start = avifile.tell()
        data = avifile.read(8)
        list_tag = data[:4].decode()
