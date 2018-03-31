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

"""Enumerations associated with AVI Files.

The module provides enumerations used in the fields
of AVI file data structures.

"""
from enum import Enum

try:
    # IntFlag is only natively available in Python 3.6 and later
    from enum import IntFlag
except ImportError:
    # So try to import it from aenum if it is not available from
    # enum
    from aenum import IntFlag


class BI_COMPRESSION(IntFlag):
    """AVI compression flags."""
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
    """AVI header flags."""
    HASINDEX = 0x00000010
    MUSTUSEINDEX = 0x00000020
    ISINTERLEAVED = 0x00000100
    WASCAPTUREFILE = 0x00010000
    COPYRIGHTED = 0x00020000


class AVISF(IntFlag):
    """AVI stream header Flags."""
    AVISF_DISABLED = 0x00000001
    AVISF_VIDEO_PALCHANGES = 0x00010000


class AVIIF(IntFlag):
    """AVI index flags."""
    LIST = 0x00000001
    KEYFRAME = 0x00000010
    NO_TIME = 0x00000100


class FCC_TYPE(Enum):
    """AVI stream types."""
    AUDIO = 'auds'
    MIDI = 'mids'
    TEXT = 'txts'
    VIDEO = 'vids'


class STREAM_DATA_TYPES(Enum):
    """AVI stream chunk data types."""
    UNCOMPRESSED_VIDEO = 'db'
    COMPRESSED_VIDEO = 'dc'
    PALETTE_CHANGE = 'pc'
    AUDIO_DATA = 'wb'
