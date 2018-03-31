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

"""Decoders for Microsoft RLE formats.

This package provides decoders capable of decoding frames
encoded using the Microsoft RLE4 and RLE8 formats.
"""
import numpy as np
from avifilelib.decoder import chunkwise, DecoderBase
from avifilelib.enums import BI_COMPRESSION, FCC_TYPE


class RLEDecoderBase(DecoderBase):
    """Base class for RLE formats.

    This class provides the foundation for run-length encoding decoders.
    Both the RLE4 and RLE8 formats require color paletes, and therefore
    this class accepts a color palate/table as an argument.

    Parameters
    ----------
        width : int
                Width of the image to be decoded.
        height : int
                Height of the image to be decoded.
        colors : numpy.ndarray, dtype=uint8
                 N x 3 of red, green, and blue values, where N is
                 2^4 or 2^8 depending on the type of RLE compression.

    """

    COMPRESSION = (BI_COMPRESSION.BI_RLE4, BI_COMPRESSION.BI_RLE8)

    def __init__(self, width, height, colors):
        super(RLEDecoderBase, self).__init__(width=width, height=height)
        self._colors = colors
        self._image[:, :, :] = self._colors[0, :]

    @property
    def colors(self):
        """Get the color table."""
        return self._colors

    @classmethod
    def for_avi_stream(cls, stream_definition):
        """Attempts to find a decoder implementation for a stream.

        Subclasses of :class:`RLEDecoderBase` are selected by matching
        the value of `COMPRESSION`.

        Returns
        -------
            object
                A subclass of :class:`RLEDecoderBase`.

        """
        fcc_type = stream_definition.strh.fcc_type
        if fcc_type != FCC_TYPE.VIDEO:
            raise RuntimeError('Stream {} is not a video stream.')

        compression = stream_definition.strf.compression
        for scls in cls.__subclasses__():
            if scls.COMPRESSION == compression:
                return scls(width=stream_definition.strf.width,
                            height=stream_definition.strf.height,
                            colors=stream_definition.strf.color_table)
        raise RuntimeError('No decoder for compression type: {}'.format(repr(compression)))


class RLE4Decoder(RLEDecoderBase):
    """Decoder for RLE4 compression.

    This class implements a decoder for the RLE4 compression
    algorithm.

    Parameters
    ----------
        width : int
                Width of the image to be decoded.
        height : int
                Height of the image to be decoded.
        colors : numpy.ndarray, dtype=uint8
                 16 x 3 of red, green, and blue values.

    """

    COMPRESSION = BI_COMPRESSION.BI_RLE4

    def __init__(self, width, height, colors):
        super(RLE4Decoder, self).__init__(width=width, height=height, colors=colors)

    def decode_frame_buffer(self, buffer, size, keyframe=True):
        """Decode a frame from a :py:class:`bytes` object.

        Decodes a single frame from the data contained in `buffer`.

        Parameters
        ----------
            buffer : bytes
                     A :py:class:`bytes` object containing the frame
                     data.
            size : int
                   Size of the data in the buffer.
            keyframe : bool
                       Indicates to the decoder that this chunk
                       contains a key frame.

        Returns
        -------
            numpy.ndarray
                A two dimensional array of dimensions `height` by `width`
                containing the resulting image.

        """
        row, col = 0, 0
        mode = 0
        if keyframe:
            self._image[:, :, :] = 0
        data = np.frombuffer(buffer, dtype='<B', count=size)
        for count, color_idx in chunkwise(data, count=2, fill_value=0x0):
            if mode == 'delta':
                col += count
                row += color_idx
                mode = 0
            elif mode > 0:
                for j in range(4):
                    cbyte = (count, color_idx)[j // 2]
                    idx = (cbyte >> 4*(1 - (j % 2))) & 0x0F
                    self._image[row, col, :] = self._colors[idx, :]
                    col += 1
                    mode -= 1
                    if mode == 0:
                        break
            elif count == 0x00:
                if color_idx == 0x00:
                    row += 1
                    col = 0
                elif color_idx == 0x01:
                    break
                elif color_idx == 0x02:
                    mode = 'delta'
                else:
                    mode = color_idx
            else:
                self._image[row, col:col + count:2, :] = self._colors[color_idx >> 4, :]
                self._image[row, col + 1:col + count:2, :] = self._colors[color_idx & 0x0F, :]
                col += count
        return np.array(self._image)


class RLE8Decoder(RLEDecoderBase):
    """Decoder for RLE8 compression.

    This class implements a decoder for the RLE8 compression
    algorithm.

    Parameters
    ----------
        width : int
                Width of the image to be decoded.
        height : int
                Height of the image to be decoded.
        colors : numpy.ndarray, dtype=uint8
                 256 x 3 of red, green, and blue values.

    """

    COMPRESSION = BI_COMPRESSION.BI_RLE8

    def __init__(self, width, height, colors):
        super(RLE8Decoder, self).__init__(width=width, height=height, colors=colors)

    def decode_frame_buffer(self, buffer, size, keyframe=True):
        """Decode a frame from a :py:class:`bytes` object.

        Decodes a single frame from the data contained in `buffer`.

        Parameters
        ----------
            buffer : bytes
                     A :py:class:`bytes` object containing the frame
                     data.
            size : int
                   Size of the data in the buffer.
            keyframe : bool
                       Indicates to the decoder that this chunk
                       contains a key frame.

        Returns
        -------
            numpy.ndarray
                A two dimensional array of dimensions `height` by `width`
                containing the resulting image.

        """
        row, col = 0, 0
        mode = 0
        if keyframe:
            self._image[:, :, :] = 0
        data = np.frombuffer(buffer, dtype='<B', count=size)
        for count, color_idx in chunkwise(data, count=2, fill_value=0x0):
            if mode == 'delta':
                col += count
                row += color_idx
                mode = 0
            elif mode > 0:
                self._image[row, col, :] = self._colors[count, :]
                col += 1
                mode -= 1
                if mode > 0:
                    self._image[row, col, :] = self._colors[color_idx, :]
                    col += 1
                    mode -= 1
            elif count == 0x00:
                if color_idx == 0x00:
                    row += 1
                    col = 0
                elif color_idx == 0x01:
                    break
                elif color_idx == 0x02:
                    mode = 'delta'
                else:
                    mode = color_idx
            else:
                self._image[row, col:col + count, :] = self._colors[color_idx, :]
                col += count
        return np.array(self._image)
