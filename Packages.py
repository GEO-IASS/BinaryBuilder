#!/usr/bin/env python

from __future__ import print_function

import os
import os.path as P
import re

from glob import glob
from BinaryBuilder import CMakePackage, GITPackage, Package, stage, warn, PackageError, HelperError

def strip_flag(flag, key, env):
    ret = []
    hit = None
    if not key in env:
        return
    for test in env[key].split():
        m = re.search(flag, test)
        if m:
            hit = m
        else:
            ret.append(test)
    if ret:
        env[key] = ' '.join(ret).strip()
    else:
        del env[key]
    return hit, env

class gdal(Package):
    src     = 'http://download.osgeo.org/gdal/gdal-1.9.0.tar.gz'
    chksum  = 'e2eaaf0fba39137b40c0d3069ac41dfb6f3c76db'
    patches = 'patches/gdal'

    @stage
    def configure(self):
        w = ['threads', 'libtiff=internal', 'libgeotiff=internal', 'jpeg', 'png', 'zlib', 'pam']
        wo = \
          '''bsb cfitsio curl dods-root dwg-plt dwgdirect ecw epsilon expat expat-inc expat-lib fme
             geos gif grass hdf4 hdf5 idb ingres jasper jp2mrsid kakadu libgrass
             macosx-framework mrsid msg mysql netcdf oci oci-include oci-lib odbc ogdi pcidsk
             pcraster perl pg php pymoddir python ruby sde sde-version spatialite sqlite3
             static-proj4 xerces xerces-inc xerces-lib'''.split()

        self.helper('./autogen.sh')
        super(gdal,self).configure(with_=w, without=wo, disable='static', enable='shared')

class ilmbase(Package):
    src     = 'http://download.savannah.nongnu.org/releases/openexr/ilmbase-1.0.2.tar.gz'
    chksum  = 'fe6a910a90cde80137153e25e175e2b211beda36'
    patches = 'patches/ilmbase'

    @stage
    def configure(self):
        self.env['AUTOHEADER'] = 'true'
        # XCode in snow leopard removed this flag entirely (way to go, guys)
        self.helper('sed', '-ibak', '-e', 's/-Wno-long-double//g', 'configure.ac')
        self.helper('autoreconf', '-fvi')
        super(ilmbase, self).configure(disable='static')

class openexr(Package):
    src     = 'http://download.savannah.nongnu.org/releases/openexr/openexr-1.7.0.tar.gz'
    chksum  = '91d0d4e69f06de956ec7e0710fc58ec0d4c4dc2b'
    patches = 'patches/openexr'

    @stage
    def configure(self):
        self.env['AUTOHEADER'] = 'true'
        # XCode in snow leopard removed this flag entirely (way to go, guys)
        self.helper('sed', '-ibak', '-e', 's/-Wno-long-double//g', 'configure.ac')
        self.helper('autoreconf', '-fvi')
        super(openexr,self).configure(with_=('ilmbase-prefix=%(INSTALL_DIR)s' % self.env),
                                      disable=('ilmbasetest', 'imfexamples', 'static'))

class proj(Package):
    src     = 'http://download.osgeo.org/proj/proj-4.7.0.tar.gz'
    chksum  = 'bfe59b8dc1ea0c57e1426c37ff2b238fea66acd7'

    @stage
    def configure(self):
        super(proj,self).configure(disable='static')

class curl(Package):
    src     = 'http://curl.haxx.se/download/curl-7.15.5.tar.gz'
    chksum  = '32586c893e7d9246284af38d8d0f5082e83959af'

    @stage
    def configure(self):
        super(curl,self).configure(disable=['static','ldap','ldaps'], without=['ssl','libidn'])

class stereopipeline(GITPackage):
    src     = 'http://github.com/NeoGeographyToolkit/StereoPipeline.git'
    def configure(self):
        self.helper('./autogen')

        disable_apps = 'aligndem bundleadjust demprofile geodiff isisadjustcameraerr isisadjustcnetclip plateorthoproject reconstruct results rmax2cahvor rmaxadjust stereogui'
        enable_apps  = 'bundlevis disparitydebug hsvmerge isisadjust orbitviz orthoproject point2dem point2mesh stereo mer2camera'
        disable_modules  = 'photometrytk controlnettk mpi'
        enable_modules   = 'core spiceio isisio sessions'

        noinstall_pkgs = 'spice qwt gsl geos xercesc kakadu protobuf'.split()
        install_pkgs   = 'boost vw_core vw_math vw_image vw_fileio vw_camera \
                          vw_stereo vw_cartography vw_interest_point openscenegraph \
                          flapack arbitrary_qt curl ufconfig amd colamd cholmod flann'.split()

        if self.arch.os == 'linux':
            noinstall_pkgs += ['superlu']

        w = [i + '=%(INSTALL_DIR)s'   % self.env for i in install_pkgs] \
          + [i + '=%(NOINSTALL_DIR)s' % self.env for i in noinstall_pkgs] \
          + ['isis=%s' % self.env['ISISROOT']]

        includedir = P.join(self.env['NOINSTALL_DIR'], 'include')

        with file(P.join(self.workdir, 'config.options'), 'w') as config:
            for pkg in install_pkgs + noinstall_pkgs:
                ldflags=[]
                ldflags.append('-L%s -L%s' % (self.env['ISIS3RDPARTY'], P.join(self.env['INSTALL_DIR'], 'lib')))

                if self.arch.os == 'osx':
                    ldflags.append('-F%s -F%s' % (self.env['ISIS3RDPARTY'], P.join(self.env['INSTALL_DIR'], 'lib')))

                print('PKG_%s_LDFLAGS="%s"' % (pkg.upper(), ' '.join(ldflags)), file=config)

            qt_pkgs = 'QtCore QtGui QtNetwork QtSql QtSvg QtXml QtXmlPatterns'

            if self.arch.os == 'osx':
                libload = '-framework '
            else:
                libload = '-l'

            print('QT_ARBITRARY_MODULES="%s"' % qt_pkgs, file=config)

            qt_cppflags=['-I%s' % includedir]
            qt_libs=[]

            for module in qt_pkgs.split():
                qt_cppflags.append('-I%s/%s' % (includedir, module))
                qt_libs.append('%s%s' % (libload, module))

            print('PKG_ARBITRARY_QT_CPPFLAGS="%s"' %  ' '.join(qt_cppflags), file=config)
            print('PKG_ARBITRARY_QT_LIBS="%s"' %  ' '.join(qt_libs), file=config)
            print('PKG_ARBITRARY_QT_MORE_LIBS="-lpng -lz"', file=config)

            if self.arch.os == 'linux':
                print('PKG_SUPERLU_STATIC_LIBS=%s' % glob(P.join(self.env['ISIS3RDPARTY'], 'libsuperlu*.a'))[0], file=config)
                print('PKG_GEOS_LIBS=-lgeos-3.3.2', file=config)
            elif self.arch.os == 'osx':
                print('HAVE_PKG_SUPERLU=no', file=config)
                print('PKG_GEOS_LIBS=-lgeos-3.3.1', file=config)

            print('PROTOC=%s' % (P.join(self.env['INSTALL_DIR'], 'bin', 'protoc')),file=config)

        super(stereopipeline, self).configure(
            other   = ['docdir=%s/doc' % self.env['INSTALL_DIR']],
            with_   = w,
            without = ['clapack', 'slapack'],
            disable = ['pkg_paths_default', 'static', 'qt-qmake']
                      + ['app-' + a for a in disable_apps.split()]
                      + ['module-' + a for a in disable_modules.split()],
            enable  = ['debug=ignore', 'optimize=ignore']
                      + ['app-' + a for a in enable_apps.split()]
                      + ['module-' + a for a in enable_modules.split()])

class visionworkbench(GITPackage):
    src     = 'http://github.com/visionworkbench/visionworkbench.git'

    def __init__(self,env):
        super(visionworkbench,self).__init__(env)
        if not P.isdir(env['ISIS3RDPARTY']):
            # This variable is used in LDFLAGS and some other things
            # by default. If this directory doesn't exist, libtool
            # throws a warning. Unfortunately, some of libtools tests
            # will read this warning as a failure. This will cause a
            # compilation failure.
            raise ValueError('The directory described ISIS3RDPARTY does not exist. Have you set ISISROOT correctly? This is required for compilation of VW and ASP. Please set them.')

    @stage
    def configure(self):
        self.helper('./autogen')

        enable_modules  = 'camera mosaic interestpoint cartography hdr stereo geometry tools bundleadjustment'.split()
        disable_modules = 'gpu plate python gui photometry'.split()
        install_pkgs = 'jpeg png gdal proj4 z ilmbase openexr boost flapack protobuf flann'.split()

        w  = [i + '=%(INSTALL_DIR)s' % self.env for i in install_pkgs]
        w.append('protobuf=%(INSTALL_DIR)s' % self.env)

        with file(P.join(self.workdir, 'config.options'), 'w') as config:
            for pkg in install_pkgs:
                print('PKG_%s_CPPFLAGS="-I%s -I%s"' % (pkg.upper(), P.join(self.env['NOINSTALL_DIR'],   'include'),
                                                                    P.join(self.env['INSTALL_DIR'], 'include')), file=config)
                if pkg == 'gdal' and self.arch.os == 'linux':
                    print('PKG_%s_LDFLAGS="-L%s -L%s -ljpeg -lpng14 -lz"'  % (pkg.upper(), self.env['ISIS3RDPARTY'], P.join(self.env['INSTALL_DIR'], 'lib')), file=config)
                else:
                    print('PKG_%s_LDFLAGS="-L%s -L%s"'  % (pkg.upper(), self.env['ISIS3RDPARTY'], P.join(self.env['INSTALL_DIR'], 'lib')), file=config)
            # Specify executables we use
            print('PROTOC=%s' % (P.join(self.env['INSTALL_DIR'], 'bin', 'protoc')),file=config)

        super(visionworkbench, self).configure(with_   = w,
                                               without = ('tiff hdf cairomm zeromq rabbitmq_c tcmalloc x11 clapack slapack qt opencv cg'.split()),
                                               disable = ['pkg_paths_default','static', 'qt-qmake'] + ['module-' + a for a in disable_modules],
                                               enable  = ['debug=ignore', 'optimize=ignore', 'as-needed', 'no-undefined'] + ['module-' + a for a in enable_modules])

class lapack(CMakePackage):
    src     = 'http://www.netlib.org/lapack/lapack-3.4.0.tgz'
    chksum  = '910109a931524f8dcc2734ce23fe927b00ca199f'

    def configure(self):
        LDFLAGS__ = self.env['LDFLAGS']
        LDFLAGS_ = []
        for i in self.env['LDFLAGS'].split(' '):
            if not i.startswith('-L'):
                LDFLAGS_.append(i);
        self.env['LDFLAGS'] = ' '.join(LDFLAGS_)
        super(lapack, self).configure( other=['-DCMAKE_Fortran_COMPILER=gfortran','-DBUILD_SHARED_LIBS=ON','-DBUILD_STATIC_LIBS=OFF','-DBLAS_LIBRARIES=%(ISIS3RDPARTY)s/libblas.so' % self.env] )
        self.env['LDFLAGS'] = LDFLAGS__

class boost(Package):
    src    = 'http://downloads.sourceforge.net/boost/boost_1_49_0.tar.bz2'
    chksum = '26a52840e9d12f829e3008589abf0a925ce88524'
    patches = 'patches/boost'

    def __init__(self, env):
        super(boost, self).__init__(env)
        self.env['NO_BZIP2'] = '1'
        self.env['NO_ZLIB']  = '1'

    @stage
    def configure(self):
        with file(P.join(self.workdir, 'user-config.jam'), 'w') as f:
            if self.arch.os == 'linux':
                toolkit = 'gcc'
            elif self.arch.os == 'osx':
                toolkit = 'darwin'

            # print('variant myrelease : release : <optimization>none <debug-symbols>none ;', file=f)
            # print('variant mydebug : debug : <optimization>none ;', file=f)
            args = [toolkit] + list(self.env.get(i, ' ') for i in ('CXX', 'CXXFLAGS', 'LDFLAGS'))
            print('using %s : : %s : <cxxflags>"%s" <linkflags>"%s -ldl" ;' % tuple(args), file=f)
            print('option.set keep-going : false ;', file=f)

    # TODO: WRONG. There can be other things besides -j4 in MAKEOPTS
    @stage
    def compile(self):
        self.env['BOOST_ROOT'] = self.workdir

        self.helper('./bootstrap.sh')
        os.unlink(P.join(self.workdir, 'project-config.jam'))

        cmd = ['./b2']
        if 'MAKEOPTS' in self.env:
            cmd += (self.env['MAKEOPTS'],)

        self.args = [
            '-q', '--user-config=%s/user-config.jam' % self.workdir,
            '--prefix=%(INSTALL_DIR)s' % self.env, '--layout=versioned',
            'threading=multi', 'variant=release', 'link=shared', 'runtime-link=shared',
            '--without-mpi', '--without-python', '--without-wave', 'stage'
        ]

        cmd += self.args
        self.helper(*cmd)

    # TODO: Might need some darwin path-munging with install_name_tool?
    @stage
    def install(self):
        self.env['BOOST_ROOT'] = self.workdir
        cmd = ['./b2'] + self.args + ['install']
        self.helper(*cmd)

class HeaderPackage(Package):
    def configure(self, *args, **kw):
        kw['other'] = kw.get('other', []) + ['--prefix=%(NOINSTALL_DIR)s' % self.env,]
        super(HeaderPackage, self).configure(*args, **kw)

    @stage
    def compile(self): pass

    @stage
    def install(self):
        self.helper('make', 'install-data')

class gsl_headers(HeaderPackage):
    src = 'ftp://ftp.gnu.org/gnu/gsl/gsl-1.15.tar.gz',
    chksum = 'd914f84b39a5274b0a589d9b83a66f44cd17ca8e',

class geos_headers(HeaderPackage):
    def __init__(self,env):
        super(geos_headers,self).__init__(env)
        if self.arch.os == "osx":
            self.src = 'http://download.osgeo.org/geos/geos-3.3.1.tar.bz2'
            self.chksum = '4f89e62c636dbf3e5d7e1bfcd6d9a7bff1bcfa60'
        else:
            self.src = 'http://download.osgeo.org/geos/geos-3.3.2.tar.bz2'
            self.chksum = '942b0bbc61a059bd5269fddd4c0b44a508670cb3'

    def configure(self):
        super(geos_headers, self).configure(disable=('python', 'ruby'))

class superlu_headers(HeaderPackage):
    src = 'http://crd-legacy.lbl.gov/~xiaoye/SuperLU/superlu_4.3.tar.gz',
    chksum = 'd2863610d8c545d250ffd020b8e74dc667d7cbdd',
    def configure(self): pass
    def install(self):
        d = P.join('%(NOINSTALL_DIR)s' % self.env, 'include', 'SRC')
        self.helper('mkdir', '-p', d)
        cmd = ['cp', '-vf'] + glob(P.join(self.workdir, 'SRC', '*.h')) + [d]
        self.helper(*cmd)

class xercesc_headers(HeaderPackage):
    src = 'http://download.nextag.com/apache//xerces/c/3/sources/xerces-c-3.1.1.tar.gz'
    chksum = '177ec838c5119df57ec77eddec9a29f7e754c8b2'

class qt_headers(HeaderPackage):
    def __init__(self, env):
        super(qt_headers, self).__init__(env)
        if self.arch.os == "osx":
            self.src = 'http://get.qt.nokia.com/qt/source/qt-everywhere-opensource-src-4.7.4.tar.gz'
            self.chksum = 'af9016aa924a577f7b06ffd28c9773b56d74c939'
        else:
            self.src = 'http://get.qt.nokia.com/qt/source/qt-everywhere-opensource-src-4.8.0.tar.gz'
            self.chksum = '2ba35adca8fb9c66a58eca61a15b21df6213f22e'

    @stage
    def configure(self):
        args = './configure -opensource -fast -confirm-license -nomake demos -nomake examples -nomake docs -nomake tools -nomake translations'.split()
        if self.arch.os == 'osx':
            args.append('-no-framework')
        self.helper(*args)

    @stage
    def install(self):
        include = ['--include=%s' % i for i in '**/include/** *.h */'.split()]
        self.copytree(self.workdir + '/', self.env['NOINSTALL_DIR'] + '/', delete=False, args=['-m', '--copy-unsafe-links'] + include + ['--exclude=*'])

class qwt_headers(HeaderPackage):
    src = 'http://downloads.sourceforge.net/qwt/qwt-6.0.1.tar.bz2',
    chksum = '301cca0c49c7efc14363b42e082b09056178973e',
    def configure(self): pass
    def install(self):
        cmd = ['cp', '-vf'] + glob(P.join(self.workdir, 'src', '*.h')) + [P.join('%(NOINSTALL_DIR)s' % self.env, 'include')]
        self.helper(*cmd)

class zlib(Package):
    src     = 'http://downloads.sourceforge.net/libpng/zlib-1.2.6.tar.gz'
    chksum  = '38690375d8d42398ce33b2df726e25cacf096496'

    def unpack(self):
        super(zlib, self).unpack()
        # self.helper('sed', '-i',
        #             r's|\<test "`\([^"]*\) 2>&1`" = ""|\1 2>/dev/null|', 'configure')

    def configure(self):
        super(zlib,self).configure(other=('--shared',))

class zlib_headers(HeaderPackage):
    src     = 'http://downloads.sourceforge.net/libpng/zlib-1.2.6.tar.gz'
    chksum  = '38690375d8d42398ce33b2df726e25cacf096496'

    def configure(self):
        super(zlib_headers,self).configure(other=['--shared'])
    def install(self):
        include_dir = P.join(self.env['NOINSTALL_DIR'], 'include')
        self.helper('mkdir', '-p', include_dir)
        self.helper('cp', '-vf', 'zlib.h', 'zconf.h', include_dir)

class jpeg(Package):
    src     = 'http://www.ijg.org/files/jpegsrc.v8a.tar.gz'
    chksum  = '78077fb22f0b526a506c21199fbca941d5c671a9'
    patches = 'patches/jpeg8'

    def configure(self):
        super(jpeg, self).configure(enable=('shared',), disable=('static',))

class jpeg_headers(HeaderPackage):
    src     = 'http://www.ijg.org/files/jpegsrc.v8a.tar.gz'
    chksum  = '78077fb22f0b526a506c21199fbca941d5c671a9'
    patches = 'patches/jpeg8'

    def configure(self):
        super(jpeg_headers, self).configure(enable=('shared',), disable=('static',))

class png(Package):
    src    = 'http://downloads.sourceforge.net/libpng/libpng-1.4.11.tar.bz2'
    chksum = '85525715cdaa8c542316436659cada13561663c4'

    def configure(self):
        super(png,self).configure(disable='static')

class png_headers(HeaderPackage):
    src    = 'http://downloads.sourceforge.net/libpng/libpng-1.4.11.tar.bz2'
    chksum = '85525715cdaa8c542316436659cada13561663c4'

class cspice_headers(HeaderPackage):
    # This will break when they release a new version BECAUSE THEY USE UNVERSIONED TARBALLS.
    PLATFORM = dict(
        linux64 = dict(
            src    = 'ftp://naif.jpl.nasa.gov/pub/naif/toolkit/C/PC_Linux_GCC_64bit/packages/cspice.tar.Z',
            chksum = '29e3bdea10fd4005a4db8934b8d953c116a2cec7', # N0064
        ),
        linux32 = dict(
            src    = 'ftp://naif.jpl.nasa.gov/pub/naif/toolkit/C/PC_Linux_GCC_32bit/packages/cspice.tar.Z',
            chksum = 'df8ad284db3efef912a0a3090acedd2c4561a25f', # N0064
        ),
        osx32   = dict(
            src    = 'ftp://naif.jpl.nasa.gov/pub/naif/toolkit/C/MacIntel_OSX_AppleC_32bit/packages/cspice.tar.Z',
            chksum = '3a1174d0b5ca183168115d8259901e923b97eec0', # N0064
        ),
    )

    def __init__(self, env):
        super(cspice_headers, self).__init__(env)
        self.pkgname += '_' + self.arch.osbits
        self.src    = self.PLATFORM[self.arch.osbits]['src']
        self.chksum = self.PLATFORM[self.arch.osbits]['chksum']
    def configure(self, *args, **kw): pass
    @stage
    def install(self):
        d = P.join('%(NOINSTALL_DIR)s' % self.env, 'include', 'naif')
        self.helper('mkdir', '-p', d)
        cmd = ['cp', '-vf'] + glob(P.join(self.workdir, 'include', '*.h')) + [d]
        self.helper(*cmd)

class protobuf(Package):
    src = 'http://protobuf.googlecode.com/files/protobuf-2.4.1.tar.bz2'
    chksum = 'df5867e37a4b51fb69f53a8baf5b994938691d6d'

    @stage
    def configure(self):
        self.helper('./autogen.sh')
        super(protobuf, self).configure()

class isis(Package):

    ### ISIS 3.4.0 Needs:
    # geos-3.3.1 - X
    # qt 4.7.4 - X
    # gsl-1.15 - X
    # protobuf7
    # superlu-4.3 -X
    # libz 1.2.6 -X
    # xerces-c 3.1 - X
    # libtiff 3 something
    # libjpeg 8 - X
    # png-14.11 - X
    # qwt 6.0.1 - X

    PLATFORM = dict(
        linux64  = 'isisdist.astrogeology.usgs.gov::x86-64_linux_RHEL6/isis/',
        osx64    = 'isisdist.astrogeology.usgs.gov::x86-64_darwin_OSX/isis/',
        osx32    = 'isisdist.astrogeology.usgs.gov::x86-64_darwin_OSX/isis/',
        Ubuntu   = 'isisdist.astrogeology.usgs.gov::x86-64_linux_UBUNTU/isis/',
        openSUSE = 'isisdist.astrogeology.usgs.gov::x86-64_linux_SUSE11/isis/',
        SuSE     = 'isisdist.astrogeology.usgs.gov::x86-64_linux_SUSE11/isis/',
        fedora   = 'isisdist.astrogeology.usgs.gov::x86-64_linux_FEDORA/isis/',
        debian   = 'isisdist.astrogeology.usgs.gov::x86-64_linux_DEBIAN/isis/',
    )

    def __init__(self, env):
        super(isis, self).__init__(env)
        self.src       = self.PLATFORM[self.arch.osbits]
        if self.arch.dist_name == 'Ubuntu' or self.arch.dist_name == "openSUSE" or self.arch.dist_name == 'debian' or self.arch.dist_name == 'fedora' or self.arch.dist_name == "SuSE":
            self.src   = self.PLATFORM[self.arch.dist_name]
            self.pkgname += '_' + self.arch.dist_name 
        else:
            self.pkgname += '_' + self.arch.osbits
        self.localcopy = P.join(env['DOWNLOAD_DIR'], 'rsync', self.pkgname)


    def _fix_dev_symlinks(self, Dir):
        if self.arch.os != 'linux':
            return

        for lib in glob(P.join(Dir, '*.so.*')):
            if P.islink(lib):
                continue
            devsep = lib.partition('.so.')
            dev = devsep[0] + '.so'
            if not P.exists(dev):
                warn('Creating isis dev symlink %s for %s' % (P.basename(dev), P.basename(lib)))
                self.helper('ln', '-sf', P.basename(lib), dev)

    def _fix_install_name(self, Dir):
        if self.arch.os != 'osx':
            return

        for lib in glob(P.join(Dir, '*.dylib')):
            if P.islink(lib):
                continue
            try:
                self.helper('install_name_tool', '-id', lib, lib)
            except HelperError, e:
                print("Unable to process file: %s" % e)

    @stage
    def fetch(self, skip=False):
        if not os.path.exists(self.localcopy):
            if skip: raise PackageError(self, 'Fetch is skipped and no src available')
            os.makedirs(self.localcopy)
        if skip: return

        self.copytree(self.src, self.localcopy + '/', ['-zv', '--exclude', 'doc/*', '--exclude', '*/doc/*'])

    @stage
    def unpack(self):
        output_dir = P.join(self.env['BUILD_DIR'], self.pkgname)
        self.remove_build(output_dir)
        self.workdir = P.join(output_dir, self.pkgname)
        if not P.exists(self.workdir):
            os.makedirs(self.workdir)
        self.copytree(self.localcopy + '/', self.workdir, ['--link-dest=%s' % self.localcopy])
        self._apply_patches()

    @stage
    def configure(self): pass
    @stage
    def compile(self): pass

    @stage
    def install(self):
        self.copytree(self.workdir + '/', self.env['ISISROOT'], ['--link-dest=%s' % self.localcopy])
        self._fix_dev_symlinks(self.env['ISIS3RDPARTY'])
        self._fix_install_name(self.env['ISIS3RDPARTY'])

class isis_local(isis):
    ''' This isis package just uses the isis in ISISROOT (it's your job to make sure the deps are correct) '''

    def __init__(self, env):
        super(isis_local, self).__init__(env)
        self.localcopy = None

    @stage
    def fetch(self, skip=False): pass
    @stage
    def unpack(self): pass
    @stage
    def configure(self): pass
    @stage
    def compile(self): pass
    @stage
    def install(self):
        self._fix_dev_symlinks(self.env['ISIS3RDPARTY'])
        self._fix_install_name(self.env['ISIS3RDPARTY'])

class osg(CMakePackage):
    src = 'http://www.openscenegraph.org/downloads/stable_releases/OpenSceneGraph-2.8.3/source/OpenSceneGraph-2.8.3.zip'
    chksum = '90502e4cbd47aac1689cc39d25ab62bbe0bba9fc'
    patches = 'patches/osg'

    def configure(self):
        super(osg, self).configure(
                with_='GDAL GLUT JPEG OpenEXR PNG ZLIB'.split(),
                without='COLLADA CURL FBX FFmpeg FLTK FOX FreeType GIFLIB Inventor ITK Jasper LibVNCServer OpenAL OpenVRML OurDCMTK Performer Qt3 Qt4 SDL TIFF wxWidgets Xine XUL'.split(),
                other=['-DBUILD_OSG_APPLICATIONS=ON'])

class flann(CMakePackage):
    src = 'http://people.cs.ubc.ca/~mariusm/uploads/FLANN/flann-1.7.1-src.zip'
    chksum = '61b9858620528919ea60a2a4b085ccc2b3c2d138'
    patches = 'patches/flann'

    def configure(self):
        super(flann, self).configure(other=['-DBUILD_C_BINDINGS=OFF','-DBUILD_MATLAB_BINDINGS=OFF','-DBUILD_PYTHON_BINDINGS=OFF'])

# vim:foldmethod=indent
