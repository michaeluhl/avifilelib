from chunk import Chunk
from contextlib import closing, contextmanager
from enum import Enum
import numpy as np
from struct import unpack


try:
    from enum import IntFlag
except ImportError:
    from aenum import IntFlag


class BI_COMPRESSION(IntFlag):
    BI_RGB = 0x0000
    BI_RLE8 = 0x0001
    BI_RLE4 = 0x0002
    BI_BITFIELDS = 0x0003
    BI_JPEG = 0x0004
    BI_PNG = 0x0005
    BI_CMYK = 0x000B
    BI_CMYKRLE8 = 0x000C
    BI_CMYKREL4 = 0x000D


class AVIF(IntFlag):
    HASINDEX = 0x00000010
    MUSTUSEINDEX = 0x00000020
    ISINTERLEAVED = 0x00000100
    WASCAPTUREFILE = 0x00010000
    COPYRIGHTED = 0x00020000


class AVIIF(IntFlag):
    LIST = 0x00000001
    KEYFRAME = 0x00000010
    NO_TIME = 0x00000100


class FCC_TYPE(Enum):
    AUDIO = 'auds'
    MIDI = 'mids'
    TEXT = 'txts'
    VIDEO = 'vids'


class ChunkTypeException(Exception):
    pass


class ChunkFormatException(Exception):
    pass


@contextmanager
def rollback(file_like, reraise=False):
    posn = file_like.tell()
    try:
        yield file_like
    except ChunkTypeException:
        file_like.seek(posn)
        if reraise:
            raise


class AviFileHeader(object):
    
    def __init__(self, micro_sec_per_frame, max_bytes_per_sec,
                 padding_granularity, flags, total_frames,
                 initial_frames, streams, suggested_buffer_size,
                 width, height, reserved):
        self.micro_sec_per_frame = micro_sec_per_frame
        self.max_bytes_per_sec = max_bytes_per_sec
        self.padding_granularity = padding_granularity
        self.flags = AVIF(flags)
        self.total_frames = total_frames
        self.initial_frames = initial_frames
        self.streams = streams
        self.suggested_buffer_size = suggested_buffer_size
        self.width = width
        self.height = height
        self.reserved = reserved

    @classmethod
    def from_chunk(cls, parent_chunk):
        with closing(RIFFChunk(parent_chunk)) as avih_chunk:
            avih_values = unpack('14I', avih_chunk.read(56))
            return cls(*avih_values[:10], avih_values[10:])


class AviStreamDefinition(object):

    def __init__(self, stream_id, stream_header, stream_format,
                 stream_data=None, stream_name=None):
        self.steam_id = stream_id
        self.stream_header = stream_header
        self.stream_format = stream_format
        self.stream_data = stream_data
        self.stream_name = stream_name

    @property
    def strh(self):
        return self.stream_header

    @property
    def strf(self):
        return self.stream_format

    @property
    def strd(self):
        return self.stream_data

    @property
    def strn(self):
        return self.stream_name

    @classmethod
    def from_chunk(cls, stream_id, parent_chunk):
        with closing(RIFFChunk(parent_chunk)) as strl_chunk:
            strh = AviStreamHeader.from_chunk(strl_chunk)
            strf = AviStreamFormat.from_chunk(stream_header=strh,
                                              parent_chunk=strl_chunk)
            strd = None
            strn = None
            try:
                with rollback(strl_chunk):
                    strd = AviStreamData.from_chunk(parent_chunk=strl_chunk)
                with rollback(strl_chunk):
                    strn = AviStreamName.from_chunk(parent_chunk=strl_chunk)
            except EOFError:
                pass
            return cls(stream_id=stream_id, stream_header=strh, stream_format=strf, stream_data=strd, stream_name=strn)


class AviStreamHeader(object):
    
    def __init__(self, fcc_type, fcc_handler, flags,
                 priority, language, initial_frames,
                 scale, rate, start, length,
                 suggested_buffer_size, quality,
                 sample_size, frame):
        self.fcc_type = FCC_TYPE(fcc_type.decode('ASCII'))
        self.fcc_handler = fcc_handler
        self.flags = flags
        self.priority = priority
        self.language = language
        self.initial_frames  = initial_frames 
        self.scale = scale
        self.rate = rate
        self.start = start
        self.length = length
        self.suggested_buffer_size = suggested_buffer_size
        self.quality = quality
        self.sample_size = sample_size
        self.frame = frame

    @classmethod
    def from_chunk(cls, parent_chunk):
        with closing(RIFFChunk(parent_chunk)) as strh_chunk:
            strh_values = unpack('<4s4sI2H8I4h', strh_chunk.read())
            return cls(*strh_values[:-4], strh_values[-4:])


class AviStreamFormat(object):

    @classmethod
    def from_chunk(cls, stream_header, parent_chunk):
        for scls in cls.__subclasses__():
            if getattr(scls, 'FCC_TYPE', None) == stream_header.fcc_type:
                return scls.from_chunk(stream_header, parent_chunk)
        return UnparsedStreamFormat.from_chunk(stream_header, parent_chunk)


class UnparsedStreamFormat(AviStreamFormat):

    def __init__(self, raw_bytes):
        self.raw_bytes = raw_bytes

    @classmethod
    def from_chunk(cls, stream_header, parent_chunk):
        with closing(RIFFChunk(parent_chunk)) as strf_chunk:
            return cls(strf_chunk.read())


class BitmapInfoHeaders(AviStreamFormat):
    
    FCC_TYPE = FCC_TYPE.VIDEO
    
    def __init__(self, size, width, height, planes, 
                 bit_count, compression, size_image, 
                 x_pels_per_meter, y_pels_per_meter, 
                 clr_used, clr_important):
        self.size = size
        self.width = width
        self.height = height
        self.planes = planes
        self.bit_count = bit_count
        self.compression = BI_COMPRESSION(compression)
        self.size_image = size_image
        self.x_pels_per_meter = x_pels_per_meter
        self.y_pels_per_meter = y_pels_per_meter
        self.clr_used = clr_used
        self.clr_important = clr_important
        self.color_table = None

    @classmethod
    def from_chunk(cls, stream_header, parent_chunk):
        with closing(RIFFChunk(parent_chunk)) as strf_chunk:
            strf = cls(*unpack('<I2i2H2I2i2I', strf_chunk.read(40)))
            strf.read_colortable(strf_chunk)
            return strf

    def read_colortable(self, chunk):
        clr_size = 4*self.clr_used
        rem_size = chunk.getsize() - chunk.tell()
        if self.clr_used > 0 and rem_size >= clr_size:
            colors = unpack('<{}B'.format(clr_size),
                            chunk.read(clr_size))
            colors = np.array([list(reversed(colors[i:i+3])) for i in range(0, len(colors), 4)], dtype='B')
            return colors
        return []


class AviStreamData(object):

    def __init__(self, raw_bytes):
        self.raw_bytes = raw_bytes

    @classmethod
    def from_chunk(cls, parent_chunk):
        with closing(RIFFChunk(parent_chunk)) as strd_chunk:
            if strd_chunk.getname() == b'strd':
                return cls(strd_chunk.read())
            raise ChunkTypeException()


class AviStreamName(object):

    def __init__(self, name):
        self.name = name

    @classmethod
    def from_chunk(cls, parent_chunk):
        with closing(RIFFChunk(parent_chunk)) as strn_chunk:
            if strn_chunk.getname() == b'strn':
                raw_bytes = strn_chunk.read()
                name = raw_bytes[:raw_bytes.index(b'\0')].decode('ASCII')
                return cls(name=name)
            raise ChunkTypeException()


class AviStreamChunk(object):

    DATA_TYPES = ('db', 'dc', 'pc', 'wb')

    def __init__(self, stream_id, data_type, base_file, absolute_offset, size, flags=0):
        self.stream_id = stream_id
        self.data_type = data_type
        self.base_file = base_file
        self.absolute_offset = absolute_offset
        self.size = size
        self.size_read = 0
        self.__flags = AVIIF(flags)

    @property
    def flags(self):
        return self.__flags

    @flags.setter
    def flags(self, flags):
        self.__flags = AVIIF(flags)

    def read(self, size=-1):
        if self.base_file.closed:
            raise ValueError("I/O operation on closed file")
        if self.size_read >= self.size:
            return b''
        if size < 0:
            size = self.size - self.size_read
        if size > self.size - self.size_read:
            size = self.size - self.size_read
        data = self.base_file.read(size)
        self.size_read = self.size_read + len(data)
        return data

    def seek(self, pos, whence=0):
        if self.base_file.closed:
            raise ValueError("I/O operation on closed file")
        if whence == 1:
            pos = pos + self.size_read
        elif whence == 2:
            pos = pos + self.size
        if pos < 0 or pos > self.size:
            raise RuntimeError
        self.base_file.seek(self.absolute_offset + pos, 0)
        self.size_read = pos

    def tell(self):
        if self.base_file.closed:
            raise ValueError("I/O operation on closed file")
        return self.size_read

    @classmethod
    def from_chunk(cls, parent_chunk):
        with closing(RIFFChunk(parent_chunk)) as strm_chunk:
            chunk_id = strm_chunk.getname().decode('ASCII')
            try:
                stream_id = int(chunk_id[:2])
                data_type = chunk_id[2:]
                if data_type not in cls.DATA_TYPES:
                    raise KeyError()
            except ValueError:
                raise ChunkFormatException('Could not decode stream index: {}'.format(chunk_id[:2]))
            except KeyError:
                raise ChunkFormatException('Could not determine stream data type: {}'.format(chunk_id[2:]))
            base_file = parent_chunk
            while isinstance(base_file, RIFFChunk):
                base_file = base_file.file
            absolute_offset = base_file.tell()
            size = strm_chunk.getsize()
            return cls(stream_id=stream_id,
                       data_type=data_type,
                       base_file=base_file,
                       absolute_offset=absolute_offset,
                       size=size)


class AviRecList(object):

    def __init__(self, data_chunks=None):
        self.data_chunks = data_chunks if data_chunks else []

    @classmethod
    def from_chunk(cls, parent_chunk):
        with closing(RIFFChunk(parent_chunk)) as rec_list:
            if not rec_list.islist() or rec_list.getname() != b'rec ':
                raise ChunkTypeException()
            data_chunks = []
            while rec_list.tell() < rec_list.getsize() - 1:
                data_chunks.append(AviStreamChunk.from_chunk(rec_list))
            return cls(data_chunks=data_chunks)


class AviMoviList(object):

    def __init__(self, data_chunks=None):
        self.data_chunks = data_chunks if data_chunks else []
        self.streams = {}
        for chunk in self.data_chunks:
            self.streams.setdefault(chunk.stream_id, []).append(chunk)

    @classmethod
    def from_file(cls, file):
        with closing(RIFFChunk(file=file)) as movi_list:
            if not movi_list.islist() or movi_list.getlisttype() != 'movi':
                raise ChunkTypeException('Chunk: {}, {}'.format(movi_list.getname().decode('ASCII'), movi_list.getsize()))
            data_chunks = []
            while movi_list.tell() < movi_list.getsize() - 1:
                try:
                    with rollback(movi_list, reraise=True):
                        rec_list = AviRecList.from_chunk(parent_chunk=movi_list)
                        data_chunks.extend(rec_list.data_chunks)
                except ChunkTypeException:
                    data_chunks.append(AviStreamChunk.from_chunk(movi_list))
            return cls(data_chunks=data_chunks)


class AviJunkChunk(object):

    @classmethod
    def from_file(cls, file):
        with closing(RIFFChunk(file)) as junk_chunk:
            if junk_chunk.getname() != b'JUNK':
                raise ChunkTypeException()


class AviOldIndexEntry(object):

    def __init__(self, chunk_id, flags, offset, size):
        self.chunk_id = chunk_id
        self.flags = AVIIF(flags)
        self.offset = offset
        self.size = size

    def __str__(self):
        return "<i={}, f={}, o={}, s={}>".format(self.chunk_id,
                                                 repr(self.flags),
                                                 self.offset,
                                                 self.size)

    @classmethod
    def from_chunk(cls, parent_chunk):
        entry_data = unpack('4s3I', parent_chunk.read(16))
        return cls(entry_data[0].decode('ASCII'), *entry_data[1:])


class AviOldIndex(object):

    def __init__(self, index=None):
        self.index = index if index else None

    def __str__(self):
        return "AviOldIndex:\n" + "\n".join(["  " + str(e) for e in self.index])

    @classmethod
    def from_file(cls, file):
        with closing(RIFFChunk(file)) as idx1_chunk:
            if idx1_chunk.getname() != b'idx1':
                raise ChunkTypeException()
            index = []
            while idx1_chunk.tell() < idx1_chunk.getsize():
                index.append(AviOldIndexEntry.from_chunk(idx1_chunk))
            return cls(index=index)


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


class AviFile(object):

    def __init__(self, file_or_filename):
        self.__file = file_or_filename
        if not hasattr(self.__file, 'read'):
            self.__file = open(file_or_filename, 'rb')

        if self.__file.read(4).decode('ASCII') != 'RIFF':
            raise ValueError('Non-RIFF file detected.')

        self.length = unpack('<i', self.__file.read(4))[0]
        if self.__file.read(4).decode('ASCII') != 'AVI ':
            raise ValueError('Non-AVI file detected.')

        with closing(RIFFChunk(self.__file)) as hdrl_chunk:
            self.avih = AviFileHeader.from_chunk(parent_chunk=hdrl_chunk)
            self.strl = []
            while hdrl_chunk.tell() < hdrl_chunk.getsize():
                self.strl.append(AviStreamDefinition.from_chunk(stream_id=len(self.strl), parent_chunk=hdrl_chunk))

        with rollback(self.__file):
            AviJunkChunk.from_file(self.__file)
        self.movi = AviMoviList.from_file(self.__file)

        self.idx1 = None
        try:
            self.idx1 = AviOldIndex.from_file(self.__file)
        except ChunkTypeException:
            pass

        self.__file.close()
