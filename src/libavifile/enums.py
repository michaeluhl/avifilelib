from enum import Enum

try:
    from enum import IntFlag
except ImportError:
    from aenum import IntFlag


class BI_COMPRESSION(IntFlag):
    BI_RGB = 0x0000
    BI_RLE8 = 0x0001
    BI_RLE4 = 0x0002
    BI_BITFIELDS = 0x0003
    BI_JPEG = 0x0004
    BI_PNG = 0x0005
    BI_CMYK = 0x000B
    BI_CMYKRLE8 = 0x000C
    BI_CMYKREL4 = 0x000D


class AVIF(IntFlag):
    HASINDEX = 0x00000010
    MUSTUSEINDEX = 0x00000020
    ISINTERLEAVED = 0x00000100
    WASCAPTUREFILE = 0x00010000
    COPYRIGHTED = 0x00020000


class AVISF(IntFlag):
    AVISF_DISABLED = 0x00000001
    AVISF_VIDEO_PALCHANGES = 0x00010000


class AVIIF(IntFlag):
    LIST = 0x00000001
    KEYFRAME = 0x00000010
    NO_TIME = 0x00000100


class FCC_TYPE(Enum):
    AUDIO = 'auds'
    MIDI = 'mids'
    TEXT = 'txts'
    VIDEO = 'vids'


class STREAM_DATA_TYPES(Enum):
    UNCOMPRESSED_VIDEO = 'db'
    COMPRESSED_VIDEO = 'dc'
    PALETTE_CHANGE = 'pc'
    AUDIO_DATA = 'wb'
