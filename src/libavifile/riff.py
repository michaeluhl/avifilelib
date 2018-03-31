# This file is part of libavifile.
#
# libavifile is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# libavifile is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU LesserGeneral Public
# License along with libavifile.  If not, see
#  <http://www.gnu.org/licenses/>.

from chunk import Chunk
from contextlib import contextmanager


@contextmanager
def rollback(file_like, reraise=False):
    """Context manager to recover from failed chunk creation.

    This context manager can be used to wrap calls to methods that attempt to
    read a RIFF chunk but require the chunk to be of a specific type.  If the
    method raises a :class:`ChunkTypeException`, this context manager catches
    the `ChunkTypeException` and rewinds the `file_like` object to its position
    before the failed call.

    Parameters
    ----------
        file_like : file-like
                    A file-like object (having at least `tell()` and `seek()` methods).
        reraise : bool
                  If `True`, any :class:`ChunkTypeException` raised while within
                  the context manager will be reraised after `file_like` is rewound.

    Yields
    ------
        file-like
            the object `file_like` passed as a parameter.

    """
    posn = file_like.tell()
    try:
        yield file_like
    except ChunkTypeException:
        file_like.seek(posn)
        if reraise:
            raise


class RIFFChunk(Chunk):
    """A class for reading RIFF chunks.

    A customized version of the :py:class:`chunk.Chunk` class to be used for reading RIFF files.
    The main customization being that the `bigendian` parameter defaults to `False` rather than
    `True`.  Additionally, the object will correctly handle RIFF 'LIST' chunks.

    Parameters
    ----------
    file : file_like
           A file-like object (has `read()`, `seek()`, and `tell()` methods.
    align : bool
            Indicates whether the chunk should aligned to a 2-byte boundary.
    bigendian : bool
            Indicates whether the byte order of the data should be big endian
            or little endian.
    inclheader : bool
                 Specifies whether the chunk size that will be read includes
                 the size of the chunk header (name and size).

    """

    def __init__(self, file, align=False, bigendian=False, inclheader=False):
        super(RIFFChunk, self).__init__(file=file,
                                        align=align,
                                        bigendian=bigendian,
                                        inclheader=inclheader)
        self.__list_type = None
        if self.getname() == b'LIST':
            self.__list_type = self.read(4).decode('ASCII')

    def islist(self):
        """Indicates if the chunk contains a RIFF list.

        Returns
        -------
            bool
                `True` if the chunk contains a RIFF list.

        """
        return self.__list_type is not None

    def getlisttype(self):
        """Type of RIFF list.

        Returns
        -------
            str
                The four character type identifier of the RIFF list or
                `None` if the chunk is not a RIFF list.

        """
        return self.__list_type


class ChunkTypeException(Exception):
    """Raised when the underlying chunk data does not match the expected RIFF type."""
    pass


class ChunkFormatException(Exception):
    """Raised when the underlying chunk data does not match the expected format."""
    pass