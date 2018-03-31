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

"""Base class for video stream decoders.

This module defines the base class for video decoders and
provides a utility function that is used by a number of
the included decoders.
"""
from itertools import zip_longest

import numpy as np
from libavifile.enums import FCC_TYPE, AVIIF


def chunkwise(iterable, count=2, fill_value=None):
    """Iterate over `count`-size chunks of an iterable.

    Parameters
    ----------
        iterable : iterable
                   An object that can be iterated over.
        count : int
                Size of the chunks to be returned.
        fill_value : object
                Value to be use as a filler if `iterable` is not
                divisible by `count`.

    Returns
    -------
        zip_longest
            An iterable object which yields `count`-tuples.


    """
    it = iter(iterable)
    return zip_longest(*[it]*count, fillvalue=fill_value)


class DecoderBase(object):
    """Base class for video Decoder objects.

    Parameters
    ----------
        width : int
                Width of the image to be decoded.
        height : int
                 Height of the image to be decoded.

    """

    def __init__(self, width, height):
        self._width = width
        self._height = height
        self._image = np.zeros((height, width, 3), dtype='B')

    @property
    def width(self):
        """Gets the width of the image."""
        return self._width

    @property
    def height(self):
        """Gets the height of the image."""
        return self._height

    @property
    def image(self):
        """Gets a copy of the image."""
        return np.array(self._image)

    def decode_frame_chunk(self, stream_chunk, keyframe=False):
        """Decode a frame from a RIFF chunk.

        Parameters
        ----------
            stream_chunk : :class:`libavifile.avi.AviStreamChunk`
                           A data chunk that contains frame data.
            keyframe : bool
                       Indicates to the decoder that this chunk
                       contains a key frame.

        Returns
        -------
            numpy.ndarray
                A two dimensional array of dimensions `height` by `width` containing the resulting image.

        """
        stream_chunk.seek(0)
        buffer = stream_chunk.read()
        keyframe = AVIIF.KEYFRAME in stream_chunk.flags or keyframe
        return self.decode_frame_buffer(buffer=buffer,
                                        size=len(buffer),
                                        keyframe=keyframe)

    def decode_frame_buffer(self, buffer, size, keyframe=True):
        """Decode a frame from a :py:class:`bytes` object.

        This method has no implementation in DecoderBase and raises
        a :py:class:`NotImplementedError`.  This method must be
        implemented by subclasses of :class:`DecoderBase`.

        Parameters
        ----------
            buffer : bytes
                     A :py:class:`bytes` object containing the frame
                     data.
            size : int
                   Size of the data in the buffer.  Some formats write
                   2-byte aligned chunks, and therefore, the data size
                   need not equal the length of `buffer`.
            keyframe : bool
                       Indicates to the decoder that this chunk
                       contains a key frame.

        Returns
        -------
            numpy.ndarray
                A two dimensional array of dimensions `height` by `width` containing the resulting image.

        """
        raise NotImplementedError()

    @classmethod
    def for_avi_stream(cls, stream_definition):
        """Attempts to find a decoder implementation for a stream.

        This method searches DecoderBase subclasses for a subclass capable of
        handling the stream format defined in `stream_definition`.  Matches are
        made by comparing the `stream_definition.stream_header.compression` field
        to the `COMPRESSION` member of a `DecoderBase` subclass.  The `COMPRESSION`
        member must be a member of the :class:`libavifile.enums.BI_COMPRESSION`
        enumeration, or a tuple of such values.  Thus, if a particular compression
        method supports multiple subformats, it is recommended that a subclass base
        for that compression method be written, and the `for_avi_stream()` method
        of the subclass be overridden to handle further delegation.

        Parameters
        ----------
            stream_definition : :class:`libavifile.avi.AviStreamDefinition`
                                Stream definition for the stream to be decoded.

        Returns
        -------
            object
                A subclass of :class:`DecoderBase` capable of decoding a stream
                compressed according to `stream_definition`.

        """
        fcc_type = stream_definition.strh.fcc_type
        if fcc_type != FCC_TYPE.VIDEO:
            raise RuntimeError('Stream {} is not a video stream.')

        compression = stream_definition.strf.compression
        for scls in cls.__subclasses__():
            if compression in scls.COMPRESSION:
                return scls.for_avi_stream(stream_definition=stream_definition)
        raise RuntimeError('No decoder for compression type: {}'.format(repr(compression)))
