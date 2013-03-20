
#ifndef LOGGING_TORRENT_PLUGIN_HPP_INCLUDED
#define LOGGING_TORRENT_PLUGIN_HPP_INCLUDED

#ifdef _MSC_VER
#pragma warning(push, 1)
#endif

#include <boost/shared_ptr.hpp>
#include "libtorrent/config.hpp"

#ifdef _MSC_VER
#pragma warning(pop)
#endif

namespace libtorrent
{
    struct torrent_plugin;
    class torrent;
    TORRENT_EXPORT boost::shared_ptr<torrent_plugin> create_torrent_logging_plugin(torrent*, void*);
}

#endif // LOGGING_TORRENT_PLUGIN_HPP_INCLUDED

