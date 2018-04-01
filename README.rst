avifilelib
==========

A native Python library (other than it's dependence on Numpy) to
read uncompressed and RLE-compressed AVI files.

The following is a simple example showing how to iterate over the
frames in an AVI file:

.. code:: python

    >>> import matplotlib
    >>> matplotlib.use('TKAGG')
    >>> import matplotlib.pyplot as plt
    >>> import avifilelib
    >>> a = avifilelib.AviFile('sample.avi')
    >>> for ct, frame in enumerate(a.iter_frames(stream_id=0)):
            _ = plt.imshow(frame, origin='lower')
            plt.gcf().savefig('frame_{:02d}.png'.format(ct))
    >>> a.close()

See the `API documentation <http://avifilelib.readthedocs.io/en/latest/index.html>`__ for more information.
