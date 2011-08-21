#-------------------------------------------------------------------------------
# This file is part of PyMad.
# 
# Copyright (c) 2011, CERN. All rights reserved.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# 	http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#-------------------------------------------------------------------------------
#!/usr/bin/python

from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext

sourcefiles=["cern/cpymad/madx.pyx"] # this can be a list of both c and pyx source files..
pythonsrc=["cern",
           "cern.cpymad",
           "cern.jpymad",
           "cern.jpymad.tools", 
           "cern.pymad",
           "cern.pymad.io",
           "cern.pymad.abc",
           "cern.pymad.tools",
           "cern.pymad.domain"] 
cdata=['_models/*.json','_models/*.madx'] # list of data files to include..
libs=['madx', "X11", "z", "pthread", "c", "stdc++"]
includedirs=['/usr/local/include/madX',
             '/usr/include/madX',
             '/afs/cern.ch/user/y/ylevinse/.local/include/madX']
libdirs=['/afs/cern.ch/user/y/ylevinse/.local/lib']

madmodule=Extension('cern.madx',
                    define_macros = [('MAJOR_VERSION', '0'),
                                     ('MINOR_VERSION', '1')],
                    include_dirs = includedirs,
                    libraries = libs,
                    sources = sourcefiles,
                    library_dirs = libdirs
                    )

setup(
    name='PyMAD',
    version='0.1',
    description='Interface to Mad-X, using Cython or Py4J through JMAD',
    cmdclass = {'build_ext': build_ext},
    ext_modules = [madmodule],
    author='PyMAD developers',
    author_email='pymad@cern.ch',
    license = 'CERN Standard Copyright License',
    requires=['Cython','numpy','Py4J'],
    packages = pythonsrc,
    package_data={'cern.cpymad': cdata},
    )
