from contextlib import closing
from struct import unpack

from libavifile.data import AviMoviList
from libavifile.decoder import DecoderBase
from libavifile.definition import AviStreamDefinition
from libavifile.enums import AVIF
from libavifile.index import AviV1Index
from libavifile.riff import RIFFChunk, ChunkTypeException


class AviFileHeader(object):

    def __init__(self, micro_sec_per_frame, max_bytes_per_sec,
                 padding_granularity, flags, total_frames,
                 initial_frames, streams, suggested_buffer_size,
                 width, height, reserved):
        self.micro_sec_per_frame = micro_sec_per_frame
        self.max_bytes_per_sec = max_bytes_per_sec
        self.padding_granularity = padding_granularity
        self.flags = AVIF(flags)
        self.total_frames = total_frames
        self.initial_frames = initial_frames
        self.streams = streams
        self.suggested_buffer_size = suggested_buffer_size
        self.width = width
        self.height = height
        self.reserved = reserved

    @classmethod
    def from_chunk(cls, parent_chunk):
        with closing(RIFFChunk(parent_chunk)) as avih_chunk:
            avih_values = unpack('14I', avih_chunk.read(56))
            return cls(*avih_values[:10], avih_values[10:])


class AviFile(object):

    def __init__(self, file_or_filename):
        self.__file = file_or_filename
        if not hasattr(self.__file, 'read'):
            self.__file = open(file_or_filename, 'rb')

        if self.__file.read(4).decode('ASCII') != 'RIFF':
            raise ValueError('Non-RIFF file detected.')

        self.length = unpack('<i', self.__file.read(4))[0]
        if self.__file.read(4).decode('ASCII') != 'AVI ':
            raise ValueError('Non-AVI file detected.')

        with closing(RIFFChunk(self.__file)) as hdrl_chunk:
            self.avi_header = AviFileHeader.from_chunk(parent_chunk=hdrl_chunk)
            self.stream_definitions = []
            for i in range(self.avi_header.streams):
                self.stream_definitions.append(
                    AviStreamDefinition.from_chunk(stream_id=len(self.stream_definitions),
                                                   parent_chunk=hdrl_chunk))
        self.stream_content = None
        while not self.stream_content:
            try:
                self.stream_content = AviMoviList.from_file(self.__file)
            except ChunkTypeException:
                pass

        self.index_v1 = None
        try:
            self.index_v1 = AviV1Index.from_file(self.__file)
            self.stream_content.apply_index(self.index_v1)
        except ChunkTypeException:
            if AVIF.MUSTUSEINDEX in self.avi_header.flags:
                raise ValueError('AVI header requires use of index and index is missing.')

    @property
    def avih(self):
        return self.avi_header

    @property
    def strl(self):
        return self.stream_definitions

    @property
    def movi(self):
        return self.stream_content

    @property
    def idx1(self):
        return self.index_v1

    def iter_frames(self, stream_id):
        stream_definition = self.stream_definitions[stream_id]
        decoder = DecoderBase.for_avi_stream(stream_definition=stream_definition)
        for stream_chunk in self.stream_content.iter_chunks(stream=stream_id):
            yield decoder.decode_frame_chunk(stream_chunk=stream_chunk,
                                             keyframe=True)

    def close(self):
        if not self.__file.closed:
            self.__file.close()
