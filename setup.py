from setuptools import setup


exec(open('./src/avifilelib/__about__.py', 'rt').read())


def readme():
    with open('README.rst') as f:
        return f.read()


setup(name='avifilelib',
      version=__version__,
      description='A library for reading simple uncompressed'
                  'or RLE compressed AVI files.',
      long_description=readme(),
      author=__author__,
      url='https://github.com/michaeluhl/avifilelib',
      license=__license__,
      package_dir={'': 'src'},
      packages=['avifilelib'],
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
          ],
      include_package_data=True)

