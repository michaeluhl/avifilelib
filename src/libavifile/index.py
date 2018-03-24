from contextlib import closing
from struct import unpack

from libavifile.enums import AVIIF, STREAM_DATA_TYPES
from libavifile.riff import RIFFChunk, ChunkTypeException


class AviV1IndexEntry(object):

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


class AviV1Index(object):

    def __init__(self, index=None):
        self.index = index if index else None

    def __str__(self):
        return "AviV1Index:\n" + "\n".join(["  " + str(e) for e in self.index])

    def by_stream(self, stream_id):
        return AviV1Index(index=[e for e in self.index if e.stream_id == stream_id])

    def by_data_type(self, data_type):
        return AviV1Index(index=[e for e in self.index if e.data_type == data_type])

    @classmethod
    def from_file(cls, file):
        with closing(RIFFChunk(file)) as idx1_chunk:
            if idx1_chunk.getname() != b'idx1':
                raise ChunkTypeException()
            index = []
            while idx1_chunk.tell() < idx1_chunk.getsize():
                index.append(AviV1IndexEntry.from_chunk(idx1_chunk))
            return cls(index=index)