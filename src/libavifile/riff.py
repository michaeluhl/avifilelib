from chunk import Chunk
from contextlib import contextmanager


@contextmanager
def rollback(file_like, reraise=False):
    posn = file_like.tell()
    try:
        yield file_like
    except ChunkTypeException:
        file_like.seek(posn)
        if reraise:
            raise


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


class ChunkTypeException(Exception):
    pass


class ChunkFormatException(Exception):
    pass