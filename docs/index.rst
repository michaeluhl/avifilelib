.. avifilelib documentation master file, created by
   sphinx-quickstart on Sat Mar 31 15:59:38 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to avifilelib's documentation!
======================================

`avifilelib` provides a mechanism to load frames from avifiles.

The primary user class in this library is :py:class:`avifilelib.AviFile`.

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


Contents:

.. toctree::
   avifilelib


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

