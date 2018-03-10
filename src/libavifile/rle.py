import numpy as np
from libavifile.decoder import chunkwise, DecoderBase
from libavifile.enums import BI_COMPRESSION, FCC_TYPE


class RLEDecoderBase(DecoderBase):

    COMPRESSION = (BI_COMPRESSION.BI_RLE4, BI_COMPRESSION.BI_RLE8)

    def __init__(self, width, height, colors):
        super(RLEDecoderBase, self).__init__(width=width, height=height)
        self._colors = colors
        self._image[:, :, :] = self._colors[0, :]

    @property
    def colors(self):
        return self._colors

    @classmethod
    def for_avi_stream(cls, stream_definition):
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

    COMPRESSION = BI_COMPRESSION.BI_RLE4

    def __init__(self, width, height, colors):
        super(RLE4Decoder, self).__init__(width=width, height=height, colors=colors)

    def decode_frame(self, bytes, size, keyframe=True):
        row, col = 0, 0
        mode = 0
        if keyframe:
            self._image[:, :, :] = 0
        data = np.frombuffer(bytes, dtype='<B', count=size)
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
        return np.flip(self._image, axis=0)


class RLE8Decoder(RLEDecoderBase):

    COMPRESSION = BI_COMPRESSION.BI_RLE8

    def __init__(self, width, height, colors):
        super(RLE8Decoder, self).__init__(width=width, height=height, colors=colors)

    def decode_frame(self, bytes, size, keyframe=True):
        row, col = 0, 0
        mode = 0
        if keyframe:
            self._image[:, :, :] = 0
        data = np.frombuffer(bytes, dtype='<B', count=size)
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
        return np.flip(self._image, axis=0)
