from itertools import zip_longest

import numpy as np
from libavifile.enums import FCC_TYPE, AVIIF


def chunkwise(iterable, count=2, fill_value=None):
    it = iter(iterable)
    return zip_longest(*[it]*count, fillvalue=fill_value)


class DecoderBase(object):

    def __init__(self, width, height):
        self._width = width
        self._height = height
        self._image = np.zeros((height, width, 3), dtype='B')

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def image(self):
        return np.array(self._image)

    def decode_frame_chunk(self, stream_chunk, keyframe=False):
        stream_chunk.seek(0)
        buffer = stream_chunk.read()
        keyframe = AVIIF.KEYFRAME in stream_chunk.flags or keyframe
        return self.decode_frame_buffer(buffer=buffer,
                                        size=len(buffer),
                                        keyframe=keyframe)

    def decode_frame_buffer(self, buffer, size, keyframe=True):
        raise NotImplementedError()

    @classmethod
    def for_avi_stream(cls, stream_definition):
        fcc_type = stream_definition.strh.fcc_type
        if fcc_type != FCC_TYPE.VIDEO:
            raise RuntimeError('Stream {} is not a video stream.')

        compression = stream_definition.strf.compression
        for scls in cls.__subclasses__():
            if compression in scls.COMPRESSION:
                return scls.for_avi_stream(stream_definition=stream_definition)
        raise RuntimeError('No decoder for compression type: {}'.format(repr(compression)))
