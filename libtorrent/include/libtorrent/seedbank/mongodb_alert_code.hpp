
#ifndef MONGODB_ALERT_CODE_HPP_INCLUDED
#define MONGODB_ALERT_CODE_HPP_INCLUDED

#ifdef _MSC_VER
#pragma warning(push, 1)
#endif

#include "libtorrent/config.hpp"

#ifdef _MSC_VER
#pragma warning(pop)
#endif

namespace libtorrent
{
    class TORRENT_EXPORT mongodb_alert_code
    {
    public:
        enum code_t
        {
            // INFO
            db_connect_ok = 201,
            torrent_activated = 202,

            // WARN
            torrent_not_found = 401,

            // ERROR
            unclassified_error = 500,
            db_connect_error = 501,
            db_connection_failed = 502,
            invalid_torrent_file = 503
        };
    };

}

#endif // MONGODB_ALERT_CODE_HPP_INCLUDED
