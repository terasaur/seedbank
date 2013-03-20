#!/bin/bash

if [ ! -d libtorrent ]; then
    if [ -d ../libtorrent ]; then
        cd ..
    else
        echo "Could not find libtorrent source directory"
        exit 1
    fi
fi

BOOST_TYPE=system # system|source
if [ "$BOOST_TYPE" = "system" ]; then
    BOOST_VERSION="148"

    BJAM_CMD=`which bjam 2>/dev/null`
    if [ -z $BJAM_CMD ]; then
        BJAM_CMD="/usr/bin/bjam${BOOST_VERSION}"
    fi

    export BOOST_INCLUDE_PATH="/usr/include/boost${BOOST_VERSION}"
    if [ -d /usr/lib64/boost${BOOST_VERSION} ]; then
        export BOOST_LIBRARY_PATH="/usr/lib64/boost${BOOST_VERSION}"
    fi
    export BOOST_BUILD_PATH="/usr/share/boost-build"
else
    export BOOST_ROOT="/home/devel/seedbank/vendor/boost_1_48_0"
    export BOOST_BUILD_PATH=${BOOST_ROOT}/tools/build/v2
    BJAM_CMD="${BOOST_ROOT}/bjam"
    BOOST_INCLUDE_PATH="${BOOST_ROOT}/include"
    BOOST_LIBRARY_PATH="${BOOST_ROOT}/stage/lib"
fi

if [ ! -f ${BJAM_CMD} ]; then
    echo "Unable to find bjam: ${BJAM_CMD}"
    exit 1
fi

# build single target
if [ ! -z $1 ]; then
    if [ "$1" = "clean" ]; then
        CLEAN=1
    else
        BUILD_TARGET=$1
    fi
else
    CLEAN=0
fi

# always remove target file before rebuilding
rm -f src/libtorrent.so

cd libtorrent

if [ "$CLEAN" = "1" ]; then
    echo "Running bjam clean"
    ${BJAM_CMD} --clean
    rm -rf bin Debug
    rm -rf bindings/python/bin
    rm -f bindings/python/mpi.c
    rm -f bindings/python/libtorrent.so
    exit
fi

BJAM_OPTS="-d2"
BJAM_OPTS="$BJAM_OPTS gcc-4.4"
#BJAM_OPTS="$BJAM_OPTS gcc"
BJAM_OPTS="$BJAM_OPTS boost=${BOOST_TYPE}"
BJAM_OPTS="$BJAM_OPTS boost-link=shared"
#BJAM_OPTS="$BJAM_OPTS mongodb-link=shared"

CPPFLAGS=""
LINKFLAGS="linkflags=-L/lib64 linkflags=-L/usr/lib64"
if [ "$BOOST_TYPE" = "system" ]; then
    echo -n ""
    #CPPFLAGS="${CPPFLAGS} cppflags=-I${BOOST_INCLUDE_PATH}"
    LINKFLAGS="${LINKFLAGS} linkflags=-L${BOOST_LIBRARY_PATH}"
else
    echo -n ""
fi

#----------#
# begin bjam options

#BJAM_OPTS="$BJAM_OPTS ${CPPFLAGS}"
BJAM_OPTS="$BJAM_OPTS ${LINKFLAGS}"
BJAM_OPTS="$BJAM_OPTS need-librt=yes"
BJAM_OPTS="$BJAM_OPTS link=shared"

# use this for a release build
BJAM_OPTS="$BJAM_OPTS variant=release"

# or these for dev/debugging
#BJAM_OPTS="$BJAM_OPTS debug-symbols=on"
#BJAM_OPTS="$BJAM_OPTS variant=debug"
#BJAM_OPTS="$BJAM_OPTS logging=verbose"

# end bjam options
#----------#

echo ""
echo "#----------------------------------------------------------------------#"
echo "Building libtorrent and python bindings..."
echo ""
cd bindings/python
${BJAM_CMD} ${BJAM_OPTS} $BUILD_TARGET

if [ -f libtorrent.so ]; then
    echo "Copying python libtorrent.so to seedbank src directory"
    cp libtorrent.so ../../../src
fi

