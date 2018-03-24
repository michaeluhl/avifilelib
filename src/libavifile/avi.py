from contextlib import closing
from struct import unpack

import numpy as np
from libavifile.decoder import DecoderBase
from libavifile.enums import BI_COMPRESSION, AVIF, AVIIF, AVISF, FCC_TYPE, STREAM_DATA_TYPES
from libavifile.riff import rollback, RIFFChunk, ChunkTypeException, ChunkFormatException


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
            if not strl_chunk.islist() or strl_chunk.getlisttype() != 'strl':
                raise ChunkTypeException('Non-"strl" Chunk: {}, {}, {}'.format(
                    strl_chunk.getname().decode('ASCII'),
                    strl_chunk.getsize(),
                    strl_chunk.getlisttype()
                ))
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
                with rollback(strl_chunk):
                    _ = AviJunkChunk.from_file(strl_chunk)
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
    def from_chunk(cls, parent_chunk):
        with closing(RIFFChunk(parent_chunk)) as strh_chunk:
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
    def from_chunk(cls, stream_header, parent_chunk, force_color_table=False):
        with closing(RIFFChunk(parent_chunk)) as strf_chunk:
            return cls.from_file(strf_chunk, force_color_table=force_color_table)

    @classmethod
    def from_file(cls, file, force_color_table=False):
        strf = cls(*unpack(cls.UNPACK_FORMAT, file.read(40)))
        strf.read_colortable(file, force=force_color_table)
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

    def __init__(self, stream_id, data_type, base_file, absolute_offset, size, flags=0, skip=False):
        self.stream_id = stream_id
        self.data_type = STREAM_DATA_TYPES(data_type)
        self.base_file = base_file
        self.absolute_offset = absolute_offset
        self.size = size
        self.size_read = 0
        self.__flags = AVIIF(flags)
        self.skip = skip

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
        with closing(RIFFChunk(parent_chunk, align=True)) as strm_chunk:
            chunk_id = strm_chunk.getname().decode('ASCII')
            try:
                stream_id = int(chunk_id[:2])
            except ValueError:
                strm_chunk.seek(0)
                raise ChunkFormatException('Could not decode stream index: '
                                           '{} @ offset 0x{:08x}'.format(chunk_id[:2],
                                                                         parent_chunk.tell()))
            try:
                data_type = STREAM_DATA_TYPES(chunk_id[2:])
            except ValueError:
                strm_chunk.seek(0)
                raise ChunkFormatException('Could not determine stream data type: '
                                           '{} @ offset 0x{:08x}'.format(chunk_id[2:],
                                                                         parent_chunk.tell()))
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

    def __init__(self, absolute_offset=0, data_chunks=None):
        self.absolute_offset = absolute_offset
        self.data_chunks = data_chunks if data_chunks else []
        self.streams = {}
        self.by_offset = {}
        for chunk in self.data_chunks:
            self.streams.setdefault(chunk.stream_id, []).append(chunk)
            self.by_offset[chunk.absolute_offset - self.absolute_offset -4] = chunk

    def __getitem__(self, item):
        return self.streams[item]

    def apply_index(self, index):
        for entry in index.index:
            chunk = self.by_offset[entry.offset]
            chunk.flags = entry.flags

    def get_by_index_entry(self, entry):
        chunk = self.get_by_movi_offset(entry.offset)
        chunk.flags = entry.flags
        return chunk

    def get_by_movi_offset(self, movi_offset):
        return self.by_offset[movi_offset]

    def iter_chunks_by_index(self, index, stream=None):
        if stream and stream not in self.streams:
            raise RuntimeError('Invalid stream id: {}'.format(stream))
        for entry in index.index:
            chunk = self.get_by_index_entry(entry=entry)
            if not stream or chunk.stream_id == stream:
                yield chunk
            else:
                continue

    def iter_chunks(self, stream=None):
        if stream and stream not in self.streams:
            raise RuntimeError('Invalid stream id: {}'.format(stream))
        for chunk in self.data_chunks:
            if not stream or chunk.stream_id == stream:
                yield chunk
            else:
                continue

    @classmethod
    def from_file(cls, file):
        with closing(RIFFChunk(file=file)) as movi_list:
            if not movi_list.islist() or movi_list.getlisttype() != 'movi':
                raise ChunkTypeException('Chunk: {}, {}, {}'.format(movi_list.getname().decode('ASCII'),
                                                                    movi_list.getsize(),
                                                                    movi_list.getlisttype()))
            absolute_offset = file.tell()
            data_chunks = []
            while movi_list.tell() < movi_list.getsize() - 1:
                try:
                    with rollback(movi_list, reraise=True):
                        rec_list = AviRecList.from_chunk(parent_chunk=movi_list)
                        data_chunks.extend(rec_list.data_chunks)
                except ChunkTypeException:
                    data_chunks.append(AviStreamChunk.from_chunk(movi_list))
            return cls(absolute_offset=absolute_offset, data_chunks=data_chunks)


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
        self.stream_id = int(self.chunk_id[:2])
        self.data_type = STREAM_DATA_TYPES(self.chunk_id[2:])

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

    def by_stream(self, stream_id):
        return AviOldIndex(index=[e for e in self.index if e.stream_id == stream_id])

    def by_data_type(self, data_type):
        return AviOldIndex(index=[e for e in self.index if e.data_type == data_type])

    @classmethod
    def from_file(cls, file):
        with closing(RIFFChunk(file)) as idx1_chunk:
            if idx1_chunk.getname() != b'idx1':
                raise ChunkTypeException()
            index = []
            while idx1_chunk.tell() < idx1_chunk.getsize():
                index.append(AviOldIndexEntry.from_chunk(idx1_chunk))
            return cls(index=index)


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
            self.avi_header = AviFileHeader.from_chunk(parent_chunk=hdrl_chunk)
            self.stream_definitions = []
            for i in range(self.avi_header.streams):
                self.stream_definitions.append(
                    AviStreamDefinition.from_chunk(stream_id=len(self.stream_definitions),
                                                   parent_chunk=hdrl_chunk))
        self.stream_content = None
        while not self.stream_content:
            try:
                self.stream_content = AviMoviList.from_file(self.__file)
            except ChunkTypeException:
                pass

        self.old_index = None
        try:
            self.old_index = AviOldIndex.from_file(self.__file)
            self.stream_content.apply_index(self.old_index)
        except ChunkTypeException:
            if AVIF.MUSTUSEINDEX in self.avi_header.flags:
                raise ValueError('AVI header requires use of index and index is missing.')

    @property
    def avih(self):
        return self.avi_header

    @property
    def strl(self):
        return self.stream_definitions

    @property
    def movi(self):
        return self.stream_content

    @property
    def idx1(self):
        return self.old_index

    def iter_frames(self, stream_id):
        stream_definition = self.stream_definitions[stream_id]
        decoder = DecoderBase.for_avi_stream(stream_definition=stream_definition)
        for stream_chunk in self.stream_content.iter_chunks(stream=stream_id):
            yield decoder.decode_frame_chunk(stream_chunk=stream_chunk,
                                             keyframe=True)

    def close(self):
        if not self.__file.closed:
            self.__file.close()
