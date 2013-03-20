
#ifndef TORRENT_DISABLE_EXTENSIONS

#ifdef _MSC_VER
#pragma warning(push, 1)
#endif

#include <boost/shared_ptr.hpp>
#include <boost/enable_shared_from_this.hpp>

#ifdef _MSC_VER
#pragma warning(pop)
#endif

#include "libtorrent/extensions.hpp"
#include "libtorrent/seedbank/torrent_logging.hpp"
#include "libtorrent/alert.hpp"
#include "libtorrent/alert_types.hpp"

namespace libtorrent {

    class torrent;

namespace
{

    struct torrent_logging_plugin : torrent_plugin, boost::enable_shared_from_this<torrent_logging_plugin>
    {
        torrent_logging_plugin(torrent& t)
            : m_torrent(t)
        {
        }

        void on_state(int s)
        {
            if (m_torrent->alerts().should_post<invalid_request_alert>())
            {
                m_torrent->alerts().post_alert(
                    invalid_request_alert(
                            m_torrent->get_handle(), m_remote, m_peer_id, r
                    )
                    );
            }

            if (ses->m_alerts.should_post<mongodb_plugin_alert>())
            {
                ses->m_alerts.post_alert(mongodb_plugin_alert(mongodb_alert_code::db_connection_failed, e.what()));
            }
        }

        void on_piece_failed(int p)
        {
            // The piece failed the hash check. Record
            // the CRC and origin peer of every block

            // if the torrent is aborted, no point in starting
            // a bunch of read operations on it
            if (m_torrent.is_aborted()) return;

            std::vector<void*> downloaders;
            m_torrent.picker().get_downloaders(downloaders, p);

            int size = m_torrent.torrent_file().piece_size(p);
            peer_request r = {p, 0, (std::min)(16*1024, size)};
            piece_block pb(p, 0);
            for (std::vector<void*>::iterator i = downloaders.begin()
                , end(downloaders.end()); i != end; ++i)
            {
                if (*i != 0)
                {
                    m_torrent.filesystem().async_read(r, boost::bind(&smart_ban_plugin::on_read_failed_block
                        , shared_from_this(), pb, ((policy::peer*)*i)->address(), _1, _2));
                }

                r.start += 16*1024;
                size -= 16*1024;
                r.length = (std::min)(16*1024, size);
                ++pb.block_index;
            }
            TORRENT_ASSERT(size <= 0);
        }

    private:
        torrent& m_torrent;

    };

} }

namespace libtorrent
{

    boost::shared_ptr<torrent_plugin> create_torrent_logging_plugin(torrent* t, void*)
    {
        return boost::shared_ptr<torrent_plugin>(new torrent_logging_plugin(*t));
    }

}

#endif

