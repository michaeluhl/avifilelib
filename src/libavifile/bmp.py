import numpy as np
from enum import Enum
from io import BytesIO
from struct import unpack
from libavifile.avi import BitmapInfoHeaders
from libavifile.decoder import chunkwise, DecoderBase
from libavifile.enums import BI_COMPRESSION, FCC_TYPE


class BMP_DRAW_ORDER(Enum):
    BOTTOM_UP = 1
    TOP_DOWN = 2


class BMPFileHeader(object):

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

    COMPRESSION = (BI_COMPRESSION.BI_RGB, )

    def __init__(self, width, height, colors=None):
        super(BMPDecoderBase, self).__init__(width=width, height=abs(height))
        self._flip = BMP_DRAW_ORDER.BOTTOM_UP if height >= 0 else BMP_DRAW_ORDER.TOP_DOWN
        self._height = abs(height)
        self._colors = colors

    @property
    def image(self):
        if self._flip == BMP_DRAW_ORDER.TOP_DOWN:
            return np.flip(self._image, axis=0)
        return np.array(self._image)

    @classmethod
    def for_avi_stream(cls, stream_definition):
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

    BIT_COUNT = 8
    COMPRESSION = BI_COMPRESSION.BI_RGB

    def decode_frame_buffer(self, buffer, size, keyframe=True):
        if keyframe:
            self._image[:, :, :] = 0
        file = BytesIO(buffer)
        colors = self._colors
        try:
            bmpfileheader = BMPFileHeader.from_file(file=file)
            bitmapheader = BitmapInfoHeaders.from_file(file=file, force_color_table=True)
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

    BIT_COUNT = 16
    COMPRESSION = BI_COMPRESSION.BI_RGB

    RED_MASK = 0x7C00
    RED_SHIFT = 10
    GREEN_MASK = 0x3E0
    GREEN_SHIFT = 5
    BLUE_MASK = 0x1F
    BLUE_SHIFT = 0

    def decode_frame_buffer(self, buffer, size, keyframe=True):
        data = np.frombuffer(buffer, dtype='<u2', count=size // 2)
        data.shape = (self.height, self.width)
        self._image[:, :, 0] = np.right_shift(np.bitwise_and(data, self.RED_MASK), self.RED_SHIFT)
        self._image[:, :, 1] = np.right_shift(np.bitwise_and(data, self.GREEN_MASK), self.GREEN_SHIFT)
        self._image[:, :, 2] = np.right_shift(np.bitwise_and(data, self.BLUE_MASK), self.BLUE_SHIFT)
        self._image[:, :, :] = np.left_shift(self._image, 3)
        if self._flip == BMP_DRAW_ORDER.TOP_DOWN:
            return np.flip(self._image, axis=0)
        return np.array(self._image)
