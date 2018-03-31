# This file is part of avifilelib.
#
# avifilelib is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# avifilelib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU LesserGeneral Public
# License along with avifilelib.  If not, see
#  <http://www.gnu.org/licenses/>.

"""AVI Index classes.

This module contains classes related to the index structures used
in AVI files.  At present, the module provides the :py:class:`AviV1Index`
class to represent the `AVIOLDINDEX`_ structure, and the
:py:class:`AviV1IndexEntry` class to represent entries in the
index.

.. _AVIOLDINDEX: https://msdn.microsoft.com/en-us/library/windows/desktop/dd318181(v=vs.85).aspx
"""
from contextlib import closing
from struct import unpack

from avifilelib.enums import AVIIF, STREAM_DATA_TYPES
from avifilelib.riff import RIFFChunk, ChunkTypeException


class AviV1IndexEntry(object):
    """A class to represent an `AVIOLDINDEX_ENTRY`.

    Parameters
    ----------
        chunk_id : str
            String version of the chunk identifier.  This consists of
            two characters for the data type, and two characters for
            the stream id number.
        flags : :py:class:`avifilelib.enum.AVIIF`
            Flags associated with a given chunk in the index.
        offset : int
            Offset in bytes from the start of the 'movi' list to the
            start of the data chunk.
        size : int
            Size of the data in the chunk.

    """

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
    def load(cls, file_like):
        """Create an `AviV1IndexEntry` structure.

        This method creates an :py:class:`AviV1IndexEntry` from the contents of
        an AVI 'idx1' list.

        Parameters
        ----------
            file_like : file-like
                A file-like object positioned at the start of a index entry.

        Returns
        -------
            :py:class:`AviV1IndexEntry`
                An `AviV1IndexEntry` containing data for an index entry.

        """

        entry_data = unpack('4s3I', file_like.read(16))
        return cls(entry_data[0].decode('ASCII'), *entry_data[1:])


class AviV1Index(object):
    """A class to represent the `AVIOLDINDEX` structure.

    Parameters
    ----------
        index : list
            A list containing :py:class:`AviV1IndexEntry` objects.

    """

    def __init__(self, index=None):
        self.index = index if index else None

    def __str__(self):
        return "AviV1Index:\n" + "\n".join(["  " + str(e) for e in self.index])

    def by_stream(self, stream_id):
        """Get a new index structure containing only entries for `stream_id`.

        Parameters
        ----------
            stream_id : int
                The index number of stream for which an index should be returned.

        Returns
        -------
            :py:class:`AviV1Index`
                A new index containing entries only for `stream_id`.

        """
        return AviV1Index(index=[e for e in self.index if e.stream_id == stream_id])

    def by_data_type(self, data_type):
        """Get a new index structure containing entries only for `data_type`.

        Parameters
        ----------
            data_type : :py:class:`avifilelib.enums.AVIIF`
                The type of the data chunks that should be contained
                in the returned index.

        Returns
        -------
            :py:class:`AviV1Index`
                A new index containing entries only for `stream_id`.

        """
        return AviV1Index(index=[e for e in self.index if e.data_type == data_type])

    @classmethod
    def load(cls, file_like):
        """Create an `AviV1Index` structure.

        This method creates an :py:class:`AviV1Index` from the contents of
        an AVI 'idx1' list.

        Parameters
        ----------
            file_like : file-like
                A file-like object positioned at the start of a index structure.

        Returns
        -------
            :py:class:`AviV1Index`
                An `AviV1Index` that may be used to read the data for this chunk.

        """

        with closing(RIFFChunk(file_like)) as idx1_chunk:
            if idx1_chunk.getname() != b'idx1':
                raise ChunkTypeException()
            index = []
            while idx1_chunk.tell() < idx1_chunk.getsize():
                index.append(AviV1IndexEntry.load(idx1_chunk))
            return cls(index=index)