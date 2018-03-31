from setuptools import setup


exec(open('./src/libavifile/__about__.py', 'rt').read())


setup(name='libavifile',
      version=__version__,
      description='A library for reading simple uncompressed'
                  'or RLE compressed AVI files.',
      author=__author__,
      url='https://github.com/michaeluhl/libavifile',
      license=__license__,
      package_dir={'': 'src'},
      packages=['libavifile'],
      python_requires='>=3',
      install_requires=['numpy'],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Other Environment',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 3 :: Only',
          'Topic :: Software Development :: Libraries :: Application Frameworks',
          ])

