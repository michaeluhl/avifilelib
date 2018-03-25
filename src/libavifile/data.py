from contextlib import closing

from libavifile.enums import STREAM_DATA_TYPES, AVIIF
from libavifile.riff import RIFFChunk, ChunkFormatException, ChunkTypeException, rollback


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
        return pos

    def tell(self):
        if self.base_file.closed:
            raise ValueError("I/O operation on closed file")
        return self.size_read

    @classmethod
    def load(cls, file_like):
        with closing(RIFFChunk(file_like, align=True)) as strm_chunk:
            chunk_id = strm_chunk.getname().decode('ASCII')
            try:
                stream_id = int(chunk_id[:2])
            except ValueError:
                strm_chunk.seek(0)
                raise ChunkFormatException('Could not decode stream index: '
                                           '{} @ offset 0x{:08x}'.format(chunk_id[:2],
                                                                         file_like.tell()))
            try:
                data_type = STREAM_DATA_TYPES(chunk_id[2:])
            except ValueError:
                strm_chunk.seek(0)
                raise ChunkFormatException('Could not determine stream data type: '
                                           '{} @ offset 0x{:08x}'.format(chunk_id[2:],
                                                                         file_like.tell()))
            base_file = file_like
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
    def load(cls, file_like):
        with closing(RIFFChunk(file_like)) as rec_list:
            if not rec_list.islist() or rec_list.getname() != b'rec ':
                raise ChunkTypeException()
            data_chunks = []
            while rec_list.tell() < rec_list.getsize() - 1:
                data_chunks.append(AviStreamChunk.load(rec_list))
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
        # If there's an index, some of the chunks may be skipped, so
        # set them all to be skipped, and then...
        for chunk in self.data_chunks:
            chunk.skip = True
        for entry in index.index:
            chunk = self.by_offset[entry.offset]
            chunk.flags = entry.flags
            # Un-skip it in when processing the index
            chunk.skip = False

    def iter_chunks(self, stream=None):
        if stream and stream not in self.streams:
            raise RuntimeError('Invalid stream id: {}'.format(stream))
        for chunk in self.data_chunks:
            if (not stream or chunk.stream_id == stream) and not chunk.skip:
                yield chunk
            else:
                continue

    @classmethod
    def load(cls, file_like):
        with closing(RIFFChunk(file=file_like)) as movi_list:
            if not movi_list.islist() or movi_list.getlisttype() != 'movi':
                raise ChunkTypeException('Chunk: {}, {}, {}'.format(movi_list.getname().decode('ASCII'),
                                                                    movi_list.getsize(),
                                                                    movi_list.getlisttype()))
            base_file = file_like
            while isinstance(base_file, RIFFChunk):
                base_file = base_file.file
            absolute_offset = base_file.tell()
            data_chunks = []
            while movi_list.tell() < movi_list.getsize() - 1:
                try:
                    with rollback(movi_list, reraise=True):
                        rec_list = AviRecList.load(file_like=movi_list)
                        data_chunks.extend(rec_list.data_chunks)
                except ChunkTypeException:
                    data_chunks.append(AviStreamChunk.load(movi_list))
            return cls(absolute_offset=absolute_offset, data_chunks=data_chunks)