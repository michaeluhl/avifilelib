from struct import unpack
import numpy as np


class RLEDecoder(object):

    def __init__(self, width, height, colors):
        self.__width = width
        self.__height = height
        self.__colors = colors
        self.__image = np.zeros((height, width, 3), dtype='B')
        self.__image[:,:,:] = self.__colors[0,:]

    @property
    def width(self):
        return self.__width

    @property
    def height(self):
        return self.__height

    @property
    def colors(self):
        return self.__colors

    def decode_frame(self, rle_file, size):
        data = np.fromfile(rle_file, dtype='<B', count=size)
        row, col = 0, 0
        mode = 0
        for i in range(0, size, 2):
            count, color_idx = data[i:i+2]
            if mode == 'delta':
                col += count
                row += color_idx
                mode = 0
            elif mode > 0:
                self.__image[row, col, :] = self.__colors[count, :]
                col += 1
                mode -= 1
                if mode > 0:
                    self.__image[row, col, :] = self.__colors[color_idx, :]
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
                self.__image[row, col:col+count, :] = self.__colors[color_idx, :]
                col += count
        self.__image = np.flip(self.__image, axis=0)
        return
