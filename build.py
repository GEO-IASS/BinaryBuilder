#!/usr/bin/env python

from __future__ import print_function

import os
import os.path as P
import sys
import subprocess

def findfile(filename, path=None):
    if path is None: path = os.environ.get('PATH', [])
    for dirname in path.split(':'):
        possible = P.join(dirname, filename)
        if P.isfile(possible):
            return possible
    raise Exception('Could not find file %s in path[%s]' % (filename, path))

ccache = True


from Packages import *
from BinaryBuilder import Package, Environment, PackageError, error

if __name__ == '__main__':
    e = Environment(CC       = 'gcc',
                    CXX      = 'g++',
                    CFLAGS   = '',
                    CXXFLAGS = '',
                    LDFLAGS  = r'-Wl,-rpath,/%s' % ('a'*100),
                    MAKEOPTS='-j4', PATH=os.environ['PATH'], HOME=os.environ['HOME'])

    if ccache:
        compiler_dir = P.join(os.environ.get('TMPDIR', '/tmp'), 'mycompilers')
        new = dict(
            CC  = P.join(compiler_dir, e['CC']),
            CXX = P.join(compiler_dir, e['CXX']),
        )

        if not P.exists(compiler_dir):
            os.mkdir(compiler_dir)
        ccache_path = findfile('ccache', e['PATH'])
        subprocess.check_call(['ln', '-sf', ccache_path, new['CC']])
        subprocess.check_call(['ln', '-sf', ccache_path, new['CXX']])
        e.update(new)

    if len(sys.argv) == 1:
        # Many things depend on isis 3rdparty, so do it first
        build = (gsl_headers, geos_headers, superlu_headers, xercesc_headers,
                 qt_headers, qwt_headers, cspice_headers, isis, zlib, bzip2,
                 png, jpeg, proj, gdal, ilmbase, openexr, boost, osg,
                 lapack, visionworkbench, stereopipeline)
    else:
        build = (globals()[pkg] for pkg in sys.argv[1:])

    try:
        for pkg in build:
            Package.build(pkg, e)

    except PackageError, e:
        error(e)

#png -> zlib
#boost -> bzip2
#gdal -> jpeg, png, proj
#openexr -> ilmbase zlib
#visionworkbench -> boost openexr gdal png
#stereopipeline -> gsl_headers, geos_headers, superlu_headers, xercesc_headers, qt_headers, qwt_headers, cspice_headers