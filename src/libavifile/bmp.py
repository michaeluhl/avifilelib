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

"""Decoders for Microsoft BMP formats.

This package provides decoders capable of decoding frames
encoded using the Microsoft Bitmap formats.
"""
import numpy as np
from enum import Enum
from io import BytesIO
from struct import unpack
from libavifile.definition import BitmapInfoHeaders
from libavifile.decoder import chunkwise, DecoderBase
from libavifile.enums import BI_COMPRESSION, FCC_TYPE


class BMP_DRAW_ORDER(Enum):
    """Bitmap drawing orders.
    """
    BOTTOM_UP = 1
    TOP_DOWN = 2


class BMPFileHeader(object):
    """`BITMAPFILEHEADER`_ structure.

    .. _BITMAPFILEHEADER: https://msdn.microsoft.com/en-us/library/windows/desktop/dd183374(v=vs.85).aspx

    Parameters
    ----------
        type : bytes
            must be b'BM'
        size : int
            Size of the bitmap data
        reserved1 : int
            Reserved value, must be zero (but not checked here)
        reserved2 : int
            Reserved value, must be zero (but not checked here)
        offbits : int
            offset from the beginning of the header to start of the bitmap data

    """

    def __init__(self, type, size, reserved1, reserved2, offbits):
        self.type = type
        if self.type != b'BM':
            raise ValueError('BMPFileHeader type must be "BM"')
        self.size = size
        self.reserved1 = reserved1
        self.reserved2 = reserved2
        self.offbits = offbits

    @classmethod
    def from_file(cls, file):
        return cls(*unpack('<2sI2HI', file.read(14)))

    @classmethod
    def from_buffer(cls, buffer):
        return cls(*unpack('<2sI2HI', buffer))


class BMPDecoderBase(DecoderBase):
    """Base class for bitmap decoders.

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

    COMPRESSION = (BI_COMPRESSION.BI_RGB, )

    def __init__(self, width, height, colors=None):
        super(BMPDecoderBase, self).__init__(width=width, height=abs(height))
        self._flip = BMP_DRAW_ORDER.BOTTOM_UP if height >= 0 else BMP_DRAW_ORDER.TOP_DOWN
        self._height = abs(height)
        self._colors = colors

    @property
    def image(self):
        """Gets a copy of the image."""
        if self._flip == BMP_DRAW_ORDER.TOP_DOWN:
            return np.flip(self._image, axis=0)
        return np.array(self._image)

    @classmethod
    def for_avi_stream(cls, stream_definition):
        """Attempts to find a decoder implementation for a stream.

        Subclasses of :class:`BMPDecoderBase` are selected by matching
        the value of `BIT_COUNT`.

        Returns
        -------
            object
                A subclass of :class:`BMPDecoderBase`.

        """
        fcc_type = stream_definition.strh.fcc_type
        if fcc_type != FCC_TYPE.VIDEO:
            raise RuntimeError('Stream {} is not a video stream.')

        compression = stream_definition.strf.compression
        bit_count = stream_definition.strf.bit_count
        for scls in cls.__subclasses__():
            if scls.COMPRESSION == compression and scls.BIT_COUNT == bit_count:
                return scls(width=stream_definition.strf.width,
                            height=stream_definition.strf.height,
                            colors=stream_definition.strf.color_table)
        raise RuntimeError('No decoder for compression type: {}'.format(repr(compression)))


class BMP8Decoder(BMPDecoderBase):
    """Decoder for 8-bit bitmaps.

    This class implements a decoder for the 8-bit bitmaps.

    """

    BIT_COUNT = 8
    COMPRESSION = BI_COMPRESSION.BI_RGB

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
        if keyframe:
            self._image[:, :, :] = 0
        file = BytesIO(buffer)
        colors = self._colors
        try:
            bmpfileheader = BMPFileHeader.from_file(file=file)
            bitmapheader = BitmapInfoHeaders.load_from_file(file_like=file, force_color_table=True)
            if len(bitmapheader.color_table) != 0:
                colors = bitmapheader.color_table
        except ValueError:
            file.seek(0)
        count = size - file.tell()
        data = np.frombuffer(file.read(), dtype='<B', count=count)
        scan_length = self.width if self.width % 2 == 0 else self.width + 1
        for j, row_data in enumerate(chunkwise(data,
                                               count=scan_length,
                                               fill_value=0)):
            for i, idx in enumerate(row_data):
                if i < self.width:
                    self._image[j, i, :] = colors[idx, :]
        file.close()
        if self._flip == BMP_DRAW_ORDER.TOP_DOWN:
            return np.flip(self._image, axis=0)
        return np.array(self._image)


class BMP16Decoder(BMPDecoderBase):
    """Decoder for 16-bit bitmaps.

    This class implements a decoder for the 16-bit bitmaps.

    """

    BIT_COUNT = 16
    COMPRESSION = BI_COMPRESSION.BI_RGB

    RED_MASK = 0x7C00
    RED_SHIFT = 10
    GREEN_MASK = 0x3E0
    GREEN_SHIFT = 5
    BLUE_MASK = 0x1F
    BLUE_SHIFT = 0

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
        data = np.frombuffer(buffer, dtype='<u2', count=size // 2)
        data.shape = (self.height, self.width)
        self._image[:, :, 0] = np.right_shift(np.bitwise_and(data, self.RED_MASK), self.RED_SHIFT)
        self._image[:, :, 1] = np.right_shift(np.bitwise_and(data, self.GREEN_MASK), self.GREEN_SHIFT)
        self._image[:, :, 2] = np.right_shift(np.bitwise_and(data, self.BLUE_MASK), self.BLUE_SHIFT)
        self._image[:, :, :] = np.left_shift(self._image, 3)
        if self._flip == BMP_DRAW_ORDER.TOP_DOWN:
            return np.flip(self._image, axis=0)
        return np.array(self._image)


class BMP24Decoder(BMPDecoderBase):
    """Decoder for 24-bit bitmaps.

    This class implements a decoder for the 24-bit bitmaps.

    """

    BIT_COUNT = 24
    COMPRESSION = BI_COMPRESSION.BI_RGB

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
        data = np.frombuffer(buffer, dtype='<B', count=size)
        scanwidth = self.width * 3 if self.width * 3 % 4 == 0 else self.width * 3 + self.width * 3 % 4
        data.shape = (self.height, scanwidth)
        self._image[:, :, 0] = data[:, 0:self.width * 3:3]
        self._image[:, :, 1] = data[:, 1:self.width * 3:3]
        self._image[:, :, 2] = data[:, 2:self.width * 3:3]
        if self._flip == BMP_DRAW_ORDER.TOP_DOWN:
            return np.flip(self._image, axis=0)
        return np.array(self._image)


class BMP32Decoder(BMPDecoderBase):
    """Decoder for 32-bit bitmaps.

    This class implements a decoder for the 32-bit bitmaps.

    """

    BIT_COUNT = 32
    COMPRESSION = BI_COMPRESSION.BI_RGB

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
        data = np.frombuffer(buffer, dtype='<B', count=size)
        data.shape = (self.height, self.width*4)
        self._image[:, :, 0] = data[:,2::4]
        self._image[:, :, 1] = data[:,1::4]
        self._image[:, :, 2] = data[:,0::4]
        if self._flip == BMP_DRAW_ORDER.TOP_DOWN:
            return np.flip(self._image, axis=0)
        return np.array(self._image)
