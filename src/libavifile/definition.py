from contextlib import closing
from struct import unpack

import numpy as np
from libavifile.enums import FCC_TYPE, AVISF, BI_COMPRESSION
from libavifile.riff import RIFFChunk, ChunkTypeException, rollback, ChunkFormatException


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
    def load(cls, stream_id, file_like):
        with closing(RIFFChunk(file_like)) as strl_chunk:
            if not strl_chunk.islist() or strl_chunk.getlisttype() != 'strl':
                raise ChunkTypeException('Non-"strl" Chunk: {}, {}, {}'.format(
                    strl_chunk.getname().decode('ASCII'),
                    strl_chunk.getsize(),
                    strl_chunk.getlisttype()
                ))
            strh = AviStreamHeader.load(strl_chunk)
            strf = AviStreamFormat.load(stream_header=strh, file_like=strl_chunk)
            strd = None
            strn = None
            try:
                with rollback(strl_chunk):
                    strd = AviStreamData.load(file_like=strl_chunk)
                with rollback(strl_chunk):
                    strn = AviStreamName.load(file_like=strl_chunk)
                with rollback(strl_chunk):
                    _ = AviJunkChunk.load(file_like=strl_chunk)
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
        self.flags = AVISF(flags)
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
    def load(cls, file_like):
        with closing(RIFFChunk(file_like)) as strh_chunk:
            size = strh_chunk.getsize()
            if size not in (48, 56, 64):
                raise ChunkFormatException('Invalid Stream Header Size ({})'.format(strh_chunk.getsize()))
            if size == 48:
                return cls(*unpack('<4s4sI2H8I', strh_chunk.read()), tuple())
            unpack_format = '<4s4sI2H8I4h'
            if strh_chunk.getsize() == 64:
                unpack_format = '<4s4sI2H8I4l'
            strh_values = unpack(unpack_format, strh_chunk.read())
            return cls(*strh_values[:-4], strh_values[-4:])


class AviStreamFormat(object):

    @classmethod
    def load(cls, stream_header, file_like):
        for scls in cls.__subclasses__():
            if getattr(scls, 'FCC_TYPE', None) == stream_header.fcc_type:
                return scls.load(stream_header, file_like)
        return UnparsedStreamFormat.load(stream_header, file_like)


class UnparsedStreamFormat(AviStreamFormat):

    def __init__(self, raw_bytes):
        self.raw_bytes = raw_bytes

    @classmethod
    def load(cls, stream_header, file_like):
        with closing(RIFFChunk(file_like)) as strf_chunk:
            return cls(strf_chunk.read())


class BitmapInfoHeaders(AviStreamFormat):

    FCC_TYPE = FCC_TYPE.VIDEO

    UNPACK_FORMAT = '<I2i2H2I2i2I'

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
    def load(cls, stream_header, file_like, force_color_table=False):
        with closing(RIFFChunk(file_like)) as strf_chunk:
            return cls.load_from_file(strf_chunk, force_color_table=force_color_table)

    @classmethod
    def load_from_file(cls, file_like, force_color_table=False):
        strf = cls(*unpack(cls.UNPACK_FORMAT, file_like.read(40)))
        strf.read_colortable(file_like, force=force_color_table)
        return strf

    def read_colortable(self, chunk, force=False):
        clr_size = 4*self.clr_used
        self.color_table = []
        if self.clr_used <= 0 and not force:
            return
        elif self.clr_used <= 0:
            clr_size = (2**self.bit_count) * 4
        try:
            colors = unpack('<{}B'.format(clr_size),
                            chunk.read(clr_size))
            self.color_table = np.array([list(reversed(colors[i:i+3])) for i in range(0, len(colors), 4)],
                                        dtype='B')
            return
        except EOFError:
            pass


class AviStreamData(object):

    def __init__(self, raw_bytes):
        self.raw_bytes = raw_bytes

    @classmethod
    def load(cls, file_like):
        with closing(RIFFChunk(file_like)) as strd_chunk:
            if strd_chunk.getname() == b'strd':
                return cls(strd_chunk.read())
            raise ChunkTypeException()


class AviStreamName(object):

    def __init__(self, name):
        self.name = name

    @classmethod
    def load(cls, file_like):
        with closing(RIFFChunk(file_like)) as strn_chunk:
            if strn_chunk.getname() == b'strn':
                raw_bytes = strn_chunk.read()
                name = raw_bytes[:raw_bytes.index(b'\0')].decode('ASCII')
                return cls(name=name)
            raise ChunkTypeException()


class AviJunkChunk(object):

    @classmethod
    def load(cls, file_like):
        with closing(RIFFChunk(file_like)) as junk_chunk:
            if junk_chunk.getname() != b'JUNK':
                raise ChunkTypeException()