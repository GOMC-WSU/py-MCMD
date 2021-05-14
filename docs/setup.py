"""NAMD_GOMC - A Hybrid MD/MC Simulation Software

"""

import os
import subprocess
from setuptools import setup, find_packages
from distutils.spawn import find_executable

#####################################
NAME = 'NAMD_GOMC'
VERSION = "0.0.01"
ISRELEASED = True
if ISRELEASED:
    __version__ = VERSION
else:
    __version__ = VERSION + '.dev0'
#####################################


def proto_procedure():
    # Find the Protocol Compiler and compile protocol buffers
    # Taken from https://github.com/protocolbuffers/protobuf/blob/fcfc47d405113b59bd43c2e54daf5d9fe5c44593/python/setup.py
    # Only compile if a protocompiler is found, otherwise don't do anything
    if 'PROTOC' in os.environ and os.path.exists(os.environ['PROTOC']):
      protoc = os.environ['PROTOC']
    elif os.path.exists("../src/protoc"):
      protoc = "../src/protoc"
    elif os.path.exists("../src/protoc.exe"):
      protoc = "../src/protoc.exe"
    elif os.path.exists("../vsprojects/Debug/protoc.exe"):
      protoc = "../vsprojects/Debug/protoc.exe"
    elif os.path.exists("../vsprojects/Release/protoc.exe"):
      protoc = "../vsprojects/Release/protoc.exe"
    else:
      protoc = find_executable("protoc")
      if protoc is None:
          protoc = find_executable("protoc.exe")

    if protoc is not None:
        compile_proto(protoc)


def compile_proto(protoc):
    protoc_command = [protoc, '-I=NAMD_GOMC/formats/',
            '--python_out=NAMD_GOMC/formats/', 'compound.proto']
    subprocess.call(protoc_command)


if __name__ == '__main__':

    proto_procedure()

    setup(
        name=NAME,
        version=__version__,
        description=__doc__.split('\n'),
        long_description=__doc__,
        author='',
        author_email='',
        url='https://github.com/bc118/NAMD_GOMC',
        download_url='https://github.com/bc118/NAMD_GOMC/tarball/{}'.format(__version__),
        packages=find_packages(),
        package_data={'NAMD_GOMC': ['utils/reference/*.{pdb,mol2}',
                                 'lib/*.{pdb,mol2}',
                                 ]},
        package_dir={'NAMD_GOMC': 'NAMD_GOMC'},
        include_package_data=True,
        license="MIT",
        zip_safe=False,
        keywords='NAMD_GOMC',
        classifiers=[
            'Development Status :: 0 - Beta',
            'Intended Audience :: Science/Research',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: GPL-3.0 and a University of Illinois Open Source License',
            'Natural Language :: English',
            'Programming Language :: Python',
            'Programming Language :: Python :: 3',
            'Topic :: Scientific/Engineering :: Chemistry',
            'Operating System :: Microsoft :: Windows',
            'Operating System :: POSIX',
            'Operating System :: Unix',
            'Operating System :: MacOS',
        ],
    )

