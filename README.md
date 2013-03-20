## Repository init ##

The Seed Bank repository has submodules.  After you clone, run:

    git submodule init
    git submodule update

## Building ##

You need boost build (bjam) to compile libtorrent.  If you're familiar with libtorrent,
you can use bjam directly.  Otherwise, try the build script.  The following are valid:

    ./scripts/build.sh

    ./scripts/build.sh clean

    ./scripts/build.sh debug

